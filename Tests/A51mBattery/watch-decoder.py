#!/usr/bin/env python3
import importlib.util,pathlib,struct,sys
sys.dont_write_bytecode=True
root=pathlib.Path(__file__).resolve().parents[2]
sp=importlib.util.spec_from_file_location('watch',root/'Tools/watch_a51m_battery.py')
w=importlib.util.module_from_spec(sp);sp.loader.exec_module(w)
d=bytearray(18000);struct.pack_into('<10Q',d,0,0x315441424d313541,1,35,64,1,1,1,0,0,0)
row=[0]*35;row[0]=1;row[3]=11;row[4]=31404;row[5]=2;row[9]=10;row[21]=31404
struct.pack_into('<35Q',d,80,*row)
out=w.trace_current(d);assert out['high_current_events'][0]['currents_mA']==[0,31404,31404]
row[4]=(65536-31000);row[21]=(-31000)&((1<<64)-1);struct.pack_into('<35Q',d,80,*row)
assert w.trace_current(d)['high_current_events'][0]['currents_mA']==[0,-31000,-31000]
row[4]=6700;row[21]=6700;struct.pack_into('<35Q',d,80,*row)
assert not w.trace_current(d)['high_current_events']
try:w.trace_current(d[:-1])
except ValueError:pass
else:raise AssertionError('truncated trace accepted')
print('PASS: actual cached trace decoder detects signed current excursions without hardware access')
