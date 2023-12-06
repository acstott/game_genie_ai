#!/usr/bin/python3

import random
import struct, os

hexcodes = list('ABCDEFGHI')
codes = {v: k for k, v in enumerate(hexcodes)}




def addr_data_to_code(addr, data, compare=False):
    base = addr - 0x8000
    n = [0] * (9 if compare is not False else 6)
    # Address
    n[3] |= (base >> 12) & 7
    n[5] |= (base >> 8) & 7
    n[4] |= (base >> 8) & 8
    n[2] |= (base >> 4) & 7
    n[1] |= (base >> 4) & 8
    n[4] |= base & 7
    n[3] |= base & 8
    # Data
    n[1] |= (data >> 4) & 7
    n[0] |= (data >> 4) & 8
    n[0] |= (data & 7)
    if compare is not False:
        n[2] |= 8
        n[7] |= data & 8
        # Compare
        n[7] |= (compare >> 4) & 7
        n[6] |= (compare >> 4) & 8
        n[6] |= compare & 7
        n[5] |= compare & 8
    else:
        n[5] |= data & 8
    return ''.join(map(lambda x: hexcodes[x], n))


def code_to_data_addr(code):
    n = list(map(lambda x: codes[x], list(code)))
    address = 0x8000 + (
            ((n[3] & 7) << 12)
            | ((n[5] & 7) << 8) | ((n[4] & 8) << 8)
            | ((n[2] & 7) << 4) | ((n[1] & 8) << 4)
            | (n[4] & 7) | (n[3] & 8)
    )
    data = (
            ((n[1] & 7) << 4) | ((n[0] & 8) << 4)
            | (n[0] & 7)
    )
    compare = None
    if len(code) == 8:
        data |= n[7] & 8
        compare = (
                ((n[7] & 7) << 4) | ((n[6] & 8) << 4)
                | (n[6] & 7) | (n[5] & 8)
        )
        return hex(address), data, compare
    else:
        data |= n[5] & 8
        return hex(address), data


def random_code():
    return addr_data_to_code(random.randint(0, (1 << 16) - 1),
                             random.randint(0, 255))



def guess_safer_code(code, rom_path):
    rom = open(rom_path, 'rb')
    header = _read_rom_header(rom.read(16))
    addr, code = code_to_data_addr(code)
    addr = int(addr, 16)
    codes_set = set()
    root = header['offset'] + addr
    for x in range(header['prg_banks']):
        rom.seek(((x - 1) * 16384) + root, os.SEEK_SET)
        byte = rom.read(1)
        if byte == '':
            break
        codes_set.add(addr_data_to_code(addr, code))
    root = header['offset'] + (addr & 0x1FFF) + (16384 * header['prg_banks'])
    for x in range(header['chr_banks']):
        rom.seek(((x - 1) * 8192) + root, os.SEEK_SET)
        byte = rom.read(1)
        if byte == '':
            break
        codes_set.add(addr_data_to_code(addr, code))
    return codes


def guess_based_on_char(char, rom_path, write=200, harder=False, short=False):
    rom = open(rom_path, 'r')
    header = _read_rom_header(rom.read(16))
    if type(char) is not str:
        char = chr(char)
    codes_set = set()
    buffer = []
    targets = [
        [['\xa9', char, '\x8d'], 1],  # LDA Immediate, STA Absolute
        [['\xa9', char, '\x85'], 1],  # LDA Immediate, STA Zero Page
    ]
    if False and harder:
        targets.extend([
            [['\xa2', char, '\x86'], 1],  # LDX Immediate, STX Zero Page
            [['\xa0', char, '\x84'], 1],  # LDY Immediate, STY Zero Page
            [['\xa0', char, '\x8c'], 1],  # LDY Immediate, STY Absolute
            [['\xa2', char, '\x8e'], 1],  # LDX Immediate, STX Absolute
        ])
    rom.seek(header['offset'], os.SEEK_SET)
    for b in range(16384 * header['prg_banks']):
        buffer.append(rom.read(1))
        if len(buffer) > 16:
            buffer.pop(0)
        for T, offset in targets:
            if T == buffer[-len(T):]:
                codes_set.add(addr_data_to_code((b % 65536) - offset, write,
                                                ord(char) if not short else False))
    if not len(codes_set) > 0 and not harder:
        return guess_based_on_char(char, rom_path, write, True)
    return codes_set




def _read_rom_header(header):
    head = struct.unpack('BBBBBB', header[4:10])
    trainer = head[2] & 0x04;
    print(head, trainer)
    return {
        'prg_banks': head[0],
        'chr_banks': head[1],
        'offset': 16 + (512 if trainer else 0),
    }