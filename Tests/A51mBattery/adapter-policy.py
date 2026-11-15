#!/usr/bin/env python3
"""Exercise candidate policy and native image gate without loading or executing kernel code."""
import argparse,pathlib,subprocess,tempfile
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('driver',type=pathlib.Path,
                    help='Local AppleSmartBatteryManager Mach-O; exact image UUID is required')
args=parser.parse_args()
root=pathlib.Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory(prefix='a51m-adapter-policy-') as tmp:
    p=pathlib.Path(tmp);image=p/'apple-intel';exe=p/'test'
    subprocess.run(['/usr/bin/lipo',str(args.driver),
                    '-thin','x86_64','-output',str(image)],check=True)
    subprocess.run(['/usr/bin/clang++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=undefined',
                    '-I',str(root),str(root/'Tests/A51mBattery/adapter-policy.cpp'),'-o',str(exe)],check=True)
    subprocess.run([str(exe),str(image)],check=True)
