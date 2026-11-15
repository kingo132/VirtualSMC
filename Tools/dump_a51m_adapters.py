#!/usr/bin/env python3
"""Read cached A51m adapter ratings. No firmware calls or configuration writes."""
import argparse
import json
import pathlib
import plistlib
import struct
import subprocess
import time

MAX_AGE_NS = 120_000_000_000
STATUS = ['disabled', 'no_endpoint', 'invalid_descriptor', 'transport_error',
          'slow_transport_disabled', 'inconsistent_or_ambiguous', 'active']


def decode(obj, now):
    total = None
    source_ns = 0
    legacy = obj.get('A51mDellTelemetry', b'')
    if len(legacy) == 1520:
        schema, status = struct.unpack_from('<II', legacy)
        mask = struct.unpack_from('<I', legacy, 56)[0]
        watts = struct.unpack_from('<H', legacy, 198)[0]  # AX selector 3
        flags = struct.unpack_from('<H', legacy, 218)[0]  # BX selector 6
        sampled = struct.unpack_from('<Q', legacy, 1512)[0]
        if (schema == 2 and status == 7 and mask & 72 == 72 and flags & 3 == 3
                and 0 < watts <= 3000 and sampled and 0 <= now - sampled <= MAX_AGE_NS):
            total = watts
            source_ns = sampled
    result = {'revision': obj.get('A51mBatteryRevision'), 'total_rated_W': total,
              'port_1_rated_W': None, 'port_2_rated_W': None,
              'dual_status': 'not_available',
              'note': 'Rated supply capacity, not measured wall power or a guaranteed sustained system power limit. Port numbers follow firmware order; physical left/right is not identified.'}
    data = obj.get('A51mDualAdapterTelemetry')
    if data is None:
        return result
    if len(data) != 72:
        raise ValueError('Unexpected dual adapter telemetry size')
    schema, status, seq, sampled, before, after, p1, p2, fwstatus, mask, requests, failures, max_us, reserved, source = struct.unpack('<IIQQ10IQ', data)
    if schema != 1 or status >= len(STATUS) or mask & ~3 or reserved:
        raise ValueError('Unsupported dual adapter telemetry layout')
    result.update(dual_status=STATUS[status], sequence=seq,
                  attached_count_before=before, attached_count_after=after,
                  firmware_status=fwstatus, requests=requests, failures=failures,
                  max_call_duration_us=max_us,
                  sample_age_seconds=(now - sampled) / 1e9 if sampled else None)
    valid = (status == 6 and mask == 3 and sampled and 0 <= now - sampled <= MAX_AGE_NS
             and source == source_ns and 0 < source <= sampled
             and before == after == 2 and fwstatus in (1, 2)
             and 0 < p1 <= 3000 and 0 < p2 <= 3000 and total is not None and p1 + p2 == total)
    if valid:
        result.update(port_1_rated_W=p1, port_2_rated_W=p2)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=pathlib.Path, help='Read an existing private ioreg plist')
    args = parser.parse_args()
    raw = args.input.read_bytes() if args.input else subprocess.check_output(
        ['/usr/sbin/ioreg', '-a', '-r', '-c', 'SMCSMBusController'], timeout=10)
    objects = plistlib.loads(raw)
    if isinstance(objects, dict):
        objects = [objects]
    for obj in objects:
        if 'A51mDellTelemetry' in obj:
            print(json.dumps(decode(obj, time.monotonic_ns()), indent=2))
            return
    raise SystemExit('No A51m adapter cache found; requires the driver and existing -a51mbatadapter opt-in.')


if __name__ == '__main__':
    main()
