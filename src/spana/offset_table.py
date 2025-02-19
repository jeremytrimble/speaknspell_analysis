
from spana.file_paths import KNOWN_PHRASES_CSV, get_default_image_bytes
import pandas as pd
import numpy as np
import dataclasses
import typing
import struct
import random

PRESUMED_OFFSET_TABLE_LENGTH = 223          # TODO: fix this -- it's really driven from the first byte in the image
PRESUMED_OFFSET_TABLE_BASE_ADDRESS = 0xB

import fnmatch 

def nan_to_none(maybe_nan):
    if isinstance(maybe_nan, float):
        if np.isnan(maybe_nan):
            return None
    return maybe_nan


@dataclasses.dataclass
class OffsetTableEntry:
    idx: int
    rate_divider: int
    sound_data_start_addr: int                  # inclusive, Python-style
    sound_data_end_addr: typing.Optional[int]   # exclusive, Python-style
    speech: typing.Optional[str]

    @property
    def sample_rate_Hz(self):
        return 2e6/self.rate_divider

    @sample_rate_Hz.setter
    def sample_rate_Hz(self, new_sample_rate_Hz:float):
        assert(new_sample_rate_Hz > 0)
        self.rate_divider = int(round(2e6/new_sample_rate_Hz))

def ew_print(msg:str):
    print(f"  OffsetTable parse warning: {msg}")

def check_expected_value(expected:bytes, observed:bytes, description:str):
    """ Used to provide commentary on unexpected field values...  """
    if expected != observed:
        ew_print(f"for field: {description}: expected {expected.hex()} but observed {observed.hex()}")

class OffsetTableDb:
    def __init__(self, entries):
        self._offset_table_entries : typing.List[OffsetTableEntry] = entries

    def __getitem__(self, indexer) -> typing.Union[OffsetTableEntry, typing.Sequence[OffsetTableEntry]]:
        return self._offset_table_entries[indexer]

    def __setitem__(self, indexer, new_items):
        self._offset_table_entries[indexer] = new_items

    def get_by_idx(self, idx:int) -> OffsetTableEntry:
        return self._offset_table_entries[idx]

    def __len__(self) -> int:
        return len(self._offset_table_entries)

    def __iter__(self):
        return iter(self._offset_table_entries)

    def lookup_by_speech_data_address(self, speech_data_address:int) -> OffsetTableEntry:
        for entry in self._offset_table_entries:
            if entry.sound_data_start_addr <= speech_data_address:
                if (entry.sound_data_end_addr is None) or (speech_data_address < entry.sound_data_end_addr):
                    return entry

    def lookup_by_speech(self, speech_pattern:str, single_match=False) -> typing.Union[OffsetTableEntry, typing.Sequence[OffsetTableEntry]]:
        matches = []
        for entry in self._offset_table_entries:
            if entry.speech is not None:
                if fnmatch.fnmatch(entry.speech, speech_pattern):
                    matches.append(entry)
        if single_match:
            if len(matches) < 1:
                raise ValueError(f"no match for pattern: \"{speech_pattern}\"")
            elif len(matches) > 1:
                raise ValueError(f"multiple matches for pattern: \"{speech_pattern}\": {matches}")
            else:
                return matches[0]
        else:
            return matches

    def generate_bytes_for_image(self, entry_prefix_bytes=None) -> bytes:

        ba = bytearray(
            bytes.fromhex("00e0")+
            PRESUMED_OFFSET_TABLE_BASE_ADDRESS.to_bytes(length=3, byteorder="big") +    # OFFSET_TABLE_BASE
            (0x0b + 5*(PRESUMED_OFFSET_TABLE_LENGTH+1)).to_bytes(length=3, byteorder="big") + # OFFSET_TABLE_END
            (0x0b + 5*(PRESUMED_OFFSET_TABLE_LENGTH+1)).to_bytes(length=3, byteorder="big")   # SOMETHING_ELSE_PTR
        )

        for entry in self._offset_table_entries:
            rd_bytes = int.to_bytes(entry.rate_divider, length=2, byteorder="big")
            ba.extend( rd_bytes + entry.sound_data_start_addr.to_bytes(length=3, byteorder="big"))

        return bytes(ba)

    def graft_onto_image(self, FDAT:bytes, entry_prefix_bytes=None):
        FMOD = bytearray(FDAT)
        del FDAT
        new_bytes = self.generate_bytes_for_image(entry_prefix_bytes)
        FMOD[:len(new_bytes)] = new_bytes
        return bytes(FMOD)

    @classmethod
    def get_default(cls):
        FDATA = get_default_image_bytes()
        return cls.from_flash_image(FDATA)

    @classmethod
    def from_flash_image(cls, FDATA: bytes, offset_table_length:int=PRESUMED_OFFSET_TABLE_LENGTH):
        entries = []

        check_expected_value( bytes.fromhex("00e0"), FDATA[0:2], "initial header" )
        check_expected_value( bytes.fromhex("00000b"), FDATA[2:5], "offset table base address" )

        offset_table_idx_to_speech = {}
        if 1:
            df = pd.read_csv(KNOWN_PHRASES_CSV)
            offset_table_idx_to_speech = dict([ (row['offset_table_idx'], nan_to_none(row['speech'])) for idx,row in df.iterrows()])

        for offset_table_idx in range(offset_table_length):
            offset_entry_addr = 0xb + 5*offset_table_idx
            offset_entry_data = FDATA[offset_entry_addr: offset_entry_addr + 5]

            rate_divider = int.from_bytes(offset_entry_data[0:2], byteorder="big")

            #print(f" {offset_table_idx=:3d} {offset_entry_addr=:4d} {offset_entry_addr=:05x}  {offset_entry_data.hex()=}")

            sound_data_start_addr = int.from_bytes(offset_entry_data[-3:], byteorder="big")

            if sound_data_start_addr > 0xFFFFF:
                ew_print(f"offset_table_entry (idx {offset_table_idx:3d}) points to 0x{sound_data_start_addr:06X}, past end of flash!")
                entries.append(None)
            else:
                entries.append( OffsetTableEntry(
                    idx = offset_table_idx,
                    rate_divider=rate_divider,
                    sound_data_start_addr  = sound_data_start_addr,
                    sound_data_end_addr=None, # for now
                    speech = offset_table_idx_to_speech.get(offset_table_idx),
                ))

        # fix up "end addr" for each entry
        # this presumes they're in ascending order
        previous_entry :typing.Optional[OffsetTableEntry] = None

        for offset_table_idx in range(offset_table_length):
            entry = entries[offset_table_idx]

            if previous_entry is not None:
                if not( previous_entry.sound_data_start_addr < entry.sound_data_start_addr ):
                    ew_print(f"offset table pointers are not strictly ascending")

                # assume that the previous sound data ends at the preceding byte (may or may not be true)
                # since we are using "python-style" intervals [inclusive, exclusive), set it equal
                previous_entry.sound_data_end_addr = entry.sound_data_start_addr

            previous_entry = entry

        return cls(entries=entries)
