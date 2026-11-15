#!/usr/bin/env python3
import importlib.util
import pathlib
import struct
import sys
sys.dont_write_bytecode = True
path = pathlib.Path(__file__).resolve().parents[2] / 'Tools/dump_a51m_adapters.py'
spec = importlib.util.spec_from_file_location('adapters', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
legacy = bytearray(1520)
struct.pack_into('<II', legacy, 0, 2, 7)
struct.pack_into('<I', legacy, 56, 72)
struct.pack_into('<H', legacy, 198, 480)
struct.pack_into('<H', legacy, 204, 330)
struct.pack_into('<H', legacy, 218, 3)
struct.pack_into('<Q', legacy, 1512, 1)
dual = bytearray(struct.pack('<IIQQ10IQ', 1, 6, 1, 1, 2, 2, 240, 240, 1, 3, 5, 0, 1000, 0, 1))
obj = {'A51mDellTelemetry': legacy, 'A51mDualAdapterTelemetry': dual}
decoded = module.decode(obj, 2)
assert decoded['total_rated_W'] == 480 and decoded['port_1_rated_W'] == decoded['port_2_rated_W'] == 240
assert module.decode(obj, 120_000_000_002)['total_rated_W'] is None
for offset, value in [(24, 1), (28, 1), (32, 65535), (36, 0), (40, 9), (44, 0)]:
    bad = bytearray(dual)
    struct.pack_into('<I', bad, offset, value)
    assert module.decode(dict(obj, A51mDualAdapterTelemetry=bad), 2)['port_1_rated_W'] is None
for offset, fmt, value in [(56, '<I', 64), (198, '<H', 0), (218, '<H', 1)]:
    bad = bytearray(legacy)
    struct.pack_into(fmt, bad, offset, value)
    decoded = module.decode(dict(obj, A51mDellTelemetry=bad), 2)
    assert decoded['total_rated_W'] is None and decoded['port_1_rated_W'] is None
bad_source = bytearray(dual)
struct.pack_into('<Q', bad_source, 64, 2)
assert module.decode(dict(obj, A51mDualAdapterTelemetry=bad_source), 2)['port_1_rated_W'] is None
for bad in [b'', dual[:-1], bytes([2]) + dual[1:]]:
    try:
        module.decode(dict(obj, A51mDualAdapterTelemetry=bad), 2)
    except ValueError:
        pass
    else:
        raise AssertionError('Malformed record accepted')
print('PASS: dual rating decoder, dynamic/static distinction, expiry, single-source ambiguity and malformed records; no identifiers exported')
