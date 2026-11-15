// Read-only packet and numeric semantics. Synthetic fixtures; no hardware.
#include "Sensors/SMCBatteryManager/A51mDellTelemetry.hpp"
#include <cassert>
#include <cstdio>
#include <cstring>
#include <initializer_list>
using namespace A51mDell;
int main() {
    Packet p; assert(p.signature() && p.size==32);
    assert(get32(p.bytes+4)==0xfea3 && get32(p.bytes+12)==0x141);
    assert(get32(p.bytes+24)==4 && get32(p.bytes+28)==0);
    Reply reply;
    put32(p.bytes+4,DiagMagic);put32(p.bytes+28,DellMagic);put32(p.bytes+20,0x148);
    assert(decode(p.bytes,p.size,4,reply) && validSignature(reply));
    for(auto field:NumericFields) {
        assert(p.number(field,1,false)); assert(p.size==60);
        assert(get32(p.bytes+4)==0x21a3);
        assert(get32(p.bytes+12)==((uint32_t(uint8_t(field))<<8)|1));
        assert(!std::memcmp(p.bytes+28,"DELLCODE",8));
        put32(p.bytes+4,21);assert(decode(p.bytes,p.size,32,reply));
        uint16_t value=0;assert(wordValue(reply,0x21a3,value)&&value==21);
        put32(p.bytes+4,0x21a3);assert(decode(p.bytes,p.size,32,reply));
        assert(!wordValue(reply,0x21a3,value));
        for(uint16_t error:{uint16_t(0xfffe),uint16_t(0xffff)}) {
            put32(p.bytes+4,error);assert(decode(p.bytes,p.size,32,reply));
            assert(!wordValue(reply,0x21a3,value));
        }
    }
    for(unsigned command=0;command<256;++command) {
        bool allowed=false;for(auto f:NumericFields) allowed|=uint8_t(f)==command;
        assert(p.number(Field(command),1,true)==allowed);
        assert(!p.number(Field(command),0,true));assert(!p.number(Field(command),2,true));
    }
    for(uint8_t selector=0;selector<=6;++selector) {
        assert(p.adapter(selector));assert(get32(p.bytes+4)==0x24a3);
        assert(get32(p.bytes+12)==uint32_t(selector)<<8);assert(p.size==32);
    }
    assert(!p.adapter(7));
    for(uint8_t command:{uint8_t(0x20),uint8_t(0x21),uint8_t(0x22),uint8_t(0x23),uint8_t(0x37)}) {
        assert(p.string(command,1,true));assert(!std::memcmp(p.bytes+28,"DELLDIAG",8));
        assert(p.payloadSize==unsigned(command==0x37?256:32));
    }
    assert(!p.string(0x26,1,false)); // No raw-analytics control command.
    assert(p.number(Field::Cycles,1,false));
    for(unsigned i:{0U,8U,16U,24U}) {
        auto old=p.bytes[i];p.bytes[i]^=1;assert(!decode(p.bytes,p.size,32,reply));p.bytes[i]=old;
    }
    assert(!decode(p.bytes,p.size-1,32,reply));assert(!decode(nullptr,60,32,reply));
    uint32_t cap=0;
    assert(capacityMah(9000,0x8000,11400,cap)&&cap==7894);
    assert(capacityMah(9000,0,11400,cap)&&cap==9000);
    assert(!capacityMah(9000,0x8000,0,cap));assert(!capacityMah(0xffff,0,11400,cap));
    assert(validTemperature(2930)&&!validTemperature(0xffff));
    assert(validDate(uint16_t((2024-1980)<<9 | 2<<5 | 29)));
    assert(!validDate(uint16_t((2023-1980)<<9 | 2<<5 | 29)));
    assert(!validDate(0));
    puts("PASS: read allowlist, exact A3 register bytes, markers, errors, malformed packets, dates and capacity-mode conversion");
}
