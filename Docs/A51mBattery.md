# A51mR2电池时间修复与只读观察

## Published source: a51m7 — attached total and independent input ratings

The previous a51m6 bridge booted and reached iStat, but its selector-6 static
330 W value did not represent the owner's attached two 240 W supplies. The
correction uses selector 3, matching Windows IAdaptor::GetDesignPower, while
retaining selector-6 AC-present/PSID flags, image/version gating, native-data
precedence, freshness/invalidity removal and the existing publication boundary.
No fixed 480 W value is introduced. This is rated available supply power, not
measured wall consumption or a guarantee of CPU/GPU sustained limits.

The same opt-in also queries the current A51m R2 BIOS 1.37.0 AMW1 WMAX method
0x1c (PowerInformation): operation 1 reads the connected count, operation 2
reads EC A1WH:A1WL / A2WH:A2WL for firmware ports 0/1, and operation 4 reads
firmware status. Exact AWCC GUID/AX descriptor, endpoint and integer-return
checks precede the bounded five-query sequence. No control operation or EC/
SMI write is issued. A returned call exceeding 20 ms stops further AWCC reads
without disabling the independent working battery/cycle reader. This is a
post-return guard, not a preemptive firmware timeout.

A pair is valid only with two attached inputs both before and after the read,
bounded nonzero ratings, accepted firmware status and a sum equal to the exact
fresh LegacyDiags total snapshot used for the read. A single connected input
does not identify which rating register is current; no per-port value is
presented in that ambiguous case. AC change/wake invalidation and the existing
minute poll handle refresh without a new timer, daemon or app. Same-count
physical swaps without firmware notifications remain bounded snapshot data,
not continuous measurements. Firmware port order is not identified left/right.

`A51mDualAdapterTelemetry` is a separate 72-byte schema-1 cache; the existing
1520-byte Dell telemetry ABI is unchanged. Read the validated total and pair
without triggering firmware calls:

```
python3 Tools/dump_a51m_adapters.py
```

iStat's existing single Power Adapter row receives the corrected total. This
change does not add two iStat UI rows: no supported per-input iStat display
interface has been established. The independent cache and reader support
honest per-input inspection without pretending two new rows exist.

Production policy/publication/ACPI reader fixtures, invalidation/freshness/
count-race/malformed-data cases, battery regression/startup cases and Intel
Release build passed. a51m7 UUID `742CD514-F5D5-3307-BA43-625F9F968DEE` is
now verified loaded after the user restart. Native AdapterDetails reports 480 W;
fresh validated WMAX input ratings are 240 + 240 W, with stable before/after
count 2 and no failures across repeated minute polls. Firmware status 2 remains
visible and is not rewritten to normal. Two full EFI backups were
verified; only the battery executable changed within OC. The existing Shell
restore entry returns this executable to the previous booted a51m6, with its
previous broader recovery script preserved. Actual iStat menu display,
detach/reattach, sleep/wake and extended-uptime acceptance remain open.
Live per-port success is based on the loaded driver and real firmware returns,
not the host fixtures. The user authorized publishing the verified a51m7
battery source; unrelated SMCDellSensors work remains outside this update.

### Reproducible verification and privacy

Run these host-side fixtures from the repository root. They compile or decode
owned data and do not load a KEXT or call live firmware:

```sh
python3 Tests/A51mBattery/run.py
python3 Tests/A51mBattery/static-info.py
python3 Tests/A51mBattery/dell.py
python3 Tests/A51mBattery/dell-decoder.py
python3 Tests/A51mBattery/dual-decoder.py
python3 Tests/A51mBattery/watch-decoder.py
python3 Tests/A51mBattery/adapter-publication.py
```

`adapter-policy.py PATH`, `native-startup.py PATH` and `native-adapter.py PATH`
additionally require a local copy of the exact tested Intel AppleSmartBatteryManager
image (installed or from the matching KDK) and refuse an unknown image. No image
is downloaded or distributed by the tests. The optional `dell-acpi-roundtrip.py --asl PATH`
requires ACPICA tools and a private archived DSDT with the expected converter
hash; the test replaces firmware access with a stub. Neither Apple binaries,
private DSDT/logs nor local build products belong in this source publication.
Build SMCBatteryManager using the upstream Lilu/MacKernelSDK dependencies and
the Intel Release target. Offline fixtures and a successful build do not
replace real detach/reattach, wake or consumer-UI acceptance.

## Historical post-boot acceptance: a51m5, 2026-11-15

The new boot actually loaded SMCBatteryManager UUID
`37715531-726D-39EB-8568-89ABD92C6F51`, revision `1.3.8-a51m5`.
The four existing opt-ins remain enabled. Live Dell firmware requests succeeded
and returned cycle count 21, changing temperature, manufacture date, and static
design power 330 W / dynamic design power 480 W. These are current firmware
returns, not constants substituted from the earlier Windows captures.
AppleSmartBattery and the user's iStat panel both now report **21 cycles**.
AppleSmartBattery also receives the actual temperature. String fields remain
invalid; successful transport does not imply every returned field is usable.

The native adapter dictionary is still `{FamilyCode: 0}` without `Watts`.
That explains the missing adapter section: the read transport was implemented,
but its results were not connected to the native adapter publication path.
The prior staged candidate was not a completed iStat adapter-display fix.
Adapter selector 1 returned 11400 and selector 2 returned 0, with units/meaning
unverified; do not invent a 19.5 V/current pair to make the native V*I path
produce a desired wattage. Selector 6's static rating and selector 3's dynamic
design power are different reports, not independently identified bricks or
real-time wall consumption. No unsupported identity/voltage/current field is
added to the native adapter dictionary.

Historical a51m6 implementation (subsequently booted; its static-watt
interpretation was rejected and is superseded by a51m7 above):
`-a51mbatadapter` additionally requires the Dell-read and synthetic-metadata
opt-ins, Darwin 25 and the exact tested AppleSmartBatteryManager image UUID.
Its candidate hook runs the native gated SMC completion first; after adapter
or battery-data updates it enriches only this plugin's native power-source
dictionary with the valid current static design rating (330 W in this boot).
It preserves an original native `Watts` value, uses a separate ownership marker,
and removes its own rating on invalid/disconnected/expired data. The native
poll's existing `updateStatus` boundary is preserved; no partial-poll flush,
new service, direct I/O, fake rated voltage/current or iStat patch is added.

When explicitly enabled, existing minute polling refreshes all seven adapter
fields (ten allowlisted calls including signature/cycle/temperature per minute,
not the 29-call attachment burst). AC adapter notifications also invalidate
same-presence changes; a one-second request floor coalesces storms. The reader
regressions, rating/image-gate host tests, original battery regression suite and
Intel Release build have passed. The production publication function now also passes owned lifecycle tests:
330/370 W replacement, preservation of existing Apple Watts/other fields,
unplug/expiry/invalid removal, wrong provider isolation and allocation-failure
ownership. They verify that no extra updateStatus call is introduced. These
fixtures do not execute Apple's full driver or prove powerd/iStat acceptance;
that remains a next-boot requirement.

The independently staged SMCDellSensors activity-counter fix is now loaded
with UUID `59405B15-1B92-3A85-A63E-A7C9A4DC4C49`, with its live fix/revision
properties set. That does not prove all historical desktop stutter is cured.

## a51m4已通过启动核对：静态来源观察

用户重启后，控制器和插件均报告`1.3.8-a51m4`，三个开关有效、电池存在。
新观察实际捕获当前`_BIX`20项包：单位mAh、设计7895、满充7077、循环0。
因此循环0已经存在于固件方法输出，不能归咎于SMBus导出丢掉非零计数。
真实睡眠/唤醒和长期稳定性仍需验收。

只读检查Windows盘的Dell组件后，已找到A3CallerBattery的独立软件SMI路径：
AX=0x21A3、BH=0x17、BL为电池位置，成功时AX为循环值，0xFFFF/0xFFFE为错误。
38组历史日志配对返回21，最新记录在2026年10月。尚未在当前macOS上执行此请求，
不能把历史21写死或宣称当前物理电池就是21次；必须先核实当前固件传输、并发、
位置匹配及失败语义。此轮没有发起SMI/MMIO/EC请求。

本地修订版`1.3.8-a51m4`保留a51m3的电池结构识别和假测量项省略策略。
只在已有`-a51mbatobserve`开启时，复制驱动本来已读取的`_BIX`前16个数值
或`_BIF`前9个数值，记录方法类型与包长度；不新增ACPI/EC/SMBus事务，
不记录型号、序列号或OEM字符串，不修改电流、容量、单位或循环次数。
控制器在现有发布路径复制状态后解锁，再发布固定72字节
`A51mBatteryStaticInfo`和schema=1；不是额外常驻服务。

重启后用`python3 Tools/dump_a51m_battery_static.py`读取。零次计数仍需独立
来源验证，不能把观察属性当成真实计数修复。旧DSDT的固定0和倍率问题尚未
确认适用于当前BIOS，不在本次变更中猜测性修改。

`python3 Tests/A51mBattery/static-info.py`执行实际捕获代码的16组夹具，覆盖
观察关闭/开启、BIF/BIX和截断包；另验解码器的零/非零/未知值及畸形输入。
原有时间/电流/SMC注册及原生启动分支回归仍须通过。真实启动验收另行记录。

基线：官方VirtualSMC 1.3.8，提交`b15991dd87e36a102bf159ea56490e3126245590`。
范围：本节只修改SMCBatteryManager电池插件，各功能默认关闭。另一个已验证的SMCDellSensors计数竞态及其独立部署见[SMCDellActivity.md](SMCDellActivity.md)；两项不混作同一根因。

## 已定位与未定位

官方ACPIBattery.cpp在速率为零时，用`60 * remainingCapacity`作为放电时间兜底。
SMCSMBusController::setReceiveData随后将32位结果缩为16位。容量7077mAh时：

```
60 * 7077 = 424620
uint16_t(424620) = 31404
```

满电仍报告30mA时，原代码也会生成14154分钟的放电时间。两项结果均与现场读数吻合。
Smart Battery规范1.1第5.1.18、5.1.19、5.1.20节规定：未处于相应放电/充电状态，
相关时间返回65535表示未知/不适用；有效分钟数范围0..65534。

现场另有一个更新周期出现平均电流31404mA，随后归零。当前证据不足以认定它与时间字段
属于同一根因。本机苹果驱动的实际命令分支将0x0b（平均电流）与0x12（平均时间）分别处理，
没有发现直接的字段混写；本分支不钳制、不重置电流，也不宣称修复了该异常。

Windows安装记录将本机ACPI\PNP0C0A\0绑定到微软CmBatt_Inst（10.0.26100.9549）；
这是标准Control Method Battery路径，按固件_BST读取电池。Windows官方接口在不能估算时
返回BATTERY_UNKNOWN_TIME。Linux的ACPI电池实现同样区分未知值；它没有复用这里的SMBus模拟时间兜底。
这些证据支持修改KEXT的换算/导出逻辑；目前没有理由为这项时间问题修改SSDT。
循环次数和温度若要补齐，仍需当前固件方法和真实数据来源，不能移植旧SSDT或伪造值。

## 独立开关

| 启动参数 | 行为 |
| --- | --- |
| 无参数 | 原上游时间、电流、供电控制行为；仅增加分支版本/开关元数据 |
| `-a51mbattime` | 开启A51m时间策略，不更改电流、容量、百分比或充放电标志 |
| `-a51mbatobserve` | 只读观察原本已发生的读取和导出，不开启时间修复 |
| `-a51mbatmeta` | a51m3保留独立的虚拟电池结构描述，不注册无真实数据来源的ACID与BC1V测量项；a51m2此选项有启动回归，禁止使用 |
| `-a51mbatdell` | a51m5只读Dell元数据扩展；默认关闭，须核对接口签名与有效字段，真实数据验收尚待下一次启动 |
| 前两者同时 | 时间修复和观察同时开启，记录修复前后的时间 |
| 三者同时 | 在时间修复与观察之外，省略两项无真实来源的SMC元数据 |

使用显式开关是因为黑苹果SMBIOS会伪装成苹果机型，不根据伪装的型号自动启用。
时间策略实现于A51mBatteryPolicy.hpp，在上游状态/临界电量判断之后应用：

- 非放电状态：RunTimeToEmpty、AverageTimeToEmpty为0xffff。
- 非充电状态：AverageTimeToFull为0xffff。
- 零/未知速率、无效容量、无法表示的估算为0xffff。
- 容量乘60使用64位中间值；有效估算和有效的补充硬件时间仍保留。
- 保留上游1.3.8的持续轮询和供电通知修复。

即使上游通过容量校正推算出非零电流，本策略也不改动它。该路径只有时间估算会基于原始
速率有效性处理，不把估计的电流当作原始硬件电流来证明时间有效。
SMBus和原有SMC充电时间键使用同一份最终时间状态。

## 只读观察的数据意义

原始_BST在这里指**固件方法返回的四个数值**，不等同于物理电池寄存器或独立电流表测量。
SMCBatteryManager是虚拟SMBus供应者，记录的回复也不是物理总线抓包。

ACPIBattery读取现有_BST后，在转换前保存四个数；同一锁内发布规范化状态和观察序号。
每个受观察的SMBus请求在读取字段时，复制相同序号的源快照：

1. `prepared`：已有回复准备完成、请求成功入队。
2. `before_native_completion`：调用上游completeRequest之前，重新记录该请求实际缓冲区。

第二阶段保留第一阶段的预期命令/值和request_sequence，便于识别队列期间的改变。
完成回调后不访问可能已释放的请求。请求指针只用于内部配对，**不导出内核地址**。
这定位的是控制器交接之前的状态；若交接前正确而AppleSmartBattery字段异常，仍需继续查
原生完成/发布路径，不能仅凭此断言苹果驱动有错。

观察0x0a、0x0b、0x11、0x12、0x13。只记录现有数据，不新增EC/SMBus请求、内核钩子、
充电控制、常驻App或launchd服务。关闭观察时不分配观察缓冲区。
观察开启时，控制器预分配64个事件槽和64个待完成配对槽；总存储固定。
事件覆盖数与因配对槽饱和/重复请求指针而丢弃的次数分别计数。
IORegistry发布复用原有100ms定时器，在批量请求完成后进行；不在stateLock自旋锁内分配对象。

### IORegistry属性和解码

控制器SMCSMBusController提供：

- `A51mBatteryRevision`：`1.3.8-a51m3`；此前正常版为`1.3.8-a51m1`，a51m2未通过启动验收。
- `A51mBatteryTimePolicyEnabled`：时间开关。
- `A51mBatteryObserveActive`：观察存储是否成功启用。
- `A51mBatteryTrace`：可选、固定大小OSData。

电池插件SMCBatteryManager还提供相同的`A51mBatteryRevision`，以及
`A51mBatterySyntheticSMCMetadataOmitted`布尔值，用于确认第三个开关。
该开关开启时，a51m3还提供`A51mBatteryLogicalSlotCount`，表示兼容层的虚拟电池结构数量，
不代表实测物理电芯数量，也不用于推算单节电压。

```
python3 Tools/dump_a51m_battery.py
python3 Tools/dump_a51m_battery.py --input saved-ioreg.plist
```

工具只读取IORegistry或本地文件，不打开电池控制用户客户端，不发起SMBus事务。
每次调用输出一次快照，带本机采集的wall/monotonic时间。它不安装后台任务。

格式为小端64位字，共18000字节（本分支只验证x86_64）：

- 10字头：magic `A51MBAT1`、schema=1、recordWords=35、capacity=64、used、nextIndex、total、overwritten、dropped、reserved=0。
- 64条35字记录：9字事件头加26字源快照。布局定义见A51mBatteryTelemetry.hpp，解码字段见dump_a51m_battery.py。
- 环形记录按event_sequence排序；request_sequence关联同一请求的准备/交接事件。
- 源sequence=0表示尚无同一状态的_BST观察，不应据此归因。
- 非零overwritten/dropped或缺少配对时，应报告证据缺口，不把缺项认定为丢失驱动通知。

源快照还包含实际采用的补充方法配置、CBSS平均速率、上次容量和本次quickPoll标志，
用来区分硬件补充速率与容量差兜底。单位标志和设计电压是驱动实际采用的转换上下文，
不是完整的原始_BIX包。

## 测试与编译

```
python3 Tests/A51mBattery/run.py
xcodebuild -project VirtualSMC.xcodeproj -target SMCBatteryManager \
  -configuration Release ARCHS=x86_64 ONLY_ACTIVE_ARCH=YES \
  CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO build
```

按上游构建要求提供Lilu开发头文件/库及MacKernelSDK；这些依赖和build目录不提交。
无需修改Xcode工程来绕过本机构建环境。

测试覆盖正常充放电、满电、零/未知速率、无效容量、16/32位边界、硬件时间、状态不一致，
以及从真实更新代码提取的四种开关组合和电流保持行为。观察测试直接执行本分支的实际方法，
注入排队后的命令/值改变，检查请求复用、饱和与无硬件修改。解码测试覆盖符号数、环形顺序、
缓冲区改变与畸形输入。这些测试使用假状态/假请求，没有执行内核代码。
另有54组测试直接提取实际SMC键注册代码，覆盖第三个开关、系统代际、适配器与电池数量，
核对ACEN/ACFP/ACIN接电检测保留、ACID和BC1V只在显式开关开启时省略。
测试同时核对a51m3独立BNCB描述的有无与数值。可另行运行精确版本原生启动分支测试：

```
python3 Tests/A51mBattery/native-startup.py /System/Library/Extensions/AppleSmartBatteryManager.kext/Contents/MacOS/AppleSmartBatteryManager
```

该测试校验原生镜像UUID及两个代码片段哈希，在自有对象与回调替身上执行启动识别与可选键判断。
它复现a51m2的“无电池”，并验证独立结构描述允许电池存在而没有电压测量键；不是现场内核启动验收。

默认使用UndefinedBehaviorSanitizer。可在支持的环境设置
`A51M_TEST_SANITIZERS=address,undefined`运行ASan；本机Xcode所带ASan运行时在main之前因
libpthread初始化失败，不能宣称该模式已通过。本机UBSan测试和Release编译通过。
这不代替真实加载、充放电或长时间稳定性验收。

## 部署状态

此前a51m1已获授权部署并重启：时间修复和观察开关生效，满电无效时间已返回未知，
放电源数据、虚拟SMBus回复和系统读数在采样中吻合，31A异常未复现。
a51m2启动验收失败：系统记录`BatteryInstalled=0 cells:0`，电池容量/电压未建立，
pmset和监控界面失去内置电池。已保留失败证据并准备正常版回退；不是iStat设置问题。
a51m3修订基于下文已复现的启动依赖，**启动后的字段省略与界面验收仍待完成**。
不热卸载电池驱动、不自动重启。下一次获准启动后核对加载UUID、a51m3版本标记、
三个独立开关以及接电检测、电流、电压、容量和时间行为。
用户确认此前关机是手动操作，不列为电池故障。本修复不承诺容量校准、真实循环次数、
温度、31A异常或桌面卡顿已解决。

## a51m3: separate topology from unavailable measurements

The independent `-a51mbatmeta` opt-in stops registering two kinds of synthetic
metadata that have no measurement source in this implementation:

- `ACID`: the fixed adapter descriptor that presents 60 W as adapter power.
- `BC1V`-family cell keys: fixed 16000 mV values, not measured cell voltages.

The real AC-presence keys `ACEN`, `ACFP` and `ACIN` stay registered. Real current,
pack voltage, capacity, battery status, the time policy and observer are not
changed. Do not substitute zero or 65535 and call that a sensor reading.

**a51m2 failed live boot acceptance and must not be used with this option.**
The Apple startup notifier first reads `BNCB`. If it is absent, it probes BC4V
through BC1V definitions and uses the highest present slot as the installed
battery topology. Removing all cell keys while BNCB is absent sets the count
to zero and calls `setBatteryInstalled(false)`. This is the exact dependency
missed by the earlier optional-dictionary test, and matches the boot log.

a51m3 publishes an independent BNCB descriptor from the existing ACPI-backed
emulated battery-slot count, preserving the previous one-slot topology on the
reference machine without pretending a physical cell voltage exists. This
compatibility count is not a newly measured physical cell count. The optional
cell-measurement keys remain absent. A key definition with a failed read is
not sufficient: the current dictionary reader can still decode a zeroed
buffer into a misleading 0 V reading, so that alternative is not used.

The installed Apple consumer has an explicit missing-key decision path. Its
SMC dictionary builder marks an unavailable key as NOOP and skips it. Owned
instruction tests exercised that decision for all 256 byte status inputs;
this verifies the decision branch, not a full live SMC/UI lifecycle.

Scope is deliberately limited to this SMC export path. The legacy raw SMBus
cell-command fallback is unchanged. Cycle count, temperature, requested charge
voltage, design cycle limits and manufacturer failure status are not made
trustworthy by this option. Whether iStat omits the unavailable fields, rather
than inventing a fallback, requires post-boot acceptance. If it does not, the
change must not be reported as a completed display fix.

Rollback: restore the previous KEXT and matching private config together, or
remove only `-a51mbatmeta` before the next authorized boot to retain the old
compatibility metadata. Keep all personal identity and backup files private.

## a51m5 candidate: staged for the next authorized boot, not live-accepted

The opt-in `-a51mbatdell` adds a read-only LegacyDiags client to the existing
battery polling path. No new process, service, charge controller or SMI-port
writer is installed. It requires the native `DIAG` device to advertise the
F1DDEE52-063C-4784-A11E-8A06684B9B01 WMI method GUID and `DM` method identifier,
then validates the Dell diagnostic signature before an allowlisted query.
`WMDM` owns its firmware buffers and method serialization. This does not assert
serialization against other drivers that make independent SMM calls.

The Windows implementation and historical local captures establish this wire
protocol; they are not evidence that a new macOS call has already succeeded.
The previous 21-cycle and 330 W samples are historical, never constants or
substitutes for a failed current read. Thirty older Windows DDV snapshots also
contain adapter fields of330 W and480 W at different times. They do not
establish current attachment or how the dual-input platform aggregates power;
never hardcode330 or sum two bricks without current evidence. Current `_BIX` returns zero cycles.

Valid cycle count, temperature, manufacture date and battery identity can
replace the incomplete ACPI metadata. Pack current, pack voltage, capacity
units and charge thresholds remain on the existing `_BST`/`_BIX` path. Raw
manufacturer/status words are retained with provenance, not translated into
an invented Apple health diagnosis. Per-cell voltage is still unavailable.

The first batch performs 29 allowlisted reads. Normal minute updates perform
only signature/cycle/temperature reads. Wake or an actual ACPI AC-presence
transition also refreshes seven adapter fields, without repeating all battery
identity queries. A returned call taking more than 20 ms stops further calls
until reboot; this cannot interrupt firmware or guarantee a 20 ms worst case.
Failed fields are invalid, not zero measurements. Endpoint/signature failures
leave the original battery driver in place. This fail-closed behavior has only
been verified with owned endpoint fixtures so far.

`A51mDellTelemetry` schema 2 is a fixed 1520-byte cached record. The private
`Tools/dump_a51m_dell.py` decoder never initiates hardware access; it redacts
serial numbers, vendor data and ePPID unless explicitly requested locally.
It labels separate battery/static/adapter timestamps and does not interpret
unknown V/I scaling as engineering units.

Adapter `AX=0x24A3`, `BH=6` returns the static design rating in watts; `BH=3`
returns the available design rating, not instantaneous wall consumption.
`BH=6` result BX bit 0 is AC present and bit 1 is valid supply identification.
Voltage/current/ID/date/serial are separately cached. Their raw voltage/current
units still need current-machine validation. Do not synthesize 19.5 V or a
current from 330 W, truncate watts into the legacy 8-bit `ACID` field, or sum
two supplies without per-supply evidence.

The installed Apple driver has a modern `AC-N` / `D0VR` / `D0IR` path that
calculates a 32-bit wattage from rated mV and mA. Its exact arithmetic passed
owned 330 W and 370 W instruction tests. Modern SMC adapter-key publication
is deliberately not enabled until the Dell field units and connection
lifecycle are verified. Therefore iStat adapter-watt visibility is not yet an
accepted result. Existing fake 60 W and fake 16 V keys remain suppressed.

Validation includes actual reader/mapping/decoder code, missing and malformed
responses, error/echo rejection, ownership, slow-call cutoff, notification
invalidation, and 72 archived native AML buffer-conversion roundtrips with
firmware replaced by an owned stub. ACPICA 20260408 reports four fixed debug
teardown cache objects after these repeated evaluations; the test does not
hide that diagnostic or treat it as a live-kernel leak measurement. The old
DSDT's converter is a protocol reference, not proof of current firmware.

Build success and offline tests do not establish live firmware, UI, wake or
battery-hotplug acceptance. Before deployment, preserve a51m4 plus its private
config and recovery path. No live a51m5 transport has run as of this note.

Staged receipt: `battery-dell-deploy-20261115T084125Z` in the private evidence
directory. Only the battery executable and the appended `-a51mbatdell` option
changed. Current running revision remains a51m4; the staged executable UUID is
37715531-726D-39EB-8568-89ABD92C6F51. Full EFI copies on the system volume and
NV2T plus on-EFI copies of the prior config and a51m4 executable were hashed.
The existing UEFI Shell recovery script restores those two files and preserves
the accepted ACPI wake-table repair. File copies were rehearsed privately;
the firmware script was not run on the live machine. No reboot or hot load
was performed. The historical 330 W observation is still not a current Mac
measurement; iStat watt display and all new fields await actual boot readings.

## 参考

- [Smart Battery Data Specification 1.1，§5.1.18–20](https://sbs-forum.org/specs/sbdat110.pdf)
- [Windows BatteryEstimatedTime约定](https://learn.microsoft.com/en-us/windows/win32/api/batclass/nc-batclass-bclass_query_information_callback)
- [Windows标准电池/ACPI读取路径](https://learn.microsoft.com/en-us/windows-hardware/design/component-guidelines/battery-and-charging)
- [Linux ACPI电池实现](https://github.com/torvalds/linux/blob/master/drivers/acpi/battery.c)
- [上游1.3.8基线](https://github.com/acidanthera/VirtualSMC/tree/1.3.8)

公开仓库仅保存实现、可复现实验和结论；原始机器日志、序列号、Windows系统文件与本地证据包不提交。


## Combined sensor preflight, 2026-11-15

The adapter bridge is isolated in A51mAdapterPublication.hpp for tests of the
actual production code, rather than a parallel policy model. It writes a
32-bit AdapterDetails.Watts only for a current, PSID-valid static design rating
on this plugin's AppleSmartBattery provider chain. The existing native gated
completion runs first, and the existing poll publishes state at its original
boundary. The original native Watts always wins. No charger voltage/current
or instantaneous AC input power is inferred. This boot currently returns
static 330 W and dynamic available-design 480 W; neither is a wall wattmeter
nor proof of separately identified adapters. The local native bridge cannot be
called accepted before a real boot, unplug/replug and application check.

The read/export/time policy, Dell ACPI reader and native adapter arithmetic
regressions passed again alongside the new publication tests. Only the battery
plugin will be replaced; the independently accepted Dell activity fix remains
unchanged. All changes are local and uncommitted for review.


## Post-boot correction: dual-adapter interpretation is still open

The a51m6 executable UUID is now verified loaded. Its native bridge reaches
iStat, but publishing 330 W is NOT an accepted report of the owner's attached
2 x 240 W adapters. The current static selector 6 returns 330 W, while dynamic
selector 3 returns 480 W; both BX flags are 3. The owner reports the original
combination as 330+180 W. Do not equate the static field with a physically
identified attached brick or the total. Dynamic 480 W matches the stated
nameplate sum, but individual-port behavior/firmware thresholds still require
verification before switching the export. This turn changed no EFI or limits.
