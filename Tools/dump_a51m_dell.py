#!/usr/bin/env python3
"""Read cached Dell telemetry; never invokes ACPI, SMI, MMIO or a setter.

Identifiers are redacted by default. --include-identifiers is for local use.
"""
import argparse
import json
import pathlib
import plistlib
import struct
import subprocess

FIELDS={0:'manufacturer_access_raw',3:'battery_mode_raw',8:'temperature_dK',
        9:'pack_voltage_raw',10:'current_raw_u16',13:'relative_charge_percent',
        15:'remaining_capacity_raw',16:'full_capacity_raw',22:'battery_status_raw',
        23:'cycle_count',24:'design_capacity_raw',25:'design_voltage_raw',
        26:'specification_raw',27:'manufacturing_date_raw',28:'battery_serial',
        45:'battman_capability_raw'}
STATUS=['disabled','not_captured','no_endpoint','invalid_descriptor','bad_signature',
        'transport_error','slow_transport_disabled','active']


def decode(data, identifiers=False):
    if len(data)!=1520:
        raise ValueError('Unexpected Dell telemetry size')
    schema,status,sequence,sampled,static_sampled,valid,spec,requests,failures,max_us,adapters,strings=struct.unpack_from('<II4Q6I',data)
    if schema!=2 or status>=len(STATUS) or adapters>127 or strings>31 or struct.unpack_from('<H',data,1510)[0]:
        raise ValueError('Unsupported Dell telemetry layout')
    if valid&~sum(1<<n for n in FIELDS):
        raise ValueError('Unrecognized numeric field validity mask')
    raw=struct.unpack_from('<64H',data,64)
    numbers={name:(('[redacted]' if n==28 and not identifiers else raw[n])
                   if valid&(1<<n) else None) for n,name in FIELDS.items()}
    if numbers['temperature_dK'] is not None:
        numbers['temperature_C']=round(raw[8]/10-273.15,2)
    if numbers['specification_raw'] is not None:
        vscale=(raw[26]>>8)&15;iscale=(raw[26]>>12)&15
        numbers['voltage_scale_exponent']=vscale
        numbers['current_capacity_scale_exponent']=iscale
        # Retain arbitrary vendor scale nibbles as raw data; do not invent
        # engineering units for unsupported exponents.
        if vscale<=3:
            for n,key in [(9,'pack_voltage_mV'),(25,'design_voltage_mV')]:
                if valid&(1<<n):numbers[key]=raw[n]*10**vscale
        if iscale<=3 and valid&(1<<10):
            signed=raw[10]-65536 if raw[10]>=32768 else raw[10]
            numbers['current_mA']=signed*10**iscale
    ax=struct.unpack_from('<7H',data,192);bx=struct.unpack_from('<7H',data,206)
    lengths=struct.unpack_from('<5H',data,220)
    texts={}
    for i,name in enumerate(['manufacturer','model','chemistry','vendor_data','eppid']):
        if not strings&(1<<i):texts[name]=None;continue
        if lengths[i]>256:raise ValueError('Invalid string length')
        if i in [3,4] and not identifiers:texts[name]='[redacted]';continue
        b=data[230+i*256:230+i*256+lengths[i]]
        texts[name]=b.hex() if i==3 else b.replace(b'\0',b'').decode('ascii',errors='replace')
    adapter={}
    adapter_sampled=struct.unpack_from('<Q',data,1512)[0]
    for i,name in enumerate(['adapter_id_raw','voltage_raw_units_unverified',
                             'current_raw_units_unverified','available_design_power_W',
                             'manufacturing_date_raw','adapter_serial','design_power_W']):
        if not adapters&(1<<i):adapter[name]=None;continue
        adapter[name]='[redacted]' if i==5 and not identifiers else ax[i]
    if adapters&(1<<6):
        adapter['ac_present_at_capture']=bool(bx[6]&1)
        adapter['power_supply_id_valid']=bool(bx[6]&2)
    return {'schema':schema,'status':STATUS[status],'sequence':sequence,
            'sample_ns':sampled,'static_sample_ns':static_sampled,'adapter_sample_ns':adapter_sampled,
            'specification_version':spec,'requests':requests,'failures':failures,
            'max_call_duration_us':max_us,'battery':numbers,'strings':texts,
            'adapter':adapter,
            'freshness':{'cycle_temperature':'sample_ns',
                         'other_battery_fields':'static_sample_ns; attachment snapshot, not continuous monitoring',
                         'adapter_fields':'adapter_sample_ns; refreshed at attachment, wake and ACPI power-source changes'},
            'note':'Firmware reports; raw vendor fields are not automatically mapped to Apple health or capacity policy. Adapter watts are ratings, not measured consumption. A historical/static rating does not prove that the same supply is still attached.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=pathlib.Path)
    p.add_argument('--include-identifiers',action='store_true')
    args=p.parse_args()
    raw=args.input.read_bytes() if args.input else subprocess.check_output(
        ['/usr/sbin/ioreg','-a','-r','-c','SMCSMBusController'],timeout=10)
    objects=plistlib.loads(raw)
    if isinstance(objects,dict):objects=[objects]
    for obj in objects:
        if 'A51mDellTelemetry' not in obj:continue
        if obj.get('A51mDellTelemetrySchema')!=2:
            raise SystemExit('Unsupported Dell telemetry schema')
        result=decode(obj['A51mDellTelemetry'],args.include_identifiers)
        result['revision']=obj.get('A51mBatteryRevision')
        print(json.dumps(result,indent=2));return
    raise SystemExit('No Dell telemetry cache: requires the candidate driver and explicit -a51mbatdell opt-in.')


if __name__=='__main__':main()
