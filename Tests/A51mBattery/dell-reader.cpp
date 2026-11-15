#include "Sensors/SMCBatteryManager/A51mDellAcpi.hpp"
#include <cstdio>
using namespace A51mDell;
void reset() {
    Host::clock=1;Host::duration=1000000;Host::calls=Host::wdgCalls=0;
    Host::missing=Host::badDescriptor=Host::badSignature=Host::shortReply=false;
    Host::cycleError=Host::echoStrings=false;
    assert(Host::alive==1 && hostDevice.refs==1);
}
int main() {
    reset();{AcpiReader r;assert(!r.refresh(false)&&Host::calls==0&&Host::wdgCalls==0);}
    reset();{
        AcpiReader r;assert(r.refresh(true));
        assert(r.data.status==Status::Active && r.data.requests==29 && Host::calls==29);
        assert(r.data.has(Field::Cycles)&&r.data.numeric[0x17]==21);
        assert(r.data.has(Field::Temperature)&&r.data.numeric[8]==2930);
        assert(r.data.numeric[0x18]==9000 && r.data.numeric[3]==2);
        assert(r.data.adapterAx[6]==330 && r.data.adapterValid==127);
        assert(r.data.stringValid==31 && r.data.stringLength[0]==5);
        assert(!r.refresh(true)&&Host::calls==29);
        Host::clock+=61000000000ULL;assert(r.refresh(true));assert(Host::calls==32);
        r.resume();assert(!r.data.has(Field::Cycles) && !r.data.adapterValid);
        assert(r.refresh(true));assert(Host::calls==42);
        r.adapterChanged();assert(!r.data.adapterValid && !r.data.adapterSampledNs);
        assert(r.refresh(true));assert(Host::calls==52 && r.data.adapterAx[6]==330);
        r.invalidate();assert(!r.data.valid);assert(r.refresh(true));assert(Host::calls==81);
    }
    reset();{AcpiReader r;Host::missing=true;assert(!r.refresh(true));assert(Host::calls==0&&r.data.status==Status::NoEndpoint);}
    reset();{AcpiReader r;Host::badDescriptor=true;assert(!r.refresh(true));assert(Host::calls==0&&r.data.status==Status::InvalidDescriptor);}
    reset();{AcpiReader r;Host::badSignature=true;assert(!r.refresh(true));assert(Host::calls==1&&r.data.status==Status::BadSignature);
        Host::clock+=61000000000ULL;assert(!r.refresh(true)&&Host::calls==1);}
    reset();{AcpiReader r;Host::shortReply=true;assert(!r.refresh(true));assert(Host::calls==1&&r.data.failures==1);}
    reset();{AcpiReader r;Host::duration=21000000;assert(!r.refresh(true));assert(r.data.status==Status::SlowTransport&&Host::calls==1);
        r.invalidate();Host::clock+=61000000000ULL;assert(!r.refresh(true)&&Host::calls==1);}
    reset();{AcpiReader r;Host::cycleError=true;assert(r.refresh(true));assert(!r.data.has(Field::Cycles)&&r.data.has(Field::Temperature));}
    reset();{AcpiReader r;Host::echoStrings=true;assert(r.refresh(true));assert(r.data.stringValid==0);}
    reset();{
        AcpiReader r;assert(r.refresh(true,true));assert(Host::calls==29);
        auto before=r.data.adapterSampledNs;
        Host::clock+=61000000000ULL;assert(r.refresh(true,true));
        assert(Host::calls==39 && r.data.adapterSampledNs>before);
        // Same-presence AC notifications invalidate the old rating immediately,
        // but do not generate repeated calls inside the one-second floor.
        for(int i=0;i<20;++i) {
            r.adapterChanged();assert(!r.data.adapterValid);
            assert(!r.refresh(true,true));
        }
        assert(Host::calls==39);
        Host::clock+=1000000000ULL;assert(r.refresh(true,true));
        assert(Host::calls==49 && r.data.adapterValid==127);
    }
    reset();
    puts("PASS: actual ACPI reader endpoint/GUID gates, signatures, 29 allowlisted reads, cache, invalidation, missing fields, slow transport and ownership");
}
