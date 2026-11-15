#!/usr/bin/env python3
"""Read numeric _BIX/_BIF observation; no ACPI call or privileged operation."""
import argparse
import json
import pathlib
import plistlib
import struct
import subprocess

BIX = ('revision power_unit design_capacity full_charge_capacity technology '
       'design_voltage warning_capacity low_capacity cycle_count accuracy '
       'max_sampling_time min_sampling_time max_averaging_interval '
       'min_averaging_interval granularity_1 granularity_2').split()
BIF = ('power_unit design_capacity full_charge_capacity technology design_voltage '
       'warning_capacity low_capacity granularity_1 granularity_2').split()


def decode(data):
    if len(data) != 72:
        raise ValueError('Unexpected static information size')
    method, count, *values = struct.unpack('<18I', data)
    if method not in (1, 2):
        raise ValueError('Unknown ACPI source')
    names = BIX if method == 2 else BIF
    fields = dict(zip(names, values))
    cycle = fields.get('cycle_count')
    return {'method': '_BIX' if method == 2 else '_BIF',
            'package_count': count, 'raw_numeric_fields': fields,
            'cycle_count_source_available': method == 2 and cycle != 0xffffffff,
            'cycle_count_zero_requires_independent_validation': method == 2 and cycle == 0,
            'note': 'Firmware package values, not an independent hardware measurement.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=pathlib.Path)
    args = parser.parse_args()
    raw = args.input.read_bytes() if args.input else subprocess.check_output(
        ['/usr/sbin/ioreg', '-a', '-r', '-c', 'SMCSMBusController'], timeout=10)
    objects = plistlib.loads(raw)
    if isinstance(objects, dict):
        objects = [objects]
    for obj in objects:
        if 'A51mBatteryStaticInfo' in obj:
            if obj.get('A51mBatteryStaticInfoSchema') != 1:
                raise SystemExit('Unsupported static information schema')
            result = decode(obj['A51mBatteryStaticInfo'])
            result['revision'] = obj.get('A51mBatteryRevision')
            print(json.dumps(result, indent=2))
            return
    raise SystemExit('No static observation yet; requires a51m4 and observation enabled.')


if __name__ == '__main__':
    main()
