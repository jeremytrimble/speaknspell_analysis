import os
import sys

this_file_dir = os.path.dirname(os.path.normpath(__file__))
ORIGINAL_BINARY = os.path.join(this_file_dir, "../../flash_images/ORIGINAL_FLASH_IMAGE")
KNOWN_PHRASES_CSV = os.path.join(this_file_dir, "known_phrases.csv")

class OriginalFlashImageNotFoundError(Exception):
    pass


def get_default_image_bytes() -> bytes:
    try:
        with open(ORIGINAL_BINARY, "rb") as in_fo:
            FDATA = in_fo.read()
        return FDATA
    except FileNotFoundError:
        raise OriginalFlashImageNotFoundError(
            f"This action depends on a Speak&Spell SPI Flash Image file being available,\n"
            f"but no image file was found at {ORIGINAL_BINARY}.\n"
            f"  Please follow the instructions in the README to extract a usable flash image.\n"
        )