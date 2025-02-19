from spana.util import TempFileMgr
from spana.parse_trace import parse_read_operations
from spana.offset_table import OffsetTableDb, OffsetTableEntry
import typing

import subprocess
import os

from contextlib import closing

from spana.file_paths import KNOWN_PHRASES_CSV, get_default_image_bytes

EM100_CMD = "em100"
CHIP="BY25D80"

def main():
    F_ORIG = get_default_image_bytes()
    oft = OffsetTableDb.from_flash_image(F_ORIG)
    #beep_otes = oft.lookup_by_speech("*Beep*")
    #beep_otes = oft.lookup_by_speech("*as in two*")
    #beep_otes = oft[0:26]
    #beep_otes = oft[192:193]
    beep_otes = oft.lookup_by_speech("Press Go to Begin")
    if not beep_otes:
        raise ValueError("no entries returned!")

    for ote in beep_otes:
        byts = F_ORIG[ ote.sound_data_start_addr:ote.sound_data_end_addr ]

        with open(f"sound_data_{ote.idx:03d}_{ote.speech or ''}.bin", "wb") as out_fo:
            out_fo.write(byts)



if __name__ == "__main__":
    main()