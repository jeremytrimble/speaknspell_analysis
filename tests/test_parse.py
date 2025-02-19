from spana.parse_trace import CMD_RE, ADDRLINE_RE, parse_read_operations, READ_OP
import re

import os

this_file_dir = os.path.dirname(os.path.normpath(__file__))
TEST_CAP_LOG = os.path.join(this_file_dir, "../../captures/20240728/cap1/cap1.log")

def test1():

    INPUT="Time: 000000.00000000 command # 1      : 0xab - unknown command"
    mobj = CMD_RE.match(INPUT)
    assert mobj is not None
    print(mobj.groupdict())

def test2():
    INPUT="000eb2d0 : 2c 88 30 f4 77 d4 c4 77 d4 50 88 c8 f3 fc ed 0f "
    mobj = ADDRLINE_RE.match(INPUT)
    assert mobj is not None
    print(mobj.groupdict())

def test3():
    print()
    with open(TEST_CAP_LOG) as in_fo:
        read_ops = list(parse_read_operations(in_fo))
    for ro in read_ops:
        #print(f"{ro.command_idx:3d} {ro.timestamp:0.6f} {ro.command:3} {ro.addr:08X} {ro.len:04X}")
        if ro.command == READ_OP:
            print(f"{ro.command_idx:3d} {ro.timestamp:9.6f} {ro.command:3} {ro.addr:08X} {ro.len:5} -- {ro.data[:32].hex()}")
            #print(f"{ro.command_idx} {ro.timestamp} {ro.command} {ro.addr:08X} {ro.len}")
        else:
            print(ro)
    #print(read_ops)
