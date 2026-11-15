#!/usr/bin/env python3
"""Execute archived Dell buffer conversion AML with an owned firmware stub.

The production C000/C001/C002/C003/WMDM bodies are extracted unchanged.
No OperationRegion, SMI port or physical-memory method is included. This
authenticates the packet layout against archived ASL, not the current firmware.
"""
import hashlib
import argparse
import pathlib
import re
import shutil
import struct
import subprocess
import tempfile

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--asl',type=pathlib.Path,required=True,
                    help='Private archived DSDT containing the expected converter; never uploaded by this test')
args=parser.parse_args()
source=args.asl.read_text()
a=source.index('            Name (DSMM, Buffer (0x2C)')
b=source.index('            Name (WQMO, Buffer',a)
methods=source[a:b]
assert hashlib.sha256(methods.encode()).hexdigest()=='cdf1cf9b33e67fe6acf7bde498ab7346680179a2f8ea747aa2cf821fb8326bcb'
assert 'OperationRegion' not in methods and 'SMID' not in methods
stub=r'''
Method (C004, 3, Serialized) {
    CreateDWordField (Arg1, 0x14, RXAX)
    CreateDWordField (Arg1, 0x18, RXBX)
    CreateDWordField (Arg1, 0x1C, RXCX)
    CreateDWordField (Arg1, 0x20, RXDX)
    CreateDWordField (Arg1, 0x10, ATTR)
    If (Arg0 != 0xA3) {Return (Arg1)}
    If (RXAX == 0xFEA3) {
        If ((RXBX != 0x141) || (ATTR != Zero)) {Return (Arg1)}
        RXAX=0x44494147 RXCX=0x148 RXDX=0x44454C4C
    } ElseIf (RXAX == 0x24A3) {
        If ((RXBX != 0x600) || (ATTR != Zero)) {Return (Arg1)}
        RXAX=330 RXBX=3
    } ElseIf (RXAX == 0x21A3) {
        If ((RXBX != 0x1701) || (RXCX != 32) || (RXDX != 44) ||
            (ATTR != 0x01000000) || (Arg2 != 76)) {Return (Arg1)}
        CreateQWordField (Arg1, 44, MARK)
        If ((MARK != 0x474149444C4C4544) && (MARK != 0x45444F434C4C4544)) {Return (Arg1)}
        RXAX=21
    } ElseIf (RXAX == 0x23A3) {
        If ((RXBX != 0x2001) && (RXBX != 0x3701)) {Return (Arg1)}
        If ((RXCX != 32) && (RXCX != 256)) {Return (Arg1)}
        If ((RXDX != 44) || (ATTR != 0x01000000) || (Arg2 != (44 + RXCX))) {Return (Arg1)}
        CreateDWordField (Arg1, 44, TEXT)
        TEXT=0x54534554 RXAX=4
    }
    Return (Arg1)
}'''
cases=[]
for ax,bx,payload,expected,marker in [
        (0xfea3,0x141,4,0x44494147,False),
        (0x24a3,0x600,4,330,False),
        (0x21a3,0x1701,32,21,False),
        (0x21a3,0x1701,32,21,True),
        (0x23a3,0x2001,32,4,False),
        (0x23a3,0x3701,256,4,True)]:
    data=struct.pack('<7I',4,ax,4,bx,4,payload if payload>4 else 0,payload)
    data+=(b'\0'*4 if payload==4 else (b'DELLDIAG' if marker else b'DELLCODE')*(payload//8))
    index=len(cases);name=f'IN{index:02d}';test=f'VT{index:02d}';field=f'AX{index:02d}'
    extra=''
    if ax==0xfea3:extra=f'CreateDWordField (Local0, 28, DX{index:02d}) If (DX{index:02d} != 0x44454C4C) {{Return (Zero)}}'
    if ax==0x24a3:extra=f'CreateDWordField (Local0, 12, BX{index:02d}) If (BX{index:02d} != 3) {{Return (Zero)}}'
    if ax==0x23a3:extra=f'CreateDWordField (Local0, 28, TX{index:02d}) If (TX{index:02d} != 0x54534554) {{Return (Zero)}}'
    cases.append(f'''Name ({name}, Buffer () {{{','.join(hex(v) for v in data)}}})
        Method ({test}, 0, Serialized) {{
            Local0=WMDM (Zero, One, {name})
            CreateDWordField (Local0, 4, {field})
            If ({field} != {expected}) {{Return (Zero)}}
            {extra}
            Return (One)
        }}''')
iasl,executor=shutil.which('iasl'),shutil.which('acpiexec')
assert iasl and executor,'ACPICA tools are required; this test never accesses live ACPI'
with tempfile.TemporaryDirectory(prefix='a51m-dell-acpi-') as tmp:
    tmp=pathlib.Path(tmp);p=tmp/'fixture.dsl'
    p.write_text('DefinitionBlock ("", "SSDT", 2, "A51M", "WIRETEST", 1) {\n'+methods+stub+'\n'.join(cases)+'\n}')
    compiled=subprocess.run([iasl,'-ve',str(p)],text=True,capture_output=True)
    assert compiled.returncode==0,compiled.stdout+compiled.stderr
    # Repeat in the same interpreter to detect growing object retention.
    commands=';'.join(f'execute \\VT{i:02d}' for _ in range(12) for i in range(len(cases)))
    # WMDM is already serialized. Do not let the debug interpreter rewrite
    # archived helper flags (its auto-serialization retains debug objects).
    run=subprocess.run([executor,'-df','-ds','-b',commands,str(tmp/'fixture.aml')],text=True,capture_output=True,timeout=20)
    log=run.stdout+run.stderr
    # ACPICA 20260408's debug teardown reports four fixed cache allocations
    # for these dynamically-created names. Keep the report visible, require
    # that exact fixed count after 72 evaluations, and reject method errors.
    errors=[line for line in log.splitlines() if 'ACPI Error:' in line]
    assert not errors or (len(errors)==1 and '4 (0x4) Outstanding cache allocations' in errors[0]),log
    assert 'Aborting method' not in log and 'failed with status' not in log,log
    values=re.findall(r'\[Integer\] = ([0-9A-Fa-f]+)',log)
    assert [int(v,16) for v in values]==[1]*(12*len(cases)),log
    if errors:print('NOTE: ACPICA debug teardown retains four fixed cache objects; unchanged after 72 method evaluations, not a live-kernel memory test.')
print('PASS: 72 archived native WMDM roundtrips: signature, 330 W, cycles, both markers, 32/256-byte strings; firmware transport replaced, no hardware call')
