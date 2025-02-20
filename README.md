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

There are 3 main capabilities provided in this repository: `live_trace`, `decoder` and `encoder`



### `encoder`
Compiles a new 2019 Speak&Spell-compatible voice pack for programming onto your own Speak&Spell SPI Flash IC.

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
```
python -m spana.decode_sounds_to_wav
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
```
python -m spana.live_trace -M chipmunk_mode
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


