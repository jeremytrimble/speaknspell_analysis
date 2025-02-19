
import dataclasses
import typing
import re

SPI_FLASH_READ = READ_OP = 0x3

@dataclasses.dataclass
class SPIFlashOperation:
    command: int
    command_str: str
    timestamp: float
    command_idx: int
    addr: int
    len: int
    data: bytearray

CMD_RE = re.compile(r"^Time:\s+(?P<timestamp>\S+)\s+command\s+#\s+(?P<command_idx>\S+)\s+:\s+(?P<command_val>\S+)\s+-\s+(?P<command_name>.+)")
ADDRLINE_RE = re.compile(r"^(?P<addr>[0-9A-Fa-f]+)\s+:\s+(?P<data>[0-9a-fA-F ]*)")

def parse_read_operations(in_fo):
    op_in_progress = None

    def new_op(gd):
        return SPIFlashOperation(
            command = int(gd['command_val'],16),
            command_str = gd['command_name'],
            timestamp = float(gd['timestamp']),
            command_idx = int(gd['command_idx']),
            addr = None,
            len=0,
            data=bytearray(),
        )

    def finalize_for_emit(sfo):
        sfo.len = len(sfo.data)
        return sfo

    for lineno,line in enumerate(in_fo,1):
        line = line.strip()
        cmd_mobj = CMD_RE.match(line)
        if cmd_mobj:
            if op_in_progress is not None:
                yield finalize_for_emit(op_in_progress)
            op_in_progress = new_op(cmd_mobj.groupdict())

        else:
            if op_in_progress is not None:
                addr_mobj = ADDRLINE_RE.match(line)
                if addr_mobj:
                    addr_str = addr_mobj.groupdict()['addr']
                    data_str = addr_mobj.groupdict()['data']
                    addr = int(addr_str,16)
                    data = bytes.fromhex(data_str)
                    if op_in_progress.addr is None:
                        op_in_progress.addr = addr
                    else:
                        expected_addr = op_in_progress.addr + len(op_in_progress.data)
                        if addr != expected_addr:
                            raise ValueError(f"at line {lineno}: expected address 0x{expected_addr:08x} but got 0x{addr:08x}: {line}")
                    op_in_progress.data += data
                        

            # TODO: write more here!

    if op_in_progress is not None:
        yield finalize_for_emit(op_in_progress)

