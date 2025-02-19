from spana.encoder import nibble_to_signed, header_bits
import pytest

def test_header_bits():
    assert header_bits(g=0, keep_going=True)  == 0b0001
    assert header_bits(g=1, keep_going=True)  == 0b1001
    assert header_bits(g=1, keep_going=False) == 0b1000

    assert header_bits(g=2, keep_going=True)  == 0b0101
    assert header_bits(g=2, keep_going=False) == 0b0100

    assert header_bits(g=3, keep_going=True) == 0b1101

    assert header_bits(g=6, keep_going=False) == 0b0110

    with pytest.raises(Exception):
        header_bits(g=7, keep_going=True)




def test_nts():
    assert nibble_to_signed(0) == 0
    assert nibble_to_signed(7) == 7
    assert nibble_to_signed(8) == -8
    assert nibble_to_signed(15) == -1