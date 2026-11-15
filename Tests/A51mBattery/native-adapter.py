#!/usr/bin/env python3
"""Run the installed Apple's wattage arithmetic against owned rated V/I only.

No driver loading, SMC client, firmware calls, or changes to the Apple image.
This verifies the modern dictionary's 32-bit path, not the Dell field units.
"""
import ctypes as C
import argparse
import importlib.util
import pathlib
import platform
import subprocess
import sys
import tempfile
sys.dont_write_bytecode=True
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('driver',type=pathlib.Path,
                    help='Local AppleSmartBatteryManager Mach-O; exact UUID and code hashes are required')
args=parser.parse_args()
tests=pathlib.Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('native',tests/'native-startup.py')
n=importlib.util.module_from_spec(sp);sp.loader.exec_module(n)
assert platform.machine()=='x86_64' and platform.system()=='Darwin'
with tempfile.TemporaryDirectory(prefix='a51m-adapter-owned-') as tmp:
    thin=pathlib.Path(tmp)/'driver'
    subprocess.run(['/usr/bin/lipo',str(args.driver),
                    '-thin','x86_64','-output',str(thin)],check=True)
    image=n.Image(thin.read_bytes())
span=image.span(0x6dac,0x6dd7,'5e111ef3161fedf088c4e114ef1f4f25ffb133ea9b38bba29309a0f1db70ce1a')
# Owned stack frame with the two already-read native integer slots; there are
# no calls or external data references in this authenticated arithmetic span.
prefix=bytes.fromhex('554889e54881ecb000000089bd54ffffff89b56cffffff')
suffix=bytes.fromhex('89f8c9c3')
native=n.Executable(prefix+span+suffix,C.CFUNCTYPE(C.c_uint32,C.c_int32,C.c_int32))
for mv,ma,w in [(19500,16923,330),(19500,13333,260),(20000,4500,90),
                (20000,18500,370),(19500,0,0),(0,16923,0)]:
    assert native.call(mv,ma)==w,(mv,ma,w)
print('PASS: exact installed Apple modern adapter arithmetic handles 330/370 W without 8-bit truncation; synthetic rated V/I, Dell units and UI still unverified')
