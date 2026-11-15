VirtualSMC
========

[![Build Status](https://github.com/acidanthera/VirtualSMC/actions/workflows/main.yml/badge.svg?branch=master)](https://github.com/acidanthera/VirtualSMC/actions) [![Scan Status](https://scan.coverity.com/projects/16571/badge.svg?flat=1)](https://scan.coverity.com/projects/16571)

Advanced Apple SMC emulator in the kernel. Requires [Lilu](https://github.com/vit9696/Lilu) for full functioning.

### A51m R2 fork: 1.3.8-a51m7

The maintained A51m changes are on
[`a51m-battery-telemetry`](https://github.com/kingo132/VirtualSMC/tree/a51m-battery-telemetry).
`master` follows upstream; this is a model-specific SMCBatteryManager extension,
not a separate version of Apple's battery driver. Upstream attribution and
licenses are retained.

The a51m7 source was built for Intel and verified loaded on an Area-51m R2 with
BIOS 1.37.0 and macOS 26.7.1 (25G241). Actual firmware reads supplied battery
cycles and temperature, native adapter rated power, and validated ratings for
two attached inputs. In the tested two-240-W configuration, the native total
was 480 W and the independent firmware reports were 240 + 240 W. Those are
observed values, never fallback constants. They describe rated supply capacity,
not wall consumption, per-port electrical limits or guaranteed sustained power.

| Boot argument | Effect | Default |
| --- | --- | --- |
| `-a51mbattime` | Return unknown for inapplicable/invalid battery time estimates; preserve valid estimates and original current/capacity | Off |
| `-a51mbatobserve` | Record bounded source/reply and numeric ACPI metadata for local diagnosis | Off |
| `-a51mbatmeta` | Omit synthetic adapter/cell measurements while retaining the virtual battery-presence topology | Off |
| `-a51mbatdell` | Read allowlisted Dell firmware metadata through its serialized LegacyDiags ACPI endpoint | Off |
| `-a51mbatadapter` | Publish validated attached rated power in the native adapter dictionary and cache validated dual-input ratings; requires `-a51mbatdell` and `-a51mbatmeta` | Off |

The native adapter bridge requires Darwin 25 and the exact tested Apple driver
image. An unrecognized image is refused; an OS update needs revalidation, not
removal of the gate. Failed, stale or inconsistent optional data is invalidated
rather than replaced by guessed watts, current, voltage or identity. Firmware
calls use the existing battery poll; no new daemon, periodic recovery service,
charge-control write or direct SMI-port writer is installed. A slow-return guard
stops later calls; it cannot interrupt firmware execution.

The firmware count/pair, native adapter dictionary and booted revision have
passed basic acceptance. Full detach/reattach, sleep/wake, long-uptime and every
consumer's UI remain separate acceptance work. iStat has one supported adapter
row; this does not add two per-input rows. The historical 31 A excursion is
unresolved. GPU stalls, Universal Control, wake brightness and shutdown waits
are not fixed by this battery revision.

Read cached adapter data without invoking firmware:

```sh
python3 Tools/dump_a51m_adapters.py
```

Diagnostic records can contain battery identity. The Dell decoder redacts it by
default; keep raw logs, private opt-in identity dumps, EFI configuration and
SMBIOS identifiers out of issues and commits. Back up the working EFI before
deployment and retain the previous battery KEXT for rollback. Do not hot-unload
the battery driver. Revision a51m2 has a known battery-presence regression with
`-a51mbatmeta` and must not be deployed.

See [implementation, tests and acceptance limits](Docs/A51mBattery.md) and the
[changelog](Changelog.md). This source publication does not change the local EFI.

English (Current)  
[简体中文](README_zh.md)  

#### Features
- Supports macOS 10.4 and newer (10.9 and newer is recommended)
- Implements MMIO protocol and interrupt-based responses for compatibility with modern OS
- Properly reports key attributes and r/w protection in the keys
- Allows tuning on per-model basis and allows to use different SMC generations
- Extensible by the plugins for sensor and key addition support
- Enables `smcdebug=XX` boot argument support on 10.9
- Replaces hardware SMC it finds (to disable SMC entirely you need to flash a dedicated firmware)

#### Boot arguments
- Add `-vsmcdbg` to enable debug printing (available in DEBUG binaries).
- Add `-vsmcoff` to switch off all the Lilu enhancements.
- Add `-vsmcbeta` to enable Lilu enhancements on unsupported OS (26 and below are enabled by default).
- Add `-vsmcrpt` to report about missing SMC keys to the system log.
- Add `-vsmccomp` to prefer existing hardware SMC implementation if found.
- Add `vsmcgen=X` to force exposing X-gen SMC device (1 and 2 are supported).
- Add `vsmchbkp=X` to set HBKP dumping mode (0 - off, 1 - normal, 2 - without encryption).
- Add `vsmcslvl=X` to set value serialisation level (0 - off, 1 - normal, 2 - with sensitive data (default)).
- Add `smcdebug=0xff` to enable AppleSMC debug information printing.
- Add `watchdog=0` to disable WatchDog timer (if you get accidental reboots).

#### Credits
- [Apple](https://www.apple.com) for macOS
- [netkas](http://netkas.org) for the original idea of creating a software SMC emulator
- [CupertinoNet](https://github.com/CupertinoNet) for reversing most of MMIO protocol and SMC headers
- [Alex Ionescu](https://github.com/ionescu007) for the initial reverse of SMC firmware
- [07151129](https://github.com/07151129) for co-devoloping VirtualSMC and invaluable help during the research
- [lvs1974](https://github.com/lvs1974) for developing laptop sensor support
- [usr-sse2](https://github.com/usr-sse2) for developing laptop sensor support
- [joedmru](https://github.com/joedmru) for developing Super I/O chips support
- [theopolis](https://github.com/theopolis) for [smc-fuzzer](https://github.com/theopolis/smc-fuzzer) tool
- [kokke](https://github.com/kokke) for [tiny-AES-c](https://github.com/kokke/tiny-AES-c)
- [vit9696](https://github.com/vit9696) for [Lilu.kext](https://github.com/vit9696/Lilu) and this software
- Additional big thanks go to all the contributors and researchers involved in Apple SMC exploration!
