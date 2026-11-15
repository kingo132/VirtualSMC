#!/usr/bin/env python3
"""Test the actual static capture block with numeric/string ACPI fixtures."""
import importlib.util
import pathlib
import struct
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

ROOT = pathlib.Path(__file__).resolve().parents[2]
source = (ROOT / 'Sensors/SMCBatteryManager/ACPIBattery.cpp').read_text()
a = source.index('\tif (a51mObserve) {')
b = source.index('\n\tif (extended) {', a)
capture = source[a:b]
cpp = r'''
#include "Sensors/SMCBatteryManager/A51mBatteryStaticInfo.hpp"
#include <cassert>
#include <cstdio>
struct BatteryInfo {
    static constexpr uint32_t ValueUnknown = 0xffffffff;
    A51mBattery::StaticInfo a51mStaticInfo {};
};
struct Package { uint32_t count; uint32_t getCount() {return count;} };
uint32_t getNumberFromArray(Package *p, uint32_t i) {
    return i < p->count ? (i == 8 ? 321 : i + 100) : 0xffffffff;
}
BatteryInfo run(bool a51mObserve, bool extended, uint32_t count) {
    BatteryInfo bi; Package package {count}; auto info = &package;
    CAPTURE
    return bi;
}
int main() {
    for (bool observe : {false,true}) for (bool extended : {false,true})
        for (uint32_t count : {0U,3U,13U,20U}) {
            auto raw=run(observe,extended,count).a51mStaticInfo;
            assert(raw.method == (observe ? (extended?2U:1U) : 0U));
            if (!observe) continue;
            assert(raw.packageCount == count);
            for(uint32_t i=0;i<16;++i) {
                uint32_t expected=(i<(extended?16U:9U) && i<count)?(i==8?321:i+100):0xffffffff;
                assert(raw.values[i]==expected);
            }
        }
    puts("PASS: 16 actual capture fixtures; observation off/on; BIF/BIX; truncated packages; no identifying fields");
}'''.replace('CAPTURE', capture).replace('#include <cstdio>', '#include <cstdio>\n#include <initializer_list>')
with tempfile.TemporaryDirectory(prefix='a51m-static-test-') as t:
    p=pathlib.Path(t); (p/'test.cpp').write_text(cpp)
    subprocess.run(['/usr/bin/clang++','-std=c++17','-Wall','-Wextra','-Werror',
                    '-fsanitize=undefined','-I',str(ROOT),str(p/'test.cpp'),'-o',str(p/'test')], check=True)
    subprocess.run([str(p/'test')],check=True)
spec=importlib.util.spec_from_file_location('static_decoder',ROOT/'Tools/dump_a51m_battery_static.py')
decoder=importlib.util.module_from_spec(spec);spec.loader.exec_module(decoder)
for method,count in [(1,13),(2,20)]:
    for cycle in [0,321,0xffffffff]:
        values=[0]*16;values[8]=cycle
        result=decoder.decode(struct.pack('<18I',method,count,*values))
        assert result['cycle_count_source_available'] == (method==2 and cycle!=0xffffffff)
        assert result['cycle_count_zero_requires_independent_validation'] == (method==2 and cycle==0)
for invalid in [b'',bytes(71),struct.pack('<18I',3,20,*([0]*16))]:
    try: decoder.decode(invalid)
    except ValueError: pass
    else: raise AssertionError('Malformed static information accepted')
print('PASS: decoder BIF/BIX, real/zero/unknown cycle values and malformed data')
