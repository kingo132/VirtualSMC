#!/usr/bin/env python3
"""Exercise authenticated Apple decision instructions on owned fixtures only.

Does not load a KEXT, open an SMC client or touch power hardware. Calls into
Apple/kernel objects are replaced by fixture callbacks. This is not live
startup, polling or UI acceptance. Requires the exact tested Intel image.
"""
import argparse
import ctypes as C
import hashlib
import json
import mmap
from pathlib import Path
import platform
import struct
import subprocess
import tempfile


UUID = '9d502381bc1e306695e3caab88af873e'


class Image:
    def __init__(self, data):
        self.data = data
        header = struct.unpack_from('<8I', data)
        assert header[0] == 0xfeedfacf
        cursor, self.segments, actual = 32, [], None
        for _ in range(header[4]):
            cmd, size = struct.unpack_from('<II', data, cursor)
            if cmd == 0x19:
                self.segments.append(struct.unpack_from('<II16sQQQQIIII', data, cursor)[3:7])
            if cmd == 0x1b:
                actual = data[cursor+8:cursor+24].hex()
            cursor += size
        assert actual == UUID, 'Unknown Apple driver UUID; refusing execution'

    def offset(self, address):
        for va, _, offset, size in self.segments:
            if va <= address < va + size:
                return offset + address - va
        raise ValueError('Address outside file-backed segments')

    def span(self, start, end, digest):
        raw = self.data[self.offset(start):self.offset(end)]
        assert hashlib.sha256(raw).hexdigest() == digest, 'Unknown code span'
        return raw


class Executable:
    def __init__(self, code, prototype):
        assert len(code) <= mmap.PAGESIZE
        self.memory = mmap.mmap(-1, mmap.PAGESIZE, prot=mmap.PROT_READ | mmap.PROT_WRITE)
        self.memory.write(code)
        address = C.addressof(C.c_char.from_buffer(self.memory))
        system = C.CDLL('/usr/lib/libSystem.B.dylib')
        system.mprotect.argtypes = [C.c_void_p, C.c_size_t, C.c_int]
        assert system.mprotect(address, mmap.PAGESIZE, mmap.PROT_READ | mmap.PROT_EXEC) == 0
        self.call = prototype(address)


def startup(image):
    start, end = 0x244b, 0x24ea
    raw = image.span(start, end, '7b6457c5e8e826a1b2d9d35515122b87c09f43557c7230035fcee435fad2d93b')
    state = {}

    @C.CFUNCTYPE(C.c_ubyte, C.c_void_p, C.c_uint32, C.c_uint64, C.c_void_p)
    def read_key(_ctx, key, capacity, output):
        if key != 0x424e4342 or capacity != 8:
            state['callback_errors'].append('Unexpected read-key request')
            return 0x84
        if state['bncb'] is None:
            return 0x84
        # Model a one-byte SMC value copied into the native zeroed buffer.
        C.c_ubyte.from_address(output).value = state['bncb']
        return 0

    @C.CFUNCTYPE(C.c_ubyte, C.c_void_p, C.c_uint32, C.c_void_p)
    def key_info(_ctx, key, _output):
        state['probes'] += 1
        return 0 if key in state['keys'] else 0x84

    @C.CFUNCTYPE(None, C.c_void_p, C.c_bool)
    def installed(_ctx, value):
        state['installed'] = bool(value)

    vtable = (C.c_void_p * 277)()
    vtable[276] = C.cast(key_info, C.c_void_p).value
    provider = (C.c_void_p * 1)()
    provider[0] = C.addressof(vtable)
    # Supply an owned frame/context; preserve all used callee-saved registers.
    prefix = bytes.fromhex('554889e5534154415641574883ec404889fb')
    suffix = bytes.fromhex('4883c440415f415e415c5b5dc3')
    code = bytearray(prefix + raw + suffix)
    for address, callback in [(0x2463, read_key), (0x24e5, installed)]:
        stub = len(code)
        code += b'\x49\xbb' + struct.pack('<Q', C.cast(callback, C.c_void_p).value) + b'\x41\xff\xe3'
        at = len(prefix) + address - start
        assert code[at] == 0xe8
        code[at+1:at+5] = struct.pack('<i', stub-at-5)
    native = Executable(code, C.CFUNCTYPE(None, C.c_void_p))
    rows = []
    cases = [('previous-compatible', None, [0x42433156], 1),
             ('a51m2-regression', None, [], 0),
             ('independent-slot-descriptor', 1, [], 1),
             ('no-slots', 0, [], 0)]
    cases += [(f'explicit-{n}', n, [], n) for n in [2, 3, 4]]
    for name, count, keys, expected in cases:
        state.clear()
        state.update(bncb=count, keys=keys, probes=0, installed=None, callback_errors=[])
        context = C.create_string_buffer(0x400)
        address = C.addressof(context)
        C.c_void_p.from_address(address+0x1a8).value = C.addressof(provider)
        native.call(address)
        assert not state['callback_errors']
        actual = C.c_uint64.from_address(address+0x218).value
        assert actual == expected and state['installed'] == bool(expected)
        rows.append({'case': name, 'slots': actual, 'installed': state['installed'],
                     'key_info_queries': state['probes']})
    return rows


def optional_key(image):
    start = 0x59b5
    raw = image.span(start, 0x59d2, 'eb2a62aca9d434fce6e153b06560cdca015314ec5bbcd89d646c7c5809244fc1')
    code = bytearray(b'\x40\x88\xf8' + raw)
    stubs = len(code)
    for action in range(4):
        code += b'\xb8' + struct.pack('<I', action) + b'\xc3'
    for address, action in [(0x59b7, 0), (0x59c5, 1), (0x59ca, 2), (0x59d0, 3)]:
        at, target = 3 + address-start, stubs + 6*action
        if code[at:at+2] == b'\x0f\x84':
            code[at+2:at+6] = struct.pack('<i', target-at-6)
        else:
            assert code[at] in (0x74, 0xeb)
            code[at+1:at+2] = struct.pack('b', target-at-2)
    native = Executable(code, C.CFUNCTYPE(C.c_int, C.c_ubyte))
    for value in range(256):
        assert native.call(value) == {0: 0, 0x84: 1, 0x10: 2}.get(value, 3)
    return 256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('driver', type=Path)
    args = parser.parse_args()
    if platform.system() != 'Darwin' or platform.machine() != 'x86_64':
        raise SystemExit('Requires Intel macOS; no execution on another platform')
    with tempfile.TemporaryDirectory(prefix='a51m-native-owned-') as folder:
        thin = Path(folder)/'driver'
        subprocess.run(['/usr/bin/lipo', str(args.driver), '-thin', 'x86_64', '-output', str(thin)], check=True)
        image = Image(thin.read_bytes())
    print(json.dumps({'uuid': UUID, 'startup_cases': startup(image),
                      'optional_status_inputs': optional_key(image),
                      'kernel_or_hardware_calls': False,
                      'live_startup_and_UI_acceptance': False}, indent=2))


if __name__ == '__main__':
    main()
