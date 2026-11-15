#!/usr/bin/env python3
"""Host tests of the real policy, trace layout and extracted driver code.

Uses fake state/requests; never loads a KEXT or accesses power hardware.
"""
import importlib.util,json,os,pathlib,re,struct,subprocess,sys,tempfile

sys.dont_write_bytecode=True
SANITIZERS=os.environ.get('A51M_TEST_SANITIZERS','undefined')
if SANITIZERS not in ('undefined','address,undefined','none'):
    raise SystemExit('Unsupported A51M_TEST_SANITIZERS value')

ROOT=pathlib.Path(__file__).resolve().parents[2]
SENSORS=ROOT/'Sensors/SMCBatteryManager'


def function(text,signature):
    a=text.index(signature);b=text.index('{',a);depth=1;c=b+1
    while depth:
        depth+=(text[c]=='{')-(text[c]=='}');c+=1
    return text[a:c]


def build_run(base,name,source,*args):
    cpp=base/(name+'.cpp');exe=base/name;cpp.write_text(source)
    sanitizer_flags=[] if SANITIZERS=='none' else ['-fsanitize='+SANITIZERS]
    subprocess.run(['/usr/bin/clang++','-std=c++17','-Wall','-Wextra','-Werror',
                    '-Wno-unused-variable','-Wno-unused-but-set-variable',
                    *sanitizer_flags,'-fno-omit-frame-pointer','-O1',
                    '-I',str(ROOT),str(cpp),'-o',str(exe)],check=True)
    return subprocess.check_output([str(exe),*map(str,args)],text=True).strip()


def integration_source():
    cpp=(SENSORS/'ACPIBattery.cpp').read_text();header=(SENSORS/'ACPIBattery.hpp').read_text()
    state=(SENSORS/'BatteryManagerState.hpp').read_text()
    a=state.index('struct State {');b=state.index('\n\t};',a)+4;state=state[a:b]
    a=cpp.index('\t// Average rate calculation');b=cpp.index('\n\tacpi->release();',a);body=cpp[a:b]
    average_bound=int(re.search(r'AverageBoundPercent = (\d+)',header)[1])
    return '''
#include "Sensors/SMCBatteryManager/A51mBatteryPolicy.hpp"
#include "Sensors/SMCBatteryManager/A51mBatteryTelemetry.hpp"
#include <cassert>
#include <cstdio>
#define SYSLOG(...) ((void)0)
#define DBGLOG(...) ((void)0)
constexpr uint32_t BSSAverageRate=20,BSSTimeToEmpty=18,BSSTimeToFull=17;
constexpr uint32_t QuickPollInterval=1000,NormalPollInterval=60000,AverageBoundPercent=BOUND;
constexpr uint32_t BSTStateMask=3,BSTNotCharging=0,BSTDischarging=1,BSTCharging=2,BSTCritical=4;
struct BatteryInfo{static constexpr uint32_t ValueUnknown=0xffffffff;};
uint64_t getCurrentTimeNs(){return 1234;}
STATE
struct Result {State state;A51mBattery::Snapshot observation;};
Result evaluate(State st,bool a51mTimePolicy,bool a51mObserve){
 int id=0;bool quickPoll=false;uint32_t supplementConfig=0;
 uint64_t a51mObservationSequence=0;
 const uint32_t rawState=st.state,rawRate=st.presentRate;
 const uint32_t rawCapacity=st.remainingCapacity,rawVoltage=st.presentVoltage;
 const uint32_t previousCapacity=st.lastRemainingCapacity;
 BODY
 return {st,observation};
}
int main(){
 State s;s.remainingCapacity=s.lastRemainingCapacity=s.lastFullChargeCapacity=7077;
 s.presentVoltage=12870;
 for(int fix=0;fix<2;++fix)for(int observe=0;observe<2;++observe){
  auto r=evaluate(s,fix,observe);
  assert(r.state.runTimeToEmpty==uint32_t(fix?65535:424620));
  assert(r.state.averageTimeToEmpty==uint32_t(fix?65535:424620));
  assert(r.state.signedPresentRate==0 && r.state.signedAverageRate==0);
  assert(r.state.remainingCapacity==7077 && r.state.batteryIsFull);
  assert(r.observation.sequence==uint64_t(observe));
  if(observe){
   assert(r.observation.rawRate==0 && r.observation.rawCapacity==7077);
   assert(r.observation.upstreamRuntime==424620);
   assert(r.observation.upstreamAverageTime==424620);
   assert(r.observation.averageTime==uint32_t(fix?65535:424620));
   assert(r.observation.policyEnabled==uint64_t(fix));
  }
 }
 s.lastRemainingCapacity=7006;auto corrected=evaluate(s,true,true);
 assert(corrected.state.signedPresentRate==4260); // Do not hide the upstream current estimator.
 assert(corrected.state.runTimeToEmpty==65535);
 assert(corrected.observation.signedPresentRate==4260);
 s.state=1;s.presentRate=7300;s.averageRate=7300;
 auto discharge=evaluate(s,true,true);assert(discharge.state.runTimeToEmpty==58);
 assert(discharge.state.signedPresentRate==-7300);
 s.state=2;s.remainingCapacity=6000;s.lastRemainingCapacity=6000;s.presentRate=s.averageRate=1000;
 auto charging=evaluate(s,true,true);assert(charging.state.timeToFull==64);
 assert(charging.state.runTimeToEmpty==65535 && charging.state.signedPresentRate==1000);
 puts("Real updater: four independent flag combinations and current preservation passed");
}
'''.replace('BOUND',str(average_bound)).replace('STATE',state).replace('BODY',body)


def observer_source():
    cpp=(SENSORS/'SMCSMBusController.cpp').read_text()
    header=(SENSORS/'SMCSMBusController.hpp').read_text()
    a=header.index('\tstruct A51mPending');b=header.index('\n\tvoid observePrepared',a)
    members=header[a:b]
    functions='\n'.join(function(cpp,'void SMCSMBusController::'+x) for x in ['observePrepared','observeCompletion'])
    return '''
#include "Sensors/SMCBatteryManager/A51mBatteryTelemetry.hpp"
#include <cassert>
#include <cstdio>
#include <cstring>
uint64_t clockNs=0;uint64_t getCurrentTimeNs(){return ++clockNs;}
struct IOSMBusTransaction{uint8_t command=0;uint8_t receiveData[32]{};uint32_t receiveDataCount=2;};
struct IOSMBusRequest{IOSMBusTransaction *transaction=nullptr;};
class SMCSMBusController{public:
 MEMBERS
 void observePrepared(IOSMBusRequest*,const A51mBattery::Snapshot&);
 void observeCompletion(IOSMBusRequest*);
};
FUNCTIONS
int main(){
 SMCSMBusController c;IOSMBusTransaction t;t.command=0xb;IOSMBusRequest req;req.transaction=&t;
 A51mBattery::Snapshot source;source.sequence=17;source.rawRate=0;source.upstreamAverageTime=424620;
 c.observePrepared(&req,source);c.observeCompletion(&req);assert(clockNs==0);
 SMCSMBusController::A51mObserver observer;c.a51mObserver=&observer;
 c.observePrepared(&req,source);source.sequence=999;
 t.command=0x12;t.receiveData[0]=0xac;t.receiveData[1]=0x7a;
 c.observeCompletion(&req);
 auto &a=observer.trace.records[0];auto &b=observer.trace.records[1];
 assert(a.phase==1 && a.command==0xb && a.value==0 && a.source.sequence==17);
 assert(b.phase==2 && b.command==0x12 && b.value==31404 && b.expectedCommand==0xb && b.expectedValue==0);
 assert(a.requestSequence==b.requestSequence && b.source.sequence==17);
 // Reuse after completion must get a different request identity.
 c.observePrepared(&req,source);c.observeCompletion(&req);
 assert(observer.trace.records[2].requestSequence!=a.requestSequence);
 IOSMBusTransaction transactions[65];IOSMBusRequest requests[65];
 for(unsigned i=0;i<65;++i){requests[i].transaction=&transactions[i];c.observePrepared(&requests[i],source);}
 assert(observer.trace.dropped==1);
 auto before=transactions[64];c.observeCompletion(&requests[64]);
 assert(memcmp(&before,&transactions[64],sizeof(before))==0);
 c.observePrepared(&requests[0],source);assert(observer.trace.dropped==2);
 for(unsigned i=0;i<64;++i)c.observeCompletion(&requests[i]);
 for(auto &pending:observer.pending)assert(!pending.request);
 assert(observer.trace.used==64 && observer.trace.overwritten>0);
 puts("Real observer: disabled path, reply overwrite, identity reuse and saturation passed");
}
'''.replace('MEMBERS',members).replace('FUNCTIONS',functions)


def metadata_registration_source():
    cpp=(SENSORS/'SMCBatteryManager.cpp').read_text()
    a=cpp.index('\tconst bool omitSyntheticMetadata')
    b=cpp.index('\tconst auto batCount',a)
    registration=cpp[a:b]+function(cpp,'if (getKernelVersion() >= KernelVersion::BigSur && !omitSyntheticMetadata)')
    template=(pathlib.Path(__file__).parent/'metadata-registration.cpp').read_text()
    return template.replace('/* ACTUAL_REGISTRATION */',registration)


def main():
    spec=importlib.util.spec_from_file_location('dump',ROOT/'Tools/dump_a51m_battery.py')
    decoder=importlib.util.module_from_spec(spec);spec.loader.exec_module(decoder)
    with tempfile.TemporaryDirectory(prefix='a51m-battery-tests-') as d:
        d=pathlib.Path(d);binary=d/'trace.bin'
        outputs=[build_run(d,'policy',(pathlib.Path(__file__).parent/'policy.cpp').read_text(),binary),
                 build_run(d,'integration',integration_source()),
                 build_run(d,'observer',observer_source()),
                 build_run(d,'metadata',metadata_registration_source())]
        raw=binary.read_bytes();trace=decoder.decode(raw)
        assert trace['total']==70 and trace['overwritten']==6 and len(trace['events'])==64
        assert all(not x['reply_changed'] for x in trace['events'])
        assert any(x.get('interpreted_current_mA')==-7300 for x in trace['events'])
        assert trace['events'][0]['event_sequence']==7
        corrupt=bytearray(raw);first=80+6*280
        struct.pack_into('<Q',corrupt,first+4*8,123)
        assert decoder.decode(corrupt)['events'][0]['reply_changed']
        for bad in [raw[:-1],b'\0'*len(raw),raw[:32]+struct.pack('<Q',65)+raw[40:]]:
            try:decoder.decode(bad)
            except ValueError:pass
            else:raise AssertionError('Invalid trace accepted')
        outputs.append('Python decoder: signed values, wrap order, mutation and malformed input passed')
    print(json.dumps({'passed':outputs,'kernel_or_hardware_calls':False,'sanitizers':SANITIZERS},indent=2))


if __name__=='__main__':main()
