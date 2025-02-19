from spana.offset_table import OffsetTableDb
from spana.file_paths import get_default_image_bytes
import pytest

def test_offset_table():
    db = OffsetTableDb.get_default()

    entry = db.lookup_by_speech('Angel', single_match=True)
    assert entry.idx == 42
    assert entry.sound_data_start_addr == 136416
    
    entry2 = db.lookup_by_speech('Another', single_match=True)
    assert entry2.idx == 43
    assert entry.sound_data_end_addr == entry2.sound_data_start_addr == 140720

    entries = db.lookup_by_speech('*Beep*', single_match=False)
    print(f"{entries=}")

    with pytest.raises(ValueError):
        entry = db.lookup_by_speech('*Beep*', single_match=True)

    img_bytes = db.generate_bytes_for_image()

    default_image_bytes = get_default_image_bytes()

    print(f"generated: {img_bytes[:16].hex()}")
    print(f"default:   {default_image_bytes[:16].hex()}")

    assert default_image_bytes[:len(img_bytes)] == img_bytes

    mod_image_bytes = db.graft_onto_image(default_image_bytes)
    assert mod_image_bytes == default_image_bytes

    # show that we can change the table
    db[42].sound_data_start_addr = entry2.sound_data_start_addr
    mod_image_bytes = db.graft_onto_image(default_image_bytes)
    assert mod_image_bytes != default_image_bytes
    