
from spana.offset_table import OffsetTableDb
from spana.file_paths import get_default_image_bytes, ORIGINAL_BINARY
from spana.encoder import Decoder
import os, io
from scipy.io.wavfile import read as wav_read, write as wav_write
import numpy as np

#import wave


def parse_args():
    import argparse

    parser = argparse.ArgumentParser("decode_sounds_to_wav", 
        description="Decode a Speak & Spell flash image into wav files")
    parser.add_argument("-o", "--output-dir", type=str, help="Output directory in which WAV files will be created (defaults to \"decoded_sounds\")", default="decoded_sounds")
    parser.add_argument("image_file", nargs='?', type=str, help=f"Image file to decode (if not specified, default at {ORIGINAL_BINARY} is used")

    return parser.parse_args()


def decoder_main():

    args = parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    if args.image_file is None:
        image_bytes = get_default_image_bytes()
    else:
        with open(args.image_file, "rb") as in_fo:
            image_bytes = in_fo.read()

    otd = OffsetTableDb.get_default()
    for ote in otd:
        speech_bytes = image_bytes[ote.sound_data_start_addr:ote.sound_data_end_addr]

        compressed_len_bytes = len(speech_bytes)

        dec = Decoder()
        pcm = dec.decode_fully( io.BytesIO(speech_bytes) )
        #print(f'{pcm=}')

        filename = os.path.join(args.output_dir, f"ss_{ote.idx:03d}_{ote.speech or '???'}.wav")
        a_pcm = np.array(pcm, dtype=float)
        a_pcm /= np.abs(a_pcm).max()

        decoded_len_bytes = len(a_pcm) * 2  # assuming 16 bit encoding

        wav_write(filename=filename, rate=int(ote.sample_rate_Hz), data=a_pcm)
        #wav_write(filename=filename, rate=10000, data=a_pcm)

        #with wave.open(filename, mode="wb") as wav_file:
        #    wav_file.setnchannels(1)
        #    wav_file.setsampwidth(2)
        #    wav_file.setframerate(10000)
        #    wav_file.writeframes( b"".join([ int(x).to_bytes(length=2, byteorder='little') for x in pcm ]) )

        CR = decoded_len_bytes / compressed_len_bytes

        print(f"  wrote {filename}, enc size: {compressed_len_bytes:5d}, pcm size: {decoded_len_bytes}, CR: {CR:2.2f}")

if __name__ == "__main__":
    decoder_main()
