#include "Sensors/SMCBatteryManager/A51mDualAdapterAcpi.hpp"
#include <cstdio>
using namespace A51mDualAdapter;
void reset() {
    assert(Host::alive==1 && hostDevice.refs==1);
    Host::dual=true;Host::clock=1;Host::duration=1000000;Host::calls=Host::wdgCalls=0;
    Host::missing=Host::badDescriptor=Host::dualFailure=Host::dualBadType=false;
    Host::dualCount=Host::dualCountAfter=2;Host::dualCountQueries=0;
    Host::dualWatts[0]=Host::dualWatts[1]=240;Host::dualStatus=1;
}
int main() {
    reset();{Reader r;assert(!r.refresh(false,480,1) && !Host::calls);}
    reset();{Reader r;assert(r.refresh(true,480,1));assert(Host::calls==5 && r.data.validMask==3);
        assert(r.data.ratedWatts[0]==240 && r.data.ratedWatts[1]==240);
        assert(validPair(r.data,Host::clock,480,1));assert(!validPair(r.data,Host::clock,480,2));assert(!validPair(r.data,Host::clock,330,1));
        assert(!validPair(r.data,r.data.sampledNs-1,480,1));
        assert(!validPair(r.data,r.data.sampledNs+120000000001ULL,480,1));
        assert(!r.refresh(true,480,1)&&Host::calls==5);r.invalidate();assert(!r.data.validMask&&!r.data.sampledNs);
        assert(!r.refresh(true,480,1)&&Host::calls==5);
        Host::clock+=1000000000ULL;Host::dualCountQueries=0;assert(r.refresh(true,480,1));
        assert(!r.refresh(true,0,1)&&!r.data.validMask);}
    reset();{Reader r;Host::dualWatts[0]=330;Host::dualWatts[1]=180;assert(r.refresh(true,510,1));}
    reset();{Reader r;Host::dualStatus=2;assert(r.refresh(true,480,1));assert(r.data.firmwareStatus==2);}
    reset();{Reader r;Host::dualStatus=9;assert(!r.refresh(true,480,1)&&!r.data.validMask);}
    reset();{Reader r;Host::dualCount=Host::dualCountAfter=1;
        assert(!r.refresh(true,240,1)&&!r.data.validMask&&Host::calls==5);}
    reset();{Reader r;Host::dualCountAfter=1;assert(!r.refresh(true,480,1)&&!r.data.validMask);}
    reset();{Reader r;assert(!r.refresh(true,330,1)&&r.data.status==Status::Inconsistent);}
    for(uint32_t watts:{0U,3001U,65535U,UINT32_MAX}) {
        reset();Reader r;Host::dualWatts[0]=watts;assert(!r.refresh(true,480,1)&&!r.data.validMask);
    }
    for(uint32_t count:{0U,3U,UINT32_MAX}) {
        reset();Reader r;Host::dualCount=count;assert(!r.refresh(true,480,1)&&!r.data.validMask&&Host::calls==1);
    }
    reset();{Reader r;Host::missing=true;assert(!r.refresh(true,480,1)&&!Host::calls&&r.data.status==Status::NoEndpoint);}
    reset();{Reader r;Host::badDescriptor=true;assert(!r.refresh(true,480,1)&&!Host::calls&&r.data.status==Status::InvalidDescriptor);}
    reset();{Reader r;Host::dualFailure=true;assert(!r.refresh(true,480,1)&&r.data.failures==1&&Host::calls==1);}
    reset();{Reader r;Host::dualBadType=true;assert(!r.refresh(true,480,1)&&!r.data.validMask&&Host::calls==1);}
    reset();{Reader r;Host::duration=21000000;assert(!r.refresh(true,480,1)&&r.data.status==Status::SlowTransport&&Host::calls==1);
        r.invalidate();Host::clock+=61000000000ULL;assert(!r.refresh(true,480,1)&&Host::calls==1);}
    reset();Host::dual=false;
    puts("PASS: actual bounded WMAX reader; dual 240/240 and 330/180, firmware status, count races, stale/invalid fields, single-port ambiguity, slow-stop and ownership; firmware execution not simulated");
}
