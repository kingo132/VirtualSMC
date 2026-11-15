#include "Sensors/SMCBatteryManager/A51mAdapterPolicy.hpp"
#include <cassert>
#include <cstdio>
#include <fstream>
#include <iterator>
#include <vector>
using namespace A51mAdapter;
int main(int argc,char **argv) {
    assert(argc==2);
    std::ifstream file(argv[1],std::ios::binary);
    std::vector<uint8_t> image {std::istreambuf_iterator<char>(file),{}};
    assert(knownImage(image.data(),image.size()));
    assert(!knownImage(nullptr,0));
    for(size_t length=0;length<32;++length) assert(!knownImage(image.data(),length));
    auto bad=image;bad[4]^=1;assert(!knownImage(bad.data(),bad.size()));
    bad=image;bad[36]=0;bad[37]=0;bad[38]=0;bad[39]=0;
    assert(!knownImage(bad.data(),bad.size()));
    // Change the UUID in an otherwise valid image.
    size_t at=32;
    while(A51mDell::get32(image.data()+at)!=0x1b)at+=A51mDell::get32(image.data()+at+4);
    bad=image;bad[at+8]^=1;assert(!knownImage(bad.data(),bad.size()));
    bad=image;A51mDell::put32(bad.data()+20,UINT32_MAX);assert(!knownImage(bad.data(),bad.size()));
    A51mDell::Telemetry sample {};
    sample.status=A51mDell::Status::Active;sample.adapterValid=127;
    sample.adapterAx[3]=480;sample.adapterAx[6]=330;sample.adapterBx[6]=3;
    sample.adapterSampledNs=1;
    assert(designWatts(sample,2,true)==480); // Attached total, not the static 330 W field.
    assert(!designWatts(sample,2,false));
    assert(!designWatts(sample,0,true));
    assert(designWatts(sample,1+MaxAgeNs,true)==480);
    assert(!designWatts(sample,2+MaxAgeNs,true));
    auto valid=sample;
    for(uint32_t status=0;status<7;++status) {
        sample=valid;sample.status=A51mDell::Status(status);assert(!designWatts(sample,2,true));
    }
    for(uint16_t flags:{0,1,2}) {
        sample=valid;sample.adapterBx[6]=flags;assert(!designWatts(sample,2,true));
    }
    sample=valid;sample.adapterValid&=~(1U<<6);assert(!designWatts(sample,2,true));
    sample=valid;sample.adapterValid&=~(1U<<3);assert(!designWatts(sample,2,true));
    sample=valid;sample.adapterAx[6]=330;sample.adapterAx[3]=0;assert(!designWatts(sample,2,true));
    sample=valid;sample.adapterSampledNs=0;assert(!designWatts(sample,2,true));
    sample=valid;sample.schema=1;assert(!designWatts(sample,2,true));
    for(uint16_t value:{0,3001,65534,65535}) {
        sample=valid;sample.adapterAx[3]=value;assert(!designWatts(sample,2,true));
    }
    assert(isAdapterUpdate(0xd00)&&isAdapterUpdate(0x1300));
    assert(!isAdapterUpdate(0x1100)&&!isAdapterUpdate(0)&&!isAdapterUpdate(UINT32_MAX));
    puts("PASS: actual adapter rating policy, exact installed image UUID/CPU/layout, malformed image rejection, static/dynamic separation, power-source/PSID/freshness guards and native command scope; no kernel execution");
}
