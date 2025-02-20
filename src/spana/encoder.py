import typing
import numpy as np
import os, sys
import dataclasses
import io

MAX_VAL = 460
MIN_VAL = -480

def byte_to_nibbles(b:int):
    return ((b>>4)&0xF), (b&0xF)

def nibble_to_signed(b:int):
    if b > 7:
        return b - 16
    return b

def header_bits(g, keep_going) -> int:
    g = int(g)
    keep_going = 1 if bool(keep_going) else 0
    assert 0 <= g <= 7
    return (int(f"{g:03b}"[::-1],2)<<1) | keep_going


def encode_samples(x, header_bits):
    try:
        it = iter(x)
        while True:
            # for each frame:
            s = next(it)
            assert -8 <= s < 8
            #print(f"{s=} {bin((s&0b1111)<<4)=}")
            yield ((s&0b1111)<<4) | header_bits
            del s

            # 22 more samples (11 bytes)
            for byte_idx in range(1,11+1):
                s1 = next(it)
                assert -8 <= s1 < 8
                s2 = next(it)
                assert -8 <= s2 < 8

                if byte_idx %3 == 2:
                    s2,s1 = s1,s2 # nibble swap
                yield ((s2&0b1111)<<4) | (s1&0b1111)
    except StopIteration:
        pass

def pad_up_to_multiple(a, multiple:int, value_to_append = 0):
    a = list(a)
    discrepancy = len(a) % multiple
    if discrepancy:
        short_by = multiple - discrepancy
        a = list(a) + list([value_to_append]*short_by)
    return a

class Encoder:
    def __init__(self):
        #self._last_sample = 511 
        self._last_sample = 0

    @classmethod
    def encode_frame_at_gain(cls, s: np.ndarray, g:int, s_init:int) -> typing.Tuple[bytes, float, int]:
        assert len(s) == 23

        gain = 2**g

        cur = s_init

        steps = np.zeros([23], dtype=np.int8)
        error = np.zeros([23])
        vals = np.zeros([23], dtype=int) # can omit later
        for idx in range(23):
            next = s[idx]

            step = np.round((next - cur)/gain).astype(int).clip(-8,+7)
            steps[idx] = step

            cur = cur + step * gain
            vals[idx] = cur
            error[idx] = next - cur

        hb = header_bits(g=g, keep_going=True)

        sample_list = list(int(x) for x in encode_samples(steps, hb))
        sample_list = [ (x if x >=0 else x%256) for x in sample_list ]
        #print(f"{sample_list=}")
        encoded_bytes = bytes(sample_list)
        score = np.sum(error**2)
        last_sample = cur

        #print(f"  {s=} {g=} {s_init=} {gain=} ")

        if 0:
            print(f"""  {s=} 
  {g=} {s_init=} {gain=} 
  {vals=}
  {score=}
""")

        return (encoded_bytes, score, last_sample, vals, steps, error)

    def encode_frame(self, s: np.ndarray, fixed_g:int = None):
        last_sample = self._last_sample

        if fixed_g is None:

            best_encoding_so_far = None
            for g in range(0,6+1):
                tup = self.encode_frame_at_gain(s, g, last_sample)
                #print(f" encoded with {g=}, {tup[1:]=}")
                _, score, _ = tup[:3]
                if (best_encoding_so_far is None) or (score < best_encoding_so_far[1]):
                    best_encoding_so_far = tuple(list(tup) + [g])
        else:
            best_encoding_so_far = tuple( list(self.encode_frame_at_gain(s, fixed_g, last_sample)) + [fixed_g] )

        encoded_bytes, score, last_sample = best_encoding_so_far[:3]

        self._last_sample = last_sample
        return encoded_bytes, best_encoding_so_far

    def encode_int_array(self, s:np.ndarray, fixed_g:int = None) -> typing.Generator[bytes, None, None]:
        idx = 0
        s = pad_up_to_multiple(s, 23)

        while idx < len(s):
            #print(f"{idx=}:")
            frame = s[idx:idx+23]
            byts, _ = self.encode_frame(frame, fixed_g)
            idx += 23
            yield byts

    def encode_fully(self, s:np.ndarray, fixed_g:int = None) -> bytes:
        return b"".join(list(self.encode_int_array(s, fixed_g=fixed_g)))


@dataclasses.dataclass
class FrameFields:
    steps: list[int]
    g: int
    keep_going: bool

class Decoder:
    def __init__(self):
        pass

    @classmethod
    def extract_frame_fields(cls, frame:bytes) -> FrameFields:
        assert(len(frame)==12)

        steps = []

        nts = nibble_to_signed

        step0, header_bits = byte_to_nibbles(frame[0])
        steps.append( nts(step0) )
        del step0

        rev_g = ((header_bits&0b1110) >> 1)
        g = int(f"{rev_g:03b}"[::-1],2) # bit reversal and re-parse
        keep_going = bool(header_bits&0b1)

        for byte_idx in range(1,11+1):
            nh, nl = byte_to_nibbles(frame[byte_idx])
            nh = nts(nh)
            nl = nts(nl)

            if byte_idx %3 == 2:
                steps.append(nh)
                steps.append(nl)
            else:
                steps.append(nl)
                steps.append(nh)

        return FrameFields(
            steps=steps,
            g=g,
            keep_going=keep_going,
        )

    @classmethod
    def decode_frame(cls, ff:FrameFields, s_init:int) -> typing.Sequence[int]:

        g = ff.g
        if ff.g == 7:
            g = 0

        gain = 2**ff.g
        cur = s_init

        vals = []

        for step in ff.steps:
            cur = cur + step * gain
            #cur = np.clip(cur, MIN_VAL, MAX_VAL)   # shockingly this line makes decoding really slow somehow, also we get unexpected DC offsets, would rather leave unconstrained
            vals.append(cur)

        return vals

    def decode(self, in_fo: io.BytesIO) -> typing.Generator[ typing.Sequence[int], None, None ]:
        #cur = 511
        cur = 0

        stop_going_ctr = 0
        got_at_least_one_keep_going = False

        while True:
            frame = in_fo.read(12)
            if len(frame) < 12:
                break

            ff = self.extract_frame_fields(frame)

            if ff.keep_going:
                got_at_least_one_keep_going = True
                stop_going_ctr = 0
            else:
                stop_going_ctr += 1

            if (stop_going_ctr >= 3 and got_at_least_one_keep_going) or (stop_going_ctr > 4):
                break

            if not ff.keep_going:
                continue

            decoded_ints = self.decode_frame(ff, s_init = cur)
            yield decoded_ints
            cur = decoded_ints[-1]

    def decode_fully(self, in_fo: io.BytesIO) -> typing.Sequence[int]:
        L = []
        for vals in self.decode(in_fo):
            L.extend(vals)
        return L

