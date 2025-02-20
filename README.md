# Speak-n-Spell Analysis & Custom Voice Pack Software

Enables analysis and modification of the speech sounds on 2019 Speak&Spell toys (sold under the "Basic Fun" brand with "Classic 80's Design").


## Installation / Prerequisites

### Python environment
To install the `spana` (speak-and-spell analysis) package into a virtual environment, run:

```shell

cd speaknspell_analysis/
python3.13 -m venv .venv
source .venv/bin/activate

pip install -U pip

# install `spana` from this checkout in editable mode
pip install -e .

```

### Other (optional) Tools
- `em100` open-source command-line tool
    - from [here](https://github.com/PSPReverse/em100.git)
    - Compile and install it so that the `em100` binary is available on your `PATH`
    - Remember to install udev rules to `/etc/udev/rules.d/`
- `flashrom` (for reading and re-programming your SPI flash)
    - from [here](https://github.com/flashrom/flashrom.git)
    - Compile and install it so that the `flashrom` command is available on your `PATH`


## Usage

There are 3 main capabilities provided in this repository: 

1. Compiling a new Speak&Spell 2019-compatible "voice pack."
2. Decoding a SPI Flash Image
3. "Live Tracing" of SPI Flash data access with `python -m spana.live_trace`

Note: 2 and 3 require that you have an extracted Speak&Spell 2019 Flash Image (see below for how to do this with a SPI Flash reader).

### Compiling a new voice pack.

You will need 223 or so numerically-named WAV files (at 10kHz sample rate, currently the code does not do resampling).
You can generate these yourself (by recording yourself saying the words and phrases in `known_phrases.csv`) or use the existing ones in the `voice_packs/snoop_dogg` directory.

To compile:
```shell
$ python -m spana.compile_voice_pack --wav-dir voice_packs/snoop_dogg/
Encoding 224 files in 14 parallel processes...
Allocating...
Relocating...
Saving to compiled_voice_pack.bin
```

Note: The script looks for a 3-digit number (with leading zeros) in the wav filename to map the file to a particular offset table index.  The 3-digit number just has to be somewhere in the filename, before the `.wav` suffix (e.g. `angel_042.wav`, `042_angel.wav`, and `ANG042EL.wav` are all acceptable).

Usage:
```
python -m spana.compile_voice_pack --help
usage: compile_voice_pack [-h] -d WAV_DIR

Build a Speak & Spell flash image from wav files

options:
  -h, --help            show this help message and exit
  -d, --wav-dir WAV_DIR
                        Input search dir for wav files

The directory specified with -d/--wav-dir should contain 223 WAV files (at 10kHz sample rate). Each wav file should have a 3-digit (with leading zeros) number in the filename
(e.g. 042_angel.wav) which indicates which record in the offset table it will be encoded into. See known_phrases.csv for a list of all known Speak&Spell words.
```



### `decoder`
Decodes all of the sound blobs from a 2019 Speak&Spell SPI Flash image into wav files.

Operates on the ORIGINAL_FLASH_IMAGE file by default, or can be specified on command line (run with `--help` for options)

Example:
```shell
$ python -m spana.decode_sounds_to_wav
  wrote decoded_sounds/ss_000_A.wav, enc size:  2944, pcm size: 11178, CR: 3.80
  wrote decoded_sounds/ss_001_B.wav, enc size:  2448, pcm size: 9292, CR: 3.80
  wrote decoded_sounds/ss_002_C.wav, enc size:  2784, pcm size: 10580, CR: 3.80
  wrote decoded_sounds/ss_003_D.wav, enc size:  2192, pcm size: 8188, CR: 3.74
  wrote decoded_sounds/ss_004_E.wav, enc size:  2368, pcm size: 8924, CR: 3.77
  wrote decoded_sounds/ss_005_F.wav, enc size:  2128, pcm size: 8004, CR: 3.76
...
```


### `live_trace` (requires em-100 SPI flash emulator)
Loads an (optionally modified) SPI flash image onto the EM-100 SPI Flash Emulator 

Example:
```shell
$ python -m spana.live_trace -M chipmunk_mode
```


## Extracting a flash image from your own Speak & Spell SPI Flash (for use with `live_trace`)
Due to intellectual property concerns, I do not distribute the 2019 Speak&Spell SPI Flash image here.

However, you can extract your own image from your Speak&Spell using a SPI flash reader.  A good cheap option is the CH341A SPI Flash reader, which is readily available on Amazon, eBay, aliexpress, etc.

The CH341A is compatible with the venerable `flashrom` command on Linux, and modern versions of `flashrom` command support the BoyaMicro SPI flash IC I found inside my unit (although it's possible that Speak&Spells have been produced with other SPI flash chips as well).

```
cd speaknspell_analysis
mkdir -p flash_images
sudo flashrom -p ch341a_spi -c 'XM25QH80B' -r flash_images/ORIGINAL_FLASH_IMAGE
```

Code in this repository which depends on the original flash image assumes you'll place it in `speaknspell_analysis/flash_images/ORIGINAL_FLASH_IMAGE`.

The sha256 sum of the flash image I analyzed previously is: `0da032eae0bd5665ad4f3905d9e16f5b7efc75f04907b26e79f96e74380ce511`.
If your flash image has a different hash, perhaps you've discovered a new version (or check your flash reader for hookup issues).


## I just want Snoop and Spell

To convert your 2019 Speak & Spell into a Snoop & Spell:
1. Desolder the SPI Flash IC
2. Insert into CH341A flash reader
3. (optional) Make a backup as described above in "Extracting a flash image" (you never know)
4. Run the following command (with a recent version of flashrom) to write the Snoop & Spell voice pack to the flash IC:
```
flashrom -p ch341a_spi -c 'XM25QH80B' -w snoop_and_spell.bin
```
5. Re-solder the flash IC into place.
6. Be the envy of all your friends.

## Related Presentations
- As presented at DistrictCon Year 0 (22 Feb 2025): _Hacking Childhood Memories A tale of reverse engineering, audio encodings, and never growing up_


