#ifndef A51M_DELL_HOST_STUBS_HPP
#define A51M_DELL_HOST_STUBS_HPP
#include "Sensors/SMCBatteryManager/A51mDellProtocol.hpp"
#include <cassert>
#include <cstring>
#include <vector>
#include <algorithm>
namespace Host {
inline uint64_t clock=1, duration=1000000;
inline int alive=0,calls=0,wdgCalls=0;
inline bool missing=false,badDescriptor=false,badSignature=false,shortReply=false;
inline bool cycleError=false,echoStrings=false;
inline bool dual=false,dualFailure=false,dualBadType=false;
inline uint32_t dualCount=2,dualCountAfter=2,dualWatts[2]={240,240},dualStatus=1;
inline unsigned dualCountQueries=0;
}
using IOReturn=int;
constexpr int kIOReturnSuccess=0,kIORegistryIterateRecursively=1;
inline void *gIOACPIPlane=nullptr;
struct OSObject {
    int refs=1;
    OSObject(){++Host::alive;}
    virtual ~OSObject(){--Host::alive;}
    void retain(){++refs;}
    void release(){assert(refs>0);if(!--refs)delete this;}
};
#define OSDynamicCast(type,obj) dynamic_cast<type*>(obj)
struct OSNumber:OSObject {
    uint64_t value;
    explicit OSNumber(uint64_t v):value(v){}
    static OSNumber*withNumber(uint64_t v,int){return new OSNumber(v);}
    uint64_t unsigned64BitValue(){return value;}
};
struct OSData:OSObject {
    std::vector<uint8_t> bytes;
    static OSData*withBytes(const void*p,size_t n){auto d=new OSData;d->bytes.assign(static_cast<const uint8_t*>(p),static_cast<const uint8_t*>(p)+n);return d;}
    const void*getBytesNoCopy(){return bytes.data();}
    unsigned getLength(){return unsigned(bytes.size());}
};
struct IOACPIPlatformDevice:OSObject {
    const char*getName(){return Host::dual ? "AMW1" : "DIAG";}
    int validateObject(const char*n){return std::strcmp(n,Host::dual ? "WMAX" : "WMDM")?1:0;}
    int evaluateObject(const char*n,OSObject**out,OSObject**args=nullptr,unsigned count=0) {
        using namespace A51mDell;
        if(!std::strcmp(n,"_WDG")) {
            ++Host::wdgCalls;
            uint8_t d[20]={0x52,0xee,0xdd,0xf1,0x3c,0x06,0x84,0x47,0xa1,0x1e,0x8a,0x06,0x68,0x4b,0x9b,0x01,'D','M',1,2};
            if(Host::dual) {
                const uint8_t awcc[20]={0xce,0x91,0x05,0xa7,0x97,0xa9,0xda,0x11,0xb0,0x12,0xb6,0x22,0xa1,0xef,0x54,0x92,'A','X',1,2};
                std::memcpy(d,awcc,20);
            }
            if(Host::badDescriptor)d[0]^=1;
            *out=OSData::withBytes(d,sizeof(d));return 0;
        }
        if(Host::dual) {
            assert(!std::strcmp(n,"WMAX")&&count==3);
            assert(dynamic_cast<OSNumber*>(args[0])->value==0);
            assert(dynamic_cast<OSNumber*>(args[1])->value==0x1c);
            auto input=dynamic_cast<OSData*>(args[2]);assert(input&&input->bytes.size()==4);
            auto &b=input->bytes;assert(b[2]==0&&b[3]==0);
            Host::clock+=Host::duration;++Host::calls;
            if(Host::dualFailure) return 1;
            uint32_t value=0;
            if(b[0]==1) {assert(b[1]==0);value=Host::dualCountQueries++ ? Host::dualCountAfter : Host::dualCount;}
            else if(b[0]==2) {assert(b[1]<2);value=Host::dualWatts[b[1]];}
            else {assert(b[0]==4&&b[1]==0);value=Host::dualStatus;}
            *out=Host::dualBadType ? static_cast<OSObject*>(OSData::withBytes(&value,4)) : new OSNumber(value);
            return 0;
        }
        assert(!std::strcmp(n,"WMDM")&&count==3);
        assert(dynamic_cast<OSNumber*>(args[0])->value==0);
        assert(dynamic_cast<OSNumber*>(args[1])->value==1);
        auto input=dynamic_cast<OSData*>(args[2]);assert(input);
        auto b=input->bytes;auto eax=get32(b.data()+4),ebx=get32(b.data()+12);
        Host::clock+=Host::duration;++Host::calls;
        if(eax==0xfea3) {
            if(!Host::badSignature) {put32(b.data()+4,DiagMagic);put32(b.data()+28,DellMagic);put32(b.data()+20,0x148);}
        } else if(eax==0x21a3) {
            assert((ebx&255)==1 && readFieldAllowed(uint8_t(ebx>>8)));
            uint16_t value=0;
            switch(uint8_t(ebx>>8)) {
                case 0x17:value=Host::cycleError?0xffff:21;break;
                case 0x08:value=2930;break;
                case 0x03:value=2;break;
                case 0x09:value=12352;break;
                case 0x0a:value=0;break;
                case 0x0d:value=84;break;
                case 0x0f:value=6000;break;
                case 0x10:value=8067;break;
                case 0x18:value=9000;break;
                case 0x19:value=11400;break;
                case 0x1a:value=49;break;
                case 0x1b:value=uint16_t((2024-1980)<<9|2<<5|29);break;
                case 0x1c:value=1234;break;
                case 0x00:value=0x4488;break;
                default:value=0;break;
            }
            put32(b.data()+4,value);
        } else if(eax==0x24a3) {
            auto selector=ebx>>8;assert((ebx&255)==0&&selector<=6);
            const uint16_t values[]={123,19500,16900,330,uint16_t((2024-1980)<<9|2<<5|29),2345,330};
            put32(b.data()+4,values[selector]);put32(b.data()+12,3);
        } else if(eax==0x23a3) {
            assert((ebx&255)==1);
            put32(b.data()+4,5);
            if(!Host::echoStrings)std::memcpy(b.data()+28,"DELL\0",5);
        } else assert(false);
        if(Host::shortReply)b.pop_back();
        *out=OSData::withBytes(b.data(),b.size());return 0;
    }
};
inline IOACPIPlatformDevice hostDevice;
struct IORegistryIterator:OSObject {
    bool done=false;
    static IORegistryIterator*iterateOver(void*,int){return new IORegistryIterator;}
    IOACPIPlatformDevice*getNextObject(){if(done||Host::missing)return nullptr;done=true;return &hostDevice;}
};
inline uint64_t getCurrentTimeNs(){return Host::clock;}
#endif
