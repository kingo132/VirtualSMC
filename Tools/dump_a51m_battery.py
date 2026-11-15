#!/usr/bin/env python3
"""Decode the optional read-only A51mBatteryTrace IORegistry property.

No user client, SMBus transaction, setter, privileged helper or service is used.
--input accepts a saved IORegistry XML plist or raw trace data for offline work.
"""
import argparse,json,pathlib,plistlib,struct,subprocess,time

SNAPSHOT_FIELDS = (
    'sequence sample_ns raw_state raw_rate raw_capacity raw_voltage power_unit_is_watt '
    'design_voltage state present_rate average_rate signed_present_rate signed_average_rate '
    'remaining_capacity last_full_charge_capacity upstream_runtime upstream_average_time '
    'upstream_full_time runtime average_time full_time policy_enabled '
    'supplement_config previous_capacity quick_poll hardware_average_rate').split()
RECORD_FIELDS = ('event_sequence event_ns phase command value receive_count '
                 'expected_command expected_value request_sequence').split()


def decode(data):
    if len(data)!=8*(10+64*35):
        raise ValueError('Unexpected trace size')
    magic,version,words,capacity,used,next_index,total,overwritten,dropped,reserved=struct.unpack_from('<10Q',data)
    if (magic,version,words,capacity)!=(0x315441424d313541,1,35,64):
        raise ValueError('Unsupported trace schema')
    if used>64 or next_index!=total%64 or used!=min(total,64) or overwritten!=max(0,total-64) or reserved:
        raise ValueError('Inconsistent trace header')
    events=[]
    start=next_index if used==64 else 0
    for i in range(used):
        values=struct.unpack_from('<35Q',data,80+((start+i)%64)*280)
        row=dict(zip(RECORD_FIELDS,values[:9]))
        source=dict(zip(SNAPSHOT_FIELDS,values[9:]))
        for field in ['signed_present_rate','signed_average_rate','hardware_average_rate']:
            if source[field]>=2**63:source[field]-=2**64
        row['source']=source
        row['phase_name']={1:'prepared',2:'before_native_completion'}.get(row['phase'],'unknown')
        row['reply_changed']=(row['command']!=row['expected_command'] or
                              row['value']!=row['expected_value'] or row['receive_count']!=2)
        if row['command'] in (0x0a,0x0b):
            row['interpreted_current_mA']=row['value']-65536 if row['value']>=32768 else row['value']
        events.append(row)
    if events and [x['event_sequence'] for x in events]!=list(range(total-used+1,total+1)):
        raise ValueError('Inconsistent event ordering')
    pairs={}
    for row in events:pairs.setdefault(row['request_sequence'],set()).add(row['phase'])
    unpaired=sorted(key for key,phases in pairs.items() if phases!={1,2})
    return dict(schema=version,capacity=capacity,used=used,total=total,overwritten=overwritten,
                dropped=dropped,unpaired_request_sequences=unpaired,
                source_missing_events=[x['event_sequence'] for x in events if not x['source']['sequence']],
                events=events)


def find_trace(obj):
    if isinstance(obj,dict):
        if isinstance(obj.get('A51mBatteryTrace'),bytes):return obj['A51mBatteryTrace']
        for value in obj.values():
            result=find_trace(value)
            if result is not None:return result
    elif isinstance(obj,list):
        for value in obj:
            result=find_trace(value)
            if result is not None:return result
    return None


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=pathlib.Path);a=p.parse_args()
    data=a.input.read_bytes() if a.input else subprocess.check_output(
        ['/usr/sbin/ioreg','-a','-r','-c','SMCSMBusController'],timeout=10)
    if not data.startswith(b'A51MBAT1'):
        data=find_trace(plistlib.loads(data))
        if data is None:raise SystemExit('No trace. Observation is optional and disabled by default.')
    result=decode(data);result['capture_wall_epoch']=time.time();result['capture_monotonic_ns']=time.monotonic_ns()
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
