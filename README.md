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

### `decoder`
Decodes all of the sound blobs from a 2019 Speak&Spell SPI Flash image into wav files.

Example:
```

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


## Related Presentations
- As presented at DistrictCon Year 0 (22 Feb 2025): _Hacking Childhood Memories A tale of reverse engineering, audio encodings, and never growing up_


