#!/usr/bin/env python3
"""Compile actual protocol/reader code against owned ACPI endpoint fixtures."""
import pathlib
import subprocess
import tempfile
import sys
sys.dont_write_bytecode=True
ROOT=pathlib.Path(__file__).resolve().parents[2]
TESTS=ROOT/'Tests/A51mBattery'
with tempfile.TemporaryDirectory(prefix='a51m-dell-tests-') as tmp:
    p=pathlib.Path(tmp)
    for header in ['IOKit/acpi/IOACPIPlatformDevice.h','Headers/kern_time.hpp']:
        target=p/header;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text('#include "'+str(TESTS/'dell-host-stubs.hpp')+'"\n')
    for name in ['dell-protocol','dell-reader','dell-metadata','dual-adapter']:
        target=p/name
        subprocess.run(['/usr/bin/clang++','-std=c++17','-Wall','-Wextra','-Werror',
                        '-fsanitize=undefined','-fno-omit-frame-pointer',
                        '-I',str(p),'-I',str(ROOT),str(TESTS/(name+'.cpp')),
                        '-o',str(target)],check=True)
        subprocess.run([str(target)],check=True)
