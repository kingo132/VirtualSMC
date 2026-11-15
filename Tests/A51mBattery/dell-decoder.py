#!/usr/bin/env python3
"""Exercise the real cached-data decoder with private identifier fixtures."""
import importlib.util
import pathlib
import struct
import sys
sys.dont_write_bytecode=True
root=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('decoder',root/'Tools/dump_a51m_dell.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
data=bytearray(1520)
valid=sum(1<<n for n in m.FIELDS)
struct.pack_into('<II4Q6I',data,0,2,7,1,900,100,valid,0x148,29,0,3000,127,31)
struct.pack_into('<Q',data,1512,800)
for n,v in {8:2930,9:12352,10:65536-6710,26:49,28:1234}.items():
    struct.pack_into('<H',data,64+2*n,v)
struct.pack_into('<7H',data,192,123,19500,16900,330,1,2345,330)
struct.pack_into('<H',data,206+12,3)
for i in range(5):
    text=(b'PRIVATE-ID' if i>=3 else b'DELL')
    struct.pack_into('<H',data,220+i*2,len(text))
    data[230+i*256:230+i*256+len(text)]=text
out=m.decode(data)
assert out['battery']['battery_serial']=='[redacted]'
assert out['battery']['current_mA']==-6710 and out['battery']['pack_voltage_mV']==12352
assert out['adapter']['design_power_W']==330 and out['adapter']['available_design_power_W']==330
assert out['adapter']['power_supply_id_valid'] and out['adapter']['ac_present_at_capture']
assert out['adapter']['adapter_serial']=='[redacted]' and out['strings']['eppid']=='[redacted]'
assert 'PRIVATE-ID' not in str(out)
assert m.decode(data,True)['strings']['eppid']=='PRIVATE-ID'
struct.pack_into('<H',data,64+26*2,0x1100)
out=m.decode(data);assert out['battery']['pack_voltage_mV']==123520 and out['battery']['current_mA']==-67100
struct.pack_into('<Q',data,32,valid&~(1<<26))
out=m.decode(data);assert 'pack_voltage_mV' not in out['battery'] and 'current_mA' not in out['battery']
for pos,value in [(0,1),(4,9),(56,128),(60,32)]:
    bad=bytearray(data);struct.pack_into('<I',bad,pos,value)
    try:m.decode(bad)
    except ValueError:pass
    else:raise AssertionError(('invalid layout accepted',pos))
bad=bytearray(data);struct.pack_into('<H',bad,220,257)
try:m.decode(bad)
except ValueError:pass
else:raise AssertionError('invalid string length accepted')
try:m.decode(data[:-1])
except ValueError:pass
else:raise AssertionError('truncated cache accepted')
print('PASS: actual decoder, identifier redaction, signed/scaled units, adapter ratings/flags, timestamps and malformed cache rejection')
