#include <cstdio>
#include <cstring>
#include <cassert>
#include <cmath>
#include "Sensors/SMCBatteryManager/A51mDellMetadata.hpp"
using namespace A51mDell;
struct Battery {
    static constexpr size_t MaxStringLen=32;
    Telemetry a51mDellInfo {};
    unsigned cycle=0,manufactureDate=0;
    unsigned designCapacity=7895,fullCapacity=7077,voltage=12352;
    int current=-6710;
    char serial[32]="fallback",manufacturer[32]="ACPI",deviceName[32]="BATT",batteryType[32]="LION";
    struct {
        uint16_t temperatureDecikelvin=2931;
        double temperature=0;
        bool publishTemperatureKey=false;
    } state;
};
int main() {
    Telemetry raw; raw.set(Field::Cycles,21);
    Battery b;applyMetadata(raw,b);assert(b.cycle==0);
    raw.status=Status::Active;raw.set(Field::Temperature,2930);
    raw.set(Field::ManufactureDate,uint16_t((2024-1980)<<9|2<<5|29));
    raw.set(Field::SerialNumber,1234);raw.stringValid=7;
    memcpy(raw.strings[0],"DELL\0",5);raw.stringLength[0]=5;
    memset(raw.strings[1],'X',256);raw.stringLength[1]=256;
    raw.strings[2][0]=0xff;raw.stringLength[2]=1;
    applyMetadata(raw,b);assert(b.cycle==21);
    assert(!strcmp(b.serial,"1234")&&!strcmp(b.manufacturer,"DELL"));
    assert(strlen(b.deviceName)==31&&!strcmp(b.batteryType,"LION"));
    assert(b.state.temperatureDecikelvin==2930 && b.state.publishTemperatureKey);
    assert(std::abs(b.state.temperature-19.85)<0.000001);
    assert(b.designCapacity==7895&&b.fullCapacity==7077&&b.current==-6710&&b.voltage==12352);
    raw.stringLength[0]=257;strcpy(b.manufacturer,"ACPI");applyMetadata(raw,b);
    assert(!strcmp(b.manufacturer,"ACPI"));
    raw.set(Field::Temperature,0xffff);raw.set(Field::ManufactureDate,0);
    b.state.temperatureDecikelvin=2931;b.manufactureDate=123;
    applyMetadata(raw,b);assert(b.state.temperatureDecikelvin==2931&&b.manufactureDate==123);
    puts("PASS: production metadata mapping, missing/error fields, exact temperature conversion, string bounds, preserved ACPI units/current/voltage");
}
