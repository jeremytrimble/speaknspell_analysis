from spana.offset_table import OffsetTableDb, OffsetTableEntry
from spana.encoder import Encoder
from itertools import count
from pydub import AudioSegment
from pydub.silence import split_on_silence

import glob
import os

this_file_dir = os.path.dirname(os.path.normpath(__file__))

def parse_args():
    import argparse

    parser = argparse.ArgumentParser("constructor", "Build a Speak & Spell flash image from wav files")
    parser.add_argument("-o", "--output-dir", required=1, type=str, help="Output dir for chunks")
    parser.add_argument("-I", "--start-idx", default=0, type=int, help="Initial start idx for output files")
    parser.add_argument("-F", "--format-str", default=None, type=str, help="Format string for output filenames")
    parser.add_argument("-T", "--target-num-splits", default=None, type=int, help="Number of splits to try to get")
    parser.add_argument("-S", "--silence-len-milliseconds", default=500, type=int, help="Expected silence length in milliseconds")
    parser.add_argument("input_file", nargs=1, help="The input file to split")

    args = parser.parse_args()
    return args


#def get_wav_file_dir():
#    return os.path.join(this_file_dir, "../../sounds_to_encode")


def split_file(input_file:str, output_dir:str, filename_format:str=None, start_idx:int=0, target_num_splits:int=None, silence_len_milliseconds:int=None):

    if filename_format is None:
        filename_format = "split_{idx:03d}.wav" 
    
    os.makedirs(output_dir, exist_ok=True)

    seg : AudioSegment = AudioSegment.from_file(input_file)

    #silence_lens_to_try = [1000, 900, 800, 700, 600, 550, 500, 400, 300, 200, 100]
    silence_lens_to_try = list(reversed([100+10*i for i in range(0, 90+1)]))
    if silence_len_milliseconds is not None:
        silence_lens_to_try = [x for x in silence_lens_to_try if x <= silence_len_milliseconds]
        silence_lens_to_try.insert(0, silence_len_milliseconds)
    print(f"{silence_lens_to_try=}")
    while True:
        silence_len = silence_lens_to_try.pop(0)
        segments = split_on_silence(seg, min_silence_len=silence_len, silence_thresh=seg.dBFS-20)
        if target_num_splits is None:
            break
        else:
            if len(segments)== target_num_splits:
                break

    for idx, seg in enumerate(segments, start_idx):
        out_filename = os.path.join( output_dir, filename_format.format(idx=idx) )
        seg.export( out_f=out_filename, format='wav' )
    print(f" wrote {len(segments)} splits")

if __name__ == "__main__":
    args = parse_args()
    split_file(args.input_file[0], args.output_dir, args.format_str, args.start_idx, args.target_num_splits, args.silence_len_milliseconds)
