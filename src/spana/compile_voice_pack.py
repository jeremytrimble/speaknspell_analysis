from spana.offset_table import OffsetTableDb, OffsetTableEntry
from spana.encoder import Encoder
from scipy.io.wavfile import read as wav_read, write as wav_write
import numpy as np
import multiprocessing

import glob
import os

this_file_dir = os.path.dirname(os.path.normpath(__file__))

def get_single_match(pattern, dir_to_search):
    matches = glob.glob(pathname=pattern, root_dir=dir_to_search)
    if len(matches) > 1:
        raise ValueError(f"pattern {pattern} gives multiple matches: {matches}")
    elif len(matches) < 1:
        raise ValueError(f"pattern {pattern} gives no matches")
    return os.path.join( dir_to_search, matches[0] )


def parse_args():
    import argparse

    parser = argparse.ArgumentParser("compile_voice_pack", 
        description="Build a Speak & Spell flash image from wav files",
        epilog="""The directory specified with -d/--wav-dir should contain 223 WAV files (at 10kHz
sample rate).  Each wav file should have a 3-digit (with leading zeros) number
in the filename (e.g. 042_angel.wav) which indicates which record in the offset
table it will be encoded into.

See known_phrases.csv for a list of all known Speak&Spell words."""
    )
    parser.add_argument("-d", "--wav-dir", required=1, type=str, help="Input search dir for wav files")

    return parser.parse_args()

def normalize_signal(s):
    s = np.hstack([ [0], s ])
    s_max = np.abs(s).max()
    s = (s/s_max * 450).round().astype(int)

    return s


def encode_single_file(filename, out_bytes_filename=None) -> bytes:
    sample_rate, s = wav_read(filename)

    s = normalize_signal(s)

    enc = Encoder()
    encoded = b"".join(list(enc.encode_int_array(s)))

    if out_bytes_filename is not None:
        with open(out_bytes_filename, "wb") as out_fo:
            out_fo.write(encoded)

    return encoded




def main():

    args = parse_args()

    wav_file_dir = args.wav_dir

    idx_to_pattern = [None] * 0xe0

    # defaults: search by index
    idx_to_pattern = [ f"*{idx:03d}*.wav" for idx in range(len(idx_to_pattern)) ]

    idx_to_pattern[220] = idx_to_pattern[217]    # s to the n
    idx_to_pattern[223] = idx_to_pattern[217]    # s to the n

    # identify the files
    idx_to_matching_filename = [ get_single_match(x, wav_file_dir) for x in idx_to_pattern ]
    del idx_to_pattern


    unique_filenames = list(set(idx_to_matching_filename))
    # load and encode each filename

    #print(f"{len(idx_to_matching_filename)=}")
    #print(f"{len(unique_filenames)=}")

    print(f"Encoding...")
    with multiprocessing.Pool(processes=6) as pool:
        encoded_bytes = pool.map(encode_single_file, unique_filenames)
        filename_to_encoded_bytes = dict(zip(unique_filenames, encoded_bytes))
    del encoded_bytes

    #print(f"{len(filename_to_encoded_bytes)=}")

    SOUND_SECTION = b""
    filename_to_encoded_bytes_offset = {}

    prefix    = bytes.fromhex("008800 008800 008800 008800")
    separator = bytes.fromhex('008800 008800 008800 0088000 088010 00000')

    print(f"Allocating...")
    # associate offset table entry to a sound
    # "allocate" space for the sounds, update the offset table entry start addresses
    for (filename, encoded_bytes) in filename_to_encoded_bytes.items():
        filename_to_encoded_bytes_offset[filename] = len(SOUND_SECTION)
        SOUND_SECTION += prefix + (encoded_bytes) +  separator*2

    #print(f"{len(SOUND_SECTION)=}")
    SOUND_SECTION_START_OFFSET = 0x470

    print(f"Relocating...")
    otd = OffsetTableDb.get_default()
    for otd_idx in range(len(otd)):
        ote = otd.get_by_idx(otd_idx)
        ote.sample_rate_Hz = 10000

        filename = idx_to_matching_filename[otd_idx]

        #print(f"mapping {otd_idx=} to {filename=}")

        if filename is None: 
            ote.sound_data_start_addr = 0
            continue

        encoded_bytes_offset = filename_to_encoded_bytes_offset[filename]
        ote.sound_data_start_addr = SOUND_SECTION_START_OFFSET + encoded_bytes_offset
    
    header = otd.generate_bytes_for_image()
    assert len(header) < SOUND_SECTION_START_OFFSET
    header=(header+bytes([0]*SOUND_SECTION_START_OFFSET))[:SOUND_SECTION_START_OFFSET]

    image = header + SOUND_SECTION
    
    if len(image) < 2**20:
        image += bytes([0] * (2**20-len(image)))

    print(f"Saving file...")
    with open("custom_voice_pack.bin", "wb") as out_fo:
        out_fo.write(image)
    print(f"done")


if __name__ == "__main__":
    main()