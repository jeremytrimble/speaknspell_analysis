from spana.util import TempFileMgr
from spana.parse_trace import parse_read_operations
from spana.offset_table import OffsetTableDb, OffsetTableEntry
from spana.encoder import encoder_main, Encoder, Decoder, encode_samples, header_bits
import typing
import random

import numpy as np

import subprocess
import os

from contextlib import closing

from spana.file_paths import KNOWN_PHRASES_CSV, get_default_image_bytes

EM100_CMD = "em100"
CHIP="BY25D80"

def takeskip(it, take:int, skip:int):
    it = iter(it)
    try:
        while True:
            for _ in range(take):
                yield next(it)
            for _ in range(skip):
                next(it)
    except StopIteration:
        return

def pad_up_to_multiple(a, multiple:int, value_to_append = 0):
    a = list(a)
    discrepancy = len(a) % multiple
    if discrepancy:
        short_by = multiple - discrepancy
        a = list(a) + list([value_to_append]*short_by)
    return a


def get_em100_cmdline(binfile:str, chip:str=CHIP, em100_cmd:str=EM100_CMD):
    em100_cmdargs = [ em100_cmd, 
        "-c", chip, 
        "-d", binfile, 
        "--verify", "-p", "float", "-t", "--start"]
    print(f"{em100_cmdargs=}")
    return em100_cmdargs

def save_latest_first_beep_data(new_first_beep_data:bytes):
    if 1:
        with open("latest_new_first_beep_data.dat", "wb") as out_fo:
            out_fo.write(new_first_beep_data)

def make_all_beeps_point_to_first_beep(FMOD:bytearray, oft:OffsetTableDb):
    beep_entries :typing.List[OffsetTableEntry]= oft.lookup_by_speech("*Beep*")

    first_beep_entry = beep_entries[0]
    for beep_entry in beep_entries:
        beep_entry.sound_data_start_addr = first_beep_entry.sound_data_start_addr
    
    FMOD = bytearray(oft.graft_onto_image(FMOD))
    #FMOD = bytearray(oft.graft_onto_image(FMOD, entry_prefix_bytes=bytes.fromhex("0080")))
    return FMOD


def replace_prefixes(FMOD:bytearray, oft:OffsetTableDb):

    def select_portion(byts) -> bytes:
        return byts[:12+0]

    #speech_pattern = "Beep 217"
    speech_pattern = "H"
    ote = ote_prefix_to_use = oft.lookup_by_speech(speech_pattern)[0]
    prefix_to_use = select_portion(FMOD[ote.sound_data_start_addr:ote.sound_data_end_addr])
    del ote

    for ote in oft:
        FMOD[ote.sound_data_start_addr:
             ote.sound_data_start_addr+len(prefix_to_use)] = prefix_to_use

    print(f"Grafted {len(prefix_to_use)}-byte prefix for {speech_pattern} onto all speech data.")
    return FMOD


def repeated_periodic_sound(FMOD:bytearray, oft:OffsetTableDb):
    beep_entries :typing.List[OffsetTableEntry]= oft.lookup_by_speech("*Beep*")

    first_beep_entry = beep_entries[0]
    beep_datas = []

    for beep_entry in beep_entries:
        print(f"{beep_entry=}")
        beep_datas.append(
            FMOD[ beep_entry.sound_data_start_addr:beep_entry.sound_data_end_addr ]
        )

    # what if we start chopping based on frame boundaries?
    FLB = FRAME_LEN_BYTES = 12

    # plays a complex periodic sound of some kind (not just a square wave like we saw above)
    # saving clearly-periodic data from oscilloscope (mid sound) to ss02.csv 
    # beep_datas[0][1 *FLB: 2 *FLB].hex is: 'eb3101ef5c1f241ae973c6fe'
    new_first_beep_data = (
        beep_datas[0][0 *FLB: 1 *FLB] +     # initial frame
        beep_datas[0][1 *FLB: 2 *FLB] * 1000     # second frame 1000 times
    )

    # graft that onto the first beep entry so we always play it
    graft_start = first_beep_entry.sound_data_start_addr
    graft_end = graft_start + len(new_first_beep_data)
    FMOD[graft_start:graft_end] = new_first_beep_data

    print(f" repeated_periodic_sound: replaced {len(new_first_beep_data)} bytes from 0x{graft_start:06X} to 0x{graft_end:06X}")

    if 0:
        nfbd = new_first_beep_data
        import code
        g = dict(globals())
        g.update(locals())
        code.interact(local=g)

    save_latest_first_beep_data(new_first_beep_data)

    return FMOD


def steve_martin_mode(FMOD:bytearray, oft:OffsetTableDb):

    rnd = random.Random(42)
    idxs = list(range(len(oft)))

    rnd.shuffle(idxs)

    original_addresses = [ ote.sound_data_start_addr for ote in oft ]

    for idx, ote in zip(idxs, oft):
        ote.sound_data_start_addr = original_addresses[idx]

    FMOD = bytearray(oft.graft_onto_image(FMOD))
    return FMOD



    # for each of the comments below, the comment applies to the new_first_beep_data code beneath the comment



def chop_all_beeps_together(FMOD:bytearray, oft:OffsetTableDb):
    beep_entries :typing.List[OffsetTableEntry]= oft.lookup_by_speech("*Beep*")

    first_beep_entry = beep_entries[0]
    beep_datas = []

    for beep_entry in beep_entries:
        print(f"{beep_entry=}")
        beep_datas.append(
            FMOD[ beep_entry.sound_data_start_addr:beep_entry.sound_data_end_addr ]
        )

    # for each of the comments below, the comment applies to the new_first_beep_data code beneath the comment

    ## combine them (this gets all 4 beeps to play in sequence as part of a single 14304-byte mega-read)
    #new_first_beep_data = (
    #    beep_datas[0][:-16] + 
    #    beep_datas[1][:-32] +
    #    beep_datas[2][:-32] +
    #    beep_datas[3]
    #)

    ## this makes it play only the first two tones (with a slight pop at the end)
    #new_first_beep_data = (
    #    beep_datas[0][:len(beep_datas[0])//2] + beep_datas[0][-16:]
    #)

    ## repeats the tone 16 times (need to remove last 16 bytes or else it stops)
    #new_first_beep_data = (
    #    beep_datas[0][:-16] * 16
    #)

    # emits a high-pitched beep (beep_datas[0][3:4] is a single byte: 0xF8), reads 10011 (decimal) bytes
    #new_first_beep_data = (
    #    beep_datas[0][0:3] + 
    #    beep_datas[0][3:4] * 10000
    #)

    ## it likes 0xF8 but doesn't like 0xF7 -- it only reads 8 bytes below (f88700f7f7f7f7f7)
    #new_first_beep_data = (
    #    beep_datas[0][0:3] + 
    #    bytes.fromhex("F7") * 10000
    #)

    ## it also doesn't like 0xF9 -- only reads 8 bytes again (f88700f9f9f9f9f9)
    #new_first_beep_data = (
    #    beep_datas[0][0:3] + 
    #    bytes.fromhex("F9") * 10000
    #)

    ## it also doesn't like 0x8F -- only reads 8 bytes again (f887008f8f8f8f8f)
    #new_first_beep_data = (
    #    beep_datas[0][0:3] + 
    #    bytes.fromhex("8F") * 10000
    #)

    # it also doesn't like 0xA5 -- only reads 8 bytes (f88700a5a5a5a5a5)
    #new_first_beep_data = (
    #    beep_datas[0][0:3] + 
    #    bytes.fromhex("a5") * 10000
    #)

    # - produces similar-sounding high-pitched beep to 0xF8 above -- it reads 10011 bytes before stopping
    # - note that:  both 0xA4 and 0xF8 have the ones-digit set to 0, whereas all
    #   the other tests above that didn't work have the ones-digit set to 1
    # - 0xA4 seems to produce less overshoot in the audio waveform than 0xF8 did...
    #new_first_beep_data = (
    #    beep_datas[0][0:3] + 
    #    bytes.fromhex("a4") * 10000
    #)

    ## - 0x24 produces a high-pitched beep but with less amplitude than 0xF8 and 0xA4 above -- reads 10011 bytes
    ## - amplitude of 0xA4 (and similarly 0xF8) is about 940mVpp
    ## - amplitude of 0x24 is about 317mVpp
    #new_first_beep_data = (
    #    beep_datas[0][0:3] + 
    #    bytes.fromhex("24") * 10000
    #)

    ## - 0x64 produces the high-pitched beep with same amplitude as 0x24 but flipped phase wrt to the 1-byte 2-byte read pattern -- reads 10011 bytes
    #new_first_beep_data = (
    #    beep_datas[0][0:3] + 
    #    bytes.fromhex("64") * 10000
    #)

    ## 0x00 trips overcurrent protection (200mA) on power supply...
    #new_first_beep_data = (
    #    beep_datas[0][0:3] + 
    #    bytes.fromhex("00") * 10000
    #)

    ### 0x22 gets small pop from speaker but then stops -- reads 17 (decimal) bytes though...
    #new_first_beep_data = (
    #    beep_datas[0][0:3] + 
    #    bytes.fromhex("22") * 10000
    #)

    # note that none of the above (single repeated bytes) cause transitions at
    # each sample and maybe don't do the [7 3-sample-long read][1 2-sample-long]
    # periodic thing...

    # frames seem to be 96 bits based on:
    #  - timing pattern of spi byte reads
    #  - striping in bit6 when framed on 96 bit boundaries

    # what if we start chopping based on frame boundaries?
    FLB = FRAME_LEN_BYTES = 12

    # plays a complex periodic sound of some kind (not just a square wave like we saw above)
    # saving clearly-periodic data from oscilloscope (mid sound) to ss02.csv 
    # beep_datas[0][1 *FLB: 2 *FLB].hex is: 'eb3101ef5c1f241ae973c6fe'
    new_first_beep_data = (
        beep_datas[0][0 *FLB: 1 *FLB] +     # initial frame
        beep_datas[0][1 *FLB: 2 *FLB] * 1000     # second frame 1000 times
    )

    #pattern = bytes.fromhex('eb3101ef5c1f241ae973c6fe')    #ORIGINAL
    #pattern = bytes.fromhex('eb3101ef4c1f241ae973c6fe')    # flip a bit (shows up 16 samples after the sample where this is read (the flipped bit 5->4 is in the second byte read at this time))

    #pattern = bytes.fromhex('eb3101ef5c3f241ae973c6fe')     # moved a sample that is only 6 later than the one where this is read

    #pattern = bytes.fromhex('eb3101ef5c2f241ae973c6fe')
    #pattern = bytes.fromhex('eb3101ef5c4f241ae973c6fe')
    #pattern = bytes.fromhex('eb3101ef5c5f241ae973c6fe')
    #pattern = bytes.fromhex('eb3101ef5c1e241ae973c6fe')
    #pattern = bytes.fromhex('eb3101ef5c1d241ae973c6fe')

    # putting results in spreadsheet
    #C1T = CHG_1F_TO = "1c"
    #pattern = bytes.fromhex('eb3101ef5c'+C1T+'241ae973c6fe')

    #CHG = CHG_01_TO = "11"
    #pattern = bytes.fromhex('eb31'+CHG+'ef5c1f241ae973c6fe')

    ## clearly shows a 4-sample delay from where we read to where we see an effect in the signal
    #CHG = CHG_EF5C_TO = "EF5C"
    #pattern = bytes.fromhex('eb3101'+CHG+'1f241ae973c6fe')
    #new_first_beep_data = (
    #    beep_datas[0][0 *FLB: 1 *FLB] +     # initial frame
    #    pattern * 1  +   # second frame 100 times
    #    bytes([0]*12)*1000
    #)

    ## gives the beginning of a recognizable signal
    #new_first_beep_data = (
    #    #beep_datas[0][0:2*12] + 
    #    beep_datas[0][0:12+1] + 
    #    bytes([0])*10000
    #)

    ## same as above, just literal
    #new_first_beep_data = (
    #    bytes.fromhex('f88700f88708f4870ce8872ceb') + 
    #    bytes([0])*10000
    #)

    # flipped least-significant bit in last byte, which causes the signal to swing down to negative max
    #new_first_beep_data = (
    #    bytes.fromhex('f88700f88708f4870ce8872cea') + 
    #    bytes([0])*10000
    #)

    #new_first_beep_data = (
    ##    bytes.fromhex('f88708f4870ce8872ceb') + 
    #    beep_datas[0][0:2*12][3:] + 
    #    bytes([0])*10000
    #)

    print(f"{new_first_beep_data[:16].hex()=}")

    # graft that onto the first beep entry so we always play it
    graft_start = first_beep_entry.sound_data_start_addr
    graft_end = graft_start + len(new_first_beep_data)
    FMOD[graft_start:graft_end] = new_first_beep_data

    print(f" chopping beeps: replaced {len(new_first_beep_data)} bytes from 0x{graft_start:06X} to 0x{graft_end:06X}")

    if 0:
        nfbd = new_first_beep_data
        import code
        g = dict(globals())
        g.update(locals())
        code.interact(local=g)

    save_latest_first_beep_data(new_first_beep_data)

    return FMOD

def say_twosix_eesg(FMOD:bytearray, oft:OffsetTableDb):

    new_data = bytearray()
    speeches = ["Two", "Six", "E"]
    for speech_idx, speech_lkup in enumerate(speeches):
        entry = oft.lookup_by_speech(speech_lkup)[0]
        
        byts = FMOD[entry.sound_data_start_addr:entry.sound_data_end_addr]
        print(f"for {speech_lkup}: initially have {len(byts)} bytes")

        if speech_idx > 0:
            byts = byts[12:]
        if speech_idx < len(speeches) - 1:
            byts = byts[:-16*12]

        new_data += byts
        print(f"  appending {len(byts)} bytes, new length is {len(new_data)}")

    new_data = bytes(new_data)
    
    beep_entries :typing.List[OffsetTableEntry]= oft.lookup_by_speech("*Beep*")
    first_beep_entry = beep_entries[0]
    graft_start = first_beep_entry.sound_data_start_addr
    graft_end = graft_start + len(new_data)
    FMOD[graft_start:graft_end] = new_data

    E_entry = oft.lookup_by_speech("E")[0]
    S_entry = oft.lookup_by_speech("S")[0]
    G_entry = oft.lookup_by_speech("G")[0]

    to_modify = oft.lookup_by_speech("Spell")[0]
    to_modify.sound_data_start_addr = E_entry.sound_data_start_addr
    to_modify.sound_data_end_addr   = E_entry.sound_data_end_addr

    to_modify = oft.lookup_by_speech("Level")[0]
    to_modify.sound_data_start_addr = S_entry.sound_data_start_addr
    to_modify.sound_data_end_addr   = S_entry.sound_data_end_addr

    to_modify = oft.lookup_by_speech("A")[0]
    to_modify.sound_data_start_addr = G_entry.sound_data_start_addr
    to_modify.sound_data_end_addr   = G_entry.sound_data_end_addr

    entry = oft.lookup_by_speech("I win")[0]
    byts = FMOD[entry.sound_data_start_addr:entry.sound_data_end_addr]
    frames = speech_bytes_to_frames(byts)
    frames = np.hstack([frames,frames])
    new_data = bytes(frames.flatten().tolist())

    to_modify = oft.lookup_by_speech("Press Go to Begin")[0]
    graft_start = to_modify.sound_data_start_addr
    graft_end = graft_start + len(new_data)
    FMOD[graft_start:graft_end] = new_data


    FMOD = bytearray(oft.graft_onto_image(FMOD))

    return FMOD

def speech_bytes_to_frames(byts:bytes, frame_size_bytes:int=12, dtype=float):
    """Converts bytes into bitvector sequence."""

    discrepancy = len(byts) % frame_size_bytes
    if discrepancy:
        short_by = frame_size_bytes - discrepancy
        byts = byts + bytes([0]*short_by)
    
    a = np.array(list(byts), dtype=np.uint8).reshape([-1, frame_size_bytes])

    return a

def nibble_swap(a):
    return ((a&0b1111_0000)>>4) | ((a&0b0000_1111)<<4)

def add_encoded_data(FMOD:bytearray, oft:OffsetTableDb):

    speech_lkup = "Beep 217"
    entry = oft.lookup_by_speech(speech_lkup)[0]
    byts = FMOD[entry.sound_data_start_addr:entry.sound_data_end_addr]
    frames = speech_bytes_to_frames(byts)

    new_data = encoder_main()
    print(f"{len(new_data)=}")

    # place "frames" into first beep's speech area (then later we make all beeps point to that slot)
    beep_entries :typing.List[OffsetTableEntry]= oft.lookup_by_speech("*Beep*")
    first_beep_entry = beep_entries[0]
    graft_start = first_beep_entry.sound_data_start_addr
    graft_end = graft_start + len(new_data)
    FMOD[graft_start:graft_end] = new_data

    save_latest_first_beep_data(new_data)

    return FMOD

def encoded_synth(FMOD:bytearray, oft:OffsetTableDb):

    speech_lkup = "Beep 217"
    entry = oft.lookup_by_speech(speech_lkup)[0]
    byts = FMOD[entry.sound_data_start_addr:entry.sound_data_end_addr]
    frames = speech_bytes_to_frames(byts)

    SAMPLE_RATE_HZ = 10000
    duration_sec = 5.0

    if 1:
        print("Encoding a linear pitch sweep from 220Hz to 880Hz")
        # linear pitch sweep from 220Hz to 880Hz
        #AMPLITUDE_COUNTS =  2048
        #AMPLITUDE_COUNTS =  3000
        #AMPLITUDE_COUNTS =  4000
        AMPLITUDE_COUNTS =  500
        freq = np.linspace(220, 880, num=int(SAMPLE_RATE_HZ*duration_sec))
        phs = np.cumsum( 2*np.pi*freq/SAMPLE_RATE_HZ )
        x = (AMPLITUDE_COUNTS * np.sin(phs)).astype(int)
    elif 1:
        AMPLITUDE_COUNTS =  10000
        t = np.arange(int(SAMPLE_RATE_HZ*duration_sec))/SAMPLE_RATE_HZ
        x = (AMPLITUDE_COUNTS * (0<np.sin(2*np.pi*10*t))).astype(int)
    elif 1:
        x = np.zeros(int(SAMPLE_RATE_HZ*duration_sec))
        #A = 10000
        A = 20000
        x[1000:] = A 
        countdown = np.linspace(A,0,A)
        x[3000:3000+len(countdown)] = countdown
        print(f"{countdown=}")

    enc = Encoder()
    new_data = enc.encode_fully(x, fixed_g=None)
    print(f"{len(new_data)=}")

    # place "frames" into first beep's speech area (then later we make all beeps point to that slot)
    beep_entries :typing.List[OffsetTableEntry]= oft.lookup_by_speech("*Beep*")
    first_beep_entry = beep_entries[0]
    graft_start = first_beep_entry.sound_data_start_addr
    graft_end = graft_start + len(new_data)
    FMOD[graft_start:graft_end] = new_data

    save_latest_first_beep_data(new_data)

    return FMOD

def encoded_synth_raw(FMOD:bytearray, oft:OffsetTableDb):

    speech_lkup = "Beep 217"
    entry = oft.lookup_by_speech(speech_lkup)[0]
    byts = FMOD[entry.sound_data_start_addr:entry.sound_data_end_addr]
    frames = speech_bytes_to_frames(byts)

    SAMPLE_RATE_HZ = 10000
    duration_sec = 5.0

    # TODO: try g = 0 and g = 7 here
    #g = 0
    #g = 1
    #g = 4
    g = 7
    #g = 0


    #steps = -1 * np.ones(int(SAMPLE_RATE_HZ*duration_sec), dtype=int)
    #A = 1000
    #A = 400
    A = 400
    steps = (
        ([+1] * A)
      + ([ 0] * A)
      + ([-2] * A*2)
      + ([ 0] * A)
      + ([ 0] * 50*A)
    )

    #steps = np.zeros(int(SAMPLE_RATE_HZ*duration_sec), dtype=int)
    # greater than 450
    # greater than 470
    # less than 490 
    # less than 500
    # min limit is -480

    # less than 460
    # greater than 450


    ## TODO: try making the increment more significant here
    #steps[:460] = +1

    hb = header_bits(g=g, keep_going=True)
    print(f"{hb=:04b}")

    new_data = bytes(list(encode_samples(steps, hb)))

    # place "frames" into first beep's speech area (then later we make all beeps point to that slot)
    beep_entries :typing.List[OffsetTableEntry]= oft.lookup_by_speech("*Beep*")
    first_beep_entry = beep_entries[0]
    graft_start = first_beep_entry.sound_data_start_addr
    graft_end = graft_start + len(new_data)
    FMOD[graft_start:graft_end] = new_data

    save_latest_first_beep_data(new_data)

    return FMOD




def synthesizer2(FMOD:bytearray, oft:OffsetTableDb):

    speech_lkup = "Press Go to Begin"
    #speech_lkup = "I Win"
    #speech_lkup = "W"
    #speech_lkup = "Beep 217"
    if 0:
        entry = oft.lookup_by_speech(speech_lkup)[0]
        byts = FMOD[entry.sound_data_start_addr:entry.sound_data_end_addr]
        frames = speech_bytes_to_frames(byts)
    else:
        DURATION_SEC = 5.0
        SAMPLE_DURATION_SEC = 100e-6  # unless 0xcd is modified
        SAMPLES_PER_FRAME = 23
        FRAMES_PER_SEC = 1/(SAMPLES_PER_FRAME*SAMPLE_DURATION_SEC)
        NUM_FRAMES = int(round(DURATION_SEC * FRAMES_PER_SEC))
        FRAME_SIZE_BYTES = 12 # 96 bits
        print(f"{FRAMES_PER_SEC=}")
        print(f"{NUM_FRAMES=}")
        frames = np.zeros([NUM_FRAMES, FRAME_SIZE_BYTES],dtype=np.uint8)

    # Idle voltage output is 1.70V
    #frames[:,::2] |= 0b0100_0000   # gives a constant DC offset
    #frames[:,1::2] |= 0b0100_0000  # gives a constant DC offset
    #frames[:,1::3] |= 0b0100_0000 # gives a constant DC offset of 2.81V
    #frames[::2,1::3] |= 0b0100_0000 # still constant offset of 2.81V
    #frames[::8,1::3] |= 0b0100_0000 # still constant offset of 2.81V

    # Case 1 in notes:
    #frames[::8,1::3] |= 0b1111_0000 # interesting: starts at initial high value, then steps down 4 steps, then sits at constant, then steps down 4 steps, then sits at constant
                                    # suggests a differential coding of some kind?

    ## Case 2
    #frames[::8,1::3] |= 0b1010_0000

    # Case 3
    #frames[::8,1::3] |= 0b1001_0000

    ## Case 4
    #frames[::8,1::3] |= 0b1111_1111

    ## Case 5
    #frames[::8,1::3] |= 0b1111_0001

    ## Case 6
    #frames[::8,1:] |= 0b1111_0001

    ## Case 7
    #frames[::8,2:] |= 0b1111_0001

    # Case 8
    #frames[::8,2::3] |= 0b1111_0001

    # Case 9
    #frames[::8,2::3] |= 0b0001_1111

    ## Case 10 
    #frames[::8,2::2] |= 0b0001_1111

    ## Case 11
    #frames[::8, 1] |= 0b1111_1111
    #frames[::8, 4] |= 0b1111_1111
    #frames[::8, 7] |= 0b1111_1111
    ##frames[::8,10] |= 0b1111_0000  # this causes a delay before the last step down, so it seems that MSnibble gets used first
    #frames[::8,10] |= 0b0000_1111

    ## Case 12
    #frames[0, 1] |= 0b1111_1111
    #frames[0, 4] |= 0b1111_1111
    #frames[0, 7] |= 0b1111_1111
    #frames[0,10] |= 0b0000_1111
    #frames[8::8, 2] |= 0b1111_1111
    #frames[8::8, 5] |= 0b1111_1111
    #frames[8::8, 8] |= 0b1111_1111
    #frames[8::8,11] |= 0b0000_1111

    ## Case 13
    #frames[   0, 1] |= 0b1111_1111
    #frames[   0, 4] |= 0b1111_1111
    #frames[   0, 7] |= 0b1111_1111
    #frames[   0,10] |= 0b0000_1111
    #frames[8::8, 3] |= 0b1111_1111
    #frames[8::8, 6] |= 0b1111_1111
    #frames[8::8, 9] |= 0b1111_1111

    ## Case 14
    #frames[   0, 1] |= 0b1111_1111
    #frames[   0, 4] |= 0b1111_1111
    #frames[   0, 7] |= 0b1111_1111
    #frames[   0,10] |= 0b0000_1111

    #loset = 0b0000_1111
    #hiset = 0b1111_0000
    #frames[8::8, 1] |= loset
    #frames[8::8, 2] |= hiset

    #frames[8::8, 4] |= loset
    #frames[8::8, 5] |= hiset

    #frames[8::8, 7] |= loset
    #frames[8::8, 8] |= hiset

    #frames[8::8,10] |= loset
    #frames[8::8,11] |= hiset

    ## Case 15
    #frames[   0, 1] |= 0b1111_1111
    #frames[   0, 4] |= 0b1111_1111
    #frames[   0, 7] |= 0b1111_1111
    #frames[   0,10] |= 0b0000_1111

    #loset = 0b0000_1111
    ##hiset = 0b1111_0000
    #frames[8::8, 1] |= loset
    #frames[8::8, 2] |= loset

    #frames[8::8, 4] |= loset
    #frames[8::8, 5] |= loset

    #frames[8::8, 7] |= loset
    #frames[8::8, 8] |= loset

    #frames[8::8,10] |= loset
    #frames[8::8,11] |= loset


    ## Case 16
    #frames[   0, 1] |= 0b1111_1111
    #frames[   0, 4] |= 0b0000_1111
    #frames[   0, 7] |= 0b0000_1111
    #frames[   0,10] |= 0b0000_1111

    #loset = 0b0001_1111
    ##hiset = 0b1111_0000
    #frames[8:, 1] |= loset
    #frames[8:, 2] |= loset

    #frames[8:, 4] |= loset
    #frames[8:, 5] |= loset

    #frames[8:, 7] |= loset
    #frames[8:, 8] |= loset

    #frames[8:,10] |= loset
    #frames[8:,11] |= loset

    #frames[8:,1:] |= loset

    #frames[8:,2]  = nibble_swap(frames[8:,2])
    #frames[8:,5]  = nibble_swap(frames[8:,5])
    #frames[8:,8]  = nibble_swap(frames[8:,8])
    #frames[8:,11] = nibble_swap(frames[8:,11])

    frames[:,0] |= 0b0000_0111 # set loudness bits and keep playing bit -- this on its own gives silence
    #new_data = bytes(frames.flatten().tolist())

    num_samples = NUM_FRAMES * 23
    t = np.arange(num_samples)/10000.
    x = np.round((7*np.sin(2*np.pi*440*t))).astype(np.int8)
    xdiff = np.zeros_like(x)
    xdiff[:-1] = np.diff(x)
    print(f"{xdiff.max()=}")
    print(f"{xdiff.min()=}")

    def encode_samples(x):
        try:
            it = iter(x)
            while True:
                # for each frame:
                s = next(it)
                assert -8 <= s < 8
                #print(f"{s=} {bin((s&0b1111)<<4)=}")
                yield ((s&0b1111)<<4) | 0b0000_0111
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
    
    new_data = bytes(list(encode_samples(xdiff)))
    print(f"{len(new_data)=}")

    # place "frames" into first beep's speech area (then later we make all beeps point to that slot)
    beep_entries :typing.List[OffsetTableEntry]= oft.lookup_by_speech("*Beep*")
    first_beep_entry = beep_entries[0]
    graft_start = first_beep_entry.sound_data_start_addr
    graft_end = graft_start + len(new_data)
    FMOD[graft_start:graft_end] = new_data

    save_latest_first_beep_data(new_data)

    return FMOD



def synthesizer(FMOD:bytearray, oft:OffsetTableDb):

    speech_lkup = "Press Go to Begin"
    #speech_lkup = "I Win"
    #speech_lkup = "W"
    #speech_lkup = "Beep 217"
    entry = oft.lookup_by_speech(speech_lkup)[0]
    byts = FMOD[entry.sound_data_start_addr:entry.sound_data_end_addr]
    frames = speech_bytes_to_frames(byts)

    # take the first byte of the 42nd frame and replace that for all
    #incr = [ (((idx//1)|1)%256) for idx in range(len(frames)) ]
    #frames[:,0] = incr

    # INTERESTING!
    # I can still hear "go to begin" but it is way softer in volume than the initial part of the sound
    #frames[103:,0] = 1

    # makes it sound a little gravely
    #frames[103:,0] = [ (x & 0x7F) for x in frames[103:,0].flatten().tolist() ]
    #frames[103:,0] = [ (x & 0b0111_1111) for x in frames[103:,0].flatten().tolist() ]

    # makes it sound a little fuzzy
    #frames[103:,0] = [ (x & 0b1011_1111) for x in frames[103:,0].flatten().tolist() ]

    # not much audible difference
    #frames[103:,0] = [ (x & 0b1101_1111) for x in frames[103:,0].flatten().tolist() ]

    # not much audible difference
    #frames[103:,0] = [ (x & 0b1110_1111) for x in frames[103:,0].flatten().tolist() ]

    # makes "go to begin" quieter
    frames[103:,0] = [ (x & 0b1111_0111) for x in frames[103:,0].flatten().tolist() ]

    # makes "go to begin" more quieter?
    #frames[103:,0] = [ (x & 0b1111_1011) for x in frames[103:,0].flatten().tolist() ]

    # just makes it sound a little noisy (both of the below)
    #frames[103:,1] = [ (x & 0b0000_1111) for x in frames[103:,0].flatten().tolist() ]
    #frames[103:,1] = [ (x & 0b0000_1111) for x in frames[103:,1].flatten().tolist() ]

    # makes it sound more noisy
    #frames[103:,1::2] = frames[103:,1::2] & 0b0000_1111

    # becoming distorted 
    #frames[103:,1:] = frames[103:,1:] & 0b0000_1111

    # becoming more distorted 
    # for beep 217: lower frequency?
    #frames[103:,:] = frames[103:,:] & 0b0000_1111

    # distorted and very quiet but still there
    #frames[103:,:] = frames[103:,:] & 0b1111_0000
    #frames[103:,0] = frames[103:,0] | 0x1

    # almost no effect compared to two above...
    # for beep 217: lower frequency?
    #frames[103:,:] = frames[103:,:] & 0b0000_1111
    #frames[103:,0] = frames[103:,0] | 0x1

    # "Press" then totally silent (bit 3 is the only thing different from above)
    # same effect for beep 217
    #frames[103:,:] = frames[103:,:] & 0b0000_0111
    #frames[103:,0] = frames[103:,0] | 0x1

    # "Press" then just noise syllables
    # for beep 217: also sounds like "noise syllables"
    #frames[103:,:] = frames[103:,:] & 0b0000_1011
    #frames[103:,0] = frames[103:,0] | 0x1

    # "Press" then just noise syllables but different
    # for beep 217: noise syllables but very quiet
    #frames[103:,:] = frames[103:,:] & 0b0000_1101
    #frames[103:,0] = frames[103:,0] | 0x1

    # "Press" then just noise syllables but also different
    #frames[103:,:] = frames[103:,:] ^ 0b1010_0000
    #frames[103:,0] = frames[103:,0] | 0x1

    # Yes! slowed down speech!
    #frames = np.hstack([frames,frames])

    # Yes! sped up speech!
    #frames = frames[::2,:]

    # TODO: chop last bit or byte of each frame
    # TODO: shift left by one bit
    #frames = frames[:,1:].flatten()

    # gives fuzz whose envelope matches the "Press go to begin" envelope
    #num_frames, num_bytes_per_frame = frames.shape
    #ba = np.unpackbits( frames[:,1:].flatten() )
    #ba = list(takeskip(ba, 95,1))
    #ba = ba + list( [0] * ( num_frames*(num_bytes_per_frame-1)*8 - len(ba) ) )
    #ba = np.array(ba, dtype=np.uint8)
    #ba = np.packbits(ba).reshape([num_frames, num_bytes_per_frame-1])
    #frames[:,1:] = ba

    # Surprisingly, this is still recognizable
    #frames[:,1::2] = 0 # just set half the bytes in the frame data to zero (5 bytes contain data, 6 contain zeros)

    # Also Surprisingly, this is still recognizable
    #frames[:,2::2] = 0 # just set the other half the bytes in the frame data to zero (6 bytes contain data, 5 contain zeros)

    #frames[:,[1,2, 4,5, 6,7, 9,10,]] = 0 # set all but 3 bytes in the frame data to zero
    #frames[:,2:] = 0 # set all but the first byte in the frame data to zero

    #frames[:,0] = frames[:,0] & 0b0000_0001 # very quiet
    #frames[:,0] = frames[:,0] & 0b0000_1111 # almost normal
    #frames[:,0] = frames[:,0] & 0b0000_0111 # a little quieter
    #frames[:,0] = frames[:,0] & 0b0000_0011 #  quieter
    #frames[:,0] = frames[:,0] & 0b0000_0001 # very quiet
    #frames[:,0] = frames[:,0] & 0b1111_1110 # doesn't play
    #frames[:,0] = frames[:,0] ^ 0b1111_0000 # sounds fuzzy

    #frames[:,0] = (frames[:,0] & 0b0000_1111) | (0b0001_1110) # very quiet
    #frames[:,0] = (frames[:,0] & 0b0000_1111) | (0b0001_0110) # very scratchy
    #frames[:,0] = (frames[:,0] & 0b0000_1111) | (0b0000_0110) # very scratchy

    #frames[:,0] = (frames[:,0] & 0b0000_1001) | (0b0000_0110) # very scratchy

    #frames[:,0] = (frames[:,0] & 0b0000_0001) | (0b0000_1110) # very quiet   (bits[3:0] = 1111)
    #frames[:,0] = (frames[:,0] & 0b0000_0001) | (0b0000_0110) # very loud    (bits[3:0] = 0111)
    #frames[:,0] = (frames[:,0] & 0b0000_0001) | (0b0000_0010) # doesn't play (bits[3:0] = 0011)
    #frames[103:,0] = (frames[103:,0] & 0b0000_0001) | (0b0000_0010) # does play but sounds distorted after "Press" (bits[3:0] = 0011)
    #frames[:,0] = (frames[:,0] & 0b0000_0001) | (0b0000_1010) # doesn't play
    #frames[103:,0] = (frames[103:,0] & 0b0000_0001) | (0b0000_1010) # does play but sounds distorted AND LOUDER after "Press" (bits[3:0] = 1011)
    #frames[:,0] = (frames[:,0] & 0b0000_0011) | (0b0000_0000) # quiet        (bits[3:0] = 00?1)

    new_data = bytes(frames.flatten().tolist())
    beep_entries :typing.List[OffsetTableEntry]= oft.lookup_by_speech("*Beep*")
    first_beep_entry = beep_entries[0]
    graft_start = first_beep_entry.sound_data_start_addr
    graft_end = graft_start + len(new_data)
    FMOD[graft_start:graft_end] = new_data

    save_latest_first_beep_data(new_data)

    return FMOD


def access_mystery_data (FMOD:bytearray, oft:OffsetTableDb):
    # make the first beep point to the mystery data
    speech_lkup = "Beep *"
    entries = oft.lookup_by_speech(speech_lkup)
    for entry in entries:
        entry: OffsetTableEntry
        print(f" Overwriting: {entry}")
        FMOD[entry.idx*5 + 0xb : (entry.idx+1)*5 + 0xb] = bytes.fromhex("00cd0f2310")   # "Rother"
        #FMOD[entry.idx*5 + 0xb : (entry.idx+1)*5 + 0xb] = bytes.fromhex("00cd0f2310")    # whaaaat this plays it slower!?
        #FMOD[entry.idx*5 + 0xb : (entry.idx+1)*5 + 0xb] = bytes.fromhex("00cd0EEFE0")   # Spell eight as in eight reindeer
        #FMOD[entry.idx*5 + 0xb : (entry.idx+1)*5 + 0xb] = bytes.fromhex("00ab0EEFE0")   # Higher pitched

    # The mystery word is "Rother"?

    return FMOD

def change_first_byte (FMOD:bytearray, oft:OffsetTableDb):
    # first two bytes are normally 00E0
    #FMOD[0:2] = bytes.fromhex("0010") # goes to A
    #FMOD[0:2] = bytes.fromhex("0110") # acts normal
    #FMOD[0:2] = bytes.fromhex("FFFF") # acts normal
    #FMOD[0:2] = bytes.fromhex("0000") # reads 3 times and never does anything
    #FMOD[0:2] = b"TI" # acts normal
    #FMOD[0:2] = bytes.fromhex("00F0") # acts normal

    #FMOD[0:2] = bytes.fromhex("00C0") # immediately says "Spell" "A" Press Go To Begin.  Skips startup beep and the word "Level"
    #FMOD[0:2] = bytes.fromhex("0080") # goes to A

    FMOD[2:5] = bytes.fromhex("00000a")


    return FMOD

def chipmunk_mode (FMOD:bytearray, oft:OffsetTableDb, new_rate_divider_setting:int = 0x6b):
    #FMOD = bytearray(oft.graft_onto_image(FMOD, entry_prefix_bytes=bytes.fromhex("00ab")))
    # this way doesn't work anymore now that I implemented rate_divider correctly:
    #FMOD = bytearray(oft.graft_onto_image(FMOD, entry_prefix_bytes=bytes.fromhex("006b")))
    for ote in oft:
        ote.rate_divider = new_rate_divider_setting
    FMOD = bytearray(oft.graft_onto_image(FMOD))
    return FMOD

def parse_args():
    import argparse
    parser = argparse.ArgumentParser("Speak & Spell Live Trace", description="Run the em100 with a (possibly modified) flash image.")

    parser.add_argument("-B", "--base-image", default=None, type=str, help="Load a different base image (default is original)")

    parser.add_argument("-M", "--mod", default="none", type=str, 
        choices=[
            "none",
            "steve_martin_mode",
            "chop_all_beeps_together",
            "repeated_periodic_sound",
            "encoded_synth",
            "say_twosix_eesg",
            "add_encoded_data",
            "chipmunk_mode",
            "antichipmunk_mode",
            "synthesizer", 
            "access_mystery_data",
            "arbitrary",
            "replace_prefixes"
        ],
        help="Apply a modification")

    args = parser.parse_args()
    return args

def main():
    args = parse_args()

    if args.base_image is not None:
        F_ORIG = open(args.base_image, "rb").read()
    else:
        F_ORIG = get_default_image_bytes()
    oft = OffsetTableDb.from_flash_image(F_ORIG)
    FMOD = bytearray(F_ORIG)

    if args.mod != "none":
        print(f" applying modification: {args.mod} ")

    if args.mod == "chop_all_beeps_together":
        FMOD = chop_all_beeps_together(FMOD, oft)
        FMOD = make_all_beeps_point_to_first_beep(FMOD, oft)
    elif args.mod == "steve_martin_mode":
        FMOD = steve_martin_mode(FMOD, oft)
        FMOD = make_all_beeps_point_to_first_beep(FMOD, oft)
    elif args.mod == "repeated_periodic_sound":
        #FMOD = replace_prefixes(FMOD, oft)
        FMOD = repeated_periodic_sound(FMOD, oft)
        FMOD = make_all_beeps_point_to_first_beep(FMOD, oft)
    elif args.mod == "encoded_synth":
        #FMOD = replace_prefixes(FMOD, oft)
        FMOD = encoded_synth(FMOD, oft)
        FMOD = make_all_beeps_point_to_first_beep(FMOD, oft)
    elif args.mod == "say_twosix_eesg":
        FMOD = say_twosix_eesg(FMOD, oft)
        FMOD = make_all_beeps_point_to_first_beep(FMOD, oft)
    elif args.mod == "add_encoded_data":
        FMOD = add_encoded_data(FMOD, oft)
        FMOD = make_all_beeps_point_to_first_beep(FMOD, oft)
    elif args.mod == "access_mystery_data":
        FMOD = access_mystery_data(FMOD, oft)
        #FMOD = make_all_beeps_point_to_first_beep(FMOD, oft)
    elif args.mod == "chipmunk_mode":
        FMOD = chipmunk_mode(FMOD, oft, new_rate_divider_setting=0x6b)
        FMOD = make_all_beeps_point_to_first_beep(FMOD, oft)
    elif args.mod == "antichipmunk_mode":
        FMOD = chipmunk_mode(FMOD, oft, new_rate_divider_setting=0x16b)
        FMOD = make_all_beeps_point_to_first_beep(FMOD, oft)

    elif args.mod == "synthesizer":
        FMOD = synthesizer(FMOD, oft)
        FMOD = make_all_beeps_point_to_first_beep(FMOD, oft)

    elif args.mod == "arbitrary":

        # Arbitrary modification, just kinda do whatever here

        #FMOD = say_twosix_eesg(FMOD, oft)
        #FMOD = synthesizer(FMOD, oft)
        #FMOD = change_first_byte(FMOD, oft)

        #FMOD = access_mystery_data(FMOD, oft)

        #FMOD = make_all_beeps_point_to_first_beep(FMOD, oft)

        #FMOD = chipmunk_mode(FMOD, oft)
        #FMOD = synthesizer2(FMOD, oft)

        FMOD = add_encoded_data(FMOD, oft)

        #FMOD = encoded_synth(FMOD, oft)
        #FMOD = encoded_synth_raw(FMOD, oft)

        #FMOD = encoded_synth(FMOD, oft)
        FMOD = make_all_beeps_point_to_first_beep(FMOD, oft)

    elif args.mod == "replace_prefixes":
        FMOD = replace_prefixes(FMOD, oft)

    elif args.mod != "none":
        raise ValueError(f"Unsupported mod: {args.mod}")


    with closing(TempFileMgr()) as tfm:

        proc = subprocess.Popen(
            get_em100_cmdline(tfm.get_tempfile(FMOD)),
            stdout=subprocess.PIPE,
            encoding='utf-8',
        )

        for op in parse_read_operations(proc.stdout): 
            if op.command_str == "read":
                print(f"read addr=0x{op.addr:05X}  len={op.len:5d}  data_prefix={op.data[:10].hex()}")
                offset_table_idx = (op.addr - 0xb)/5
                if offset_table_idx % 1.0 <= 1e-6:
                    offset_table_idx = int(offset_table_idx)
                    if 0 <= offset_table_idx < 224:
                        entry = oft[offset_table_idx]
                        speech = "-???-"
                        if entry is not None and entry.speech is not None:
                            speech = entry.speech
                        print(f" -> Read offset table index: {offset_table_idx:3d} -> {speech}")
            else:
                print(op)

if __name__ == "__main__":
    main()