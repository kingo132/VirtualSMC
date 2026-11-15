#!/usr/bin/env python3
"""Deadline-limited, cached IORegistry observation; no power-hardware calls.

No service installation, sleep assertion, configuration write or recovery
action. Saves a minute baseline and new high-current events privately.
"""
import argparse
import ctypes as C
import datetime as D
import json
import pathlib
import platform
import signal
import struct
import time


def trace_current(data):
    if len(data)!=18000:raise ValueError('Unexpected trace length')
    header=struct.unpack_from('<10Q',data)
    magic,schema,words,capacity,used,next_index,total,overwritten,dropped,_=header
    if (magic,schema,words,capacity)!=(0x315441424d313541,1,35,64) or used>64 or next_index>=64:
        raise ValueError('Unexpected trace schema')
    events=[]
    for i in range(used):
        row=struct.unpack_from('<35Q',data,80+i*280)
        def signed(value):return value-(1<<64) if value&(1<<63) else value
        currents=[signed(row[20]),signed(row[21])]
        if row[3] in (10,11) and row[5]==2:
            currents.append((row[4]&65535)-65536 if row[4]&32768 else row[4]&65535)
        if any(abs(v)>=30000 for v in currents):
            events.append({'event_sequence':row[0],'command':row[3],
                           'source_sequence':row[9],'source_raw_state':row[11],
                           'source_raw_rate':row[12],'source_raw_capacity':row[13],
                           'source_previous_capacity':row[32],
                           'source_quick_poll':row[33],'currents_mA':currents})
    return {'total':total,'overwritten':overwritten,'dropped':dropped,'high_current_events':events}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=pathlib.Path,required=True)
    p.add_argument('--until-utc',required=True)
    args=p.parse_args()
    deadline=D.datetime.fromisoformat(args.until_utc.replace('Z','+00:00')).timestamp()
    assert platform.system()=='Darwin' and time.time()<deadline<=time.time()+9*3600
    args.output.mkdir(mode=0o700)
    io=C.CDLL('/System/Library/Frameworks/IOKit.framework/IOKit')
    cf=C.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
    P,U=C.c_void_p,C.c_uint32
    io.IOServiceMatching.argtypes=[C.c_char_p];io.IOServiceMatching.restype=P
    io.IOServiceGetMatchingService.argtypes=[U,P];io.IOServiceGetMatchingService.restype=U
    io.IORegistryEntryCreateCFProperty.argtypes=[U,P,P,U];io.IORegistryEntryCreateCFProperty.restype=P
    io.IOObjectRelease.argtypes=[U]
    cf.CFStringCreateWithCString.argtypes=[P,C.c_char_p,U];cf.CFStringCreateWithCString.restype=P
    cf.CFGetTypeID.argtypes=[P];cf.CFGetTypeID.restype=C.c_ulong
    cf.CFDataGetTypeID.restype=C.c_ulong;cf.CFNumberGetTypeID.restype=C.c_ulong;cf.CFBooleanGetTypeID.restype=C.c_ulong
    cf.CFDataGetLength.argtypes=[P];cf.CFDataGetLength.restype=C.c_long
    cf.CFDataGetBytePtr.argtypes=[P];cf.CFDataGetBytePtr.restype=P
    cf.CFNumberGetValue.argtypes=[P,C.c_int,P];cf.CFNumberGetValue.restype=C.c_bool
    cf.CFBooleanGetValue.argtypes=[P];cf.CFBooleanGetValue.restype=C.c_bool
    cf.CFRelease.argtypes=[P]
    names=['A51mBatteryTrace','Amperage','InstantAmperage','Voltage','CurrentCapacity',
           'MaxCapacity','CycleCount','Temperature','ExternalConnected','IsCharging','TimeRemaining']
    keys={name:cf.CFStringCreateWithCString(None,name.encode(),0x08000100) for name in names}
    assert all(keys.values())
    def service(name):return io.IOServiceGetMatchingService(0,io.IOServiceMatching(name.encode()))
    def value(handle,name):
        if not handle:return None
        obj=io.IORegistryEntryCreateCFProperty(handle,keys[name],None,0)
        if not obj:return None
        try:
            kind=cf.CFGetTypeID(obj)
            if kind==cf.CFDataGetTypeID():
                n=cf.CFDataGetLength(obj)
                if 0<=n<=20000:return C.string_at(cf.CFDataGetBytePtr(obj),n)
            if kind==cf.CFBooleanGetTypeID():return bool(cf.CFBooleanGetValue(obj))
            if kind==cf.CFNumberGetTypeID():
                number=C.c_int64()
                return number.value if cf.CFNumberGetValue(obj,4,C.byref(number)) else None
        finally:cf.CFRelease(obj)
        return None
    running=True
    def stop(*_):
        nonlocal running
        running=False
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    last_total,last_saved,last_high=0,0,0
    summary={'deadline_utc':args.until_utc,'started_utc':D.datetime.now(D.timezone.utc).isoformat(),
             'reads':0,'baseline_files':0,'high_current_files':0,'trace_records_missed_between_reads':0,
             'read_errors':0,'hardware_calls':False,'service_installed':False,'identifiers_recorded':False}
    log=(args.output/'timeline.ndjson').open('x');controller=battery=0
    try:
        controller=service('SMCSMBusController');battery=service('AppleSmartBattery')
        while running and time.time()<deadline:
            now=time.time();raw=value(controller,'A51mBatteryTrace')
            native={k:value(battery,k) for k in names[1:]}
            summary['reads']+=1
            try:decoded=trace_current(raw) if raw else None
            except ValueError:decoded=None;summary['read_errors']+=1
            if decoded:
                if decoded['total']>=last_total:
                    summary['trace_records_missed_between_reads']+=max(0,decoded['total']-last_total-64) if last_total else 0
                last_total=decoded['total']
            events=[e for e in decoded['high_current_events'] if e['event_sequence']>last_high] if decoded else []
            high=bool(events) or any(isinstance(native.get(k),int) and abs(native[k])>=30000 for k in ['Amperage','InstantAmperage'])
            if events:last_high=max(e['event_sequence'] for e in events)
            if high or now-last_saved>=60:
                row={'epoch':now,'utc':D.datetime.now(D.timezone.utc).isoformat(),'native_cached':native,
                     'new_high_current_events':events,'trace_total':decoded['total'] if decoded else None}
                if raw:
                    name=f'{now:.3f}-'+('high' if high else 'baseline')+'.trace.bin'
                    (args.output/name).write_bytes(raw);row['trace_file']=name
                log.write(json.dumps(row)+'\n');log.flush();last_saved=now
                summary['high_current_files' if high else 'baseline_files']+=1
            time.sleep(min(2,max(0,deadline-time.time())))
    finally:
        if controller:io.IOObjectRelease(controller)
        if battery:io.IOObjectRelease(battery)
        for key in keys.values():cf.CFRelease(key)
        log.close();summary['ended_utc']=D.datetime.now(D.timezone.utc).isoformat()
        summary['completed_deadline']=time.time()>=deadline
        (args.output/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary))


if __name__=='__main__':main()
