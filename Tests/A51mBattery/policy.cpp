#include "Sensors/SMCBatteryManager/A51mBatteryPolicy.hpp"
#include "Sensors/SMCBatteryManager/A51mBatteryTelemetry.hpp"
#include <cassert>
#include <cstdio>
#include <cstring>
#include <initializer_list>
using namespace A51mBattery;

struct State {
	uint32_t state=0, remainingCapacity=7077, lastFullChargeCapacity=7077;
	uint32_t presentRate=0, averageRate=0;
	uint32_t runTimeToEmpty=31404, averageTimeToEmpty=31404, timeToFull=0;
	uint32_t averageTimeToEmptyHW=0, timeToFullHW=0;
	int32_t signedPresentRate=0, signedAverageRate=0;
};

static void apply(State &s, bool capacity=true, bool present=true, bool average=true,
		bool hwEmpty=false, bool hwFull=false) {
	const auto original=s;
	applyTimePolicy(s,capacity,present,average,hwEmpty,hwFull);
	assert(s.state==original.state && s.remainingCapacity==original.remainingCapacity);
	assert(s.lastFullChargeCapacity==original.lastFullChargeCapacity);
	assert(s.presentRate==original.presentRate && s.averageRate==original.averageRate);
	assert(s.signedPresentRate==original.signedPresentRate && s.signedAverageRate==original.signedAverageRate);
}

int main(int argc,char **argv) {
	State s;
	apply(s); assert(s.runTimeToEmpty==65535 && s.averageTimeToEmpty==65535 && s.timeToFull==65535);
	s.presentRate=s.averageRate=30; apply(s); assert(s.runTimeToEmpty==65535 && s.averageTimeToEmpty==65535);
	s.state=1; s.presentRate=s.averageRate=7300; s.signedPresentRate=s.signedAverageRate=-7300;
	apply(s); assert(s.runTimeToEmpty==58 && s.averageTimeToEmpty==58 && s.timeToFull==65535);
	s.state=2; s.remainingCapacity=6000; s.presentRate=s.averageRate=1000;
	s.signedPresentRate=s.signedAverageRate=1000; apply(s);
	assert(s.timeToFull==64 && s.runTimeToEmpty==65535 && s.averageTimeToEmpty==65535);
	s.state=3; apply(s); assert(s.timeToFull==65535 && s.runTimeToEmpty==65535);
	s.state=4; apply(s); assert(s.averageTimeToEmpty==65535);
	s.state=1; s.presentRate=s.averageRate=0; apply(s); assert(s.runTimeToEmpty==65535);
	s.presentRate=s.averageRate=Unknown; apply(s); assert(s.averageTimeToEmpty==65535);
	s.presentRate=s.averageRate=1000; apply(s,false); assert(s.runTimeToEmpty==65535);
	apply(s,true,false,false); assert(s.runTimeToEmpty==65535 && s.averageTimeToEmpty==65535);
	s.averageTimeToEmptyHW=22; apply(s,true,true,true,true); assert(s.averageTimeToEmpty==22);
	s.averageTimeToEmptyHW=65535; apply(s,true,true,true,true); assert(s.averageTimeToEmpty==65535);
	s.averageTimeToEmptyHW=70000; apply(s,true,true,true,true); assert(s.averageTimeToEmpty==65535);
	s.state=2; s.timeToFullHW=17; apply(s,true,true,true,false,true); assert(s.timeToFull==17);
	apply(s,true,true,false,false,true); assert(s.timeToFull==65535);
	s.lastFullChargeCapacity=5000; apply(s); assert(s.timeToFull==65535);
	s.lastFullChargeCapacity=Unknown; apply(s); assert(s.timeToFull==65535);
	assert(minutes(65534,60)==65534 && minutes(65535,60)==65535);
	assert(minutes(1000000000,1000000)==60000); // Numerator must not overflow uint32_t.
	assert(minutes(Unknown,1000)==65535 && minutes(7077,0)==65535);
	assert(minutes(7077,Unknown)==65535 && hardwareMinutes(100000)==65535);
	for (uint32_t c: {0U,1U,7077U,1000000000U,Unknown})
		for (uint32_t rate: {0U,1U,30U,7300U,1000000U,Unknown}) {
			const auto result=minutes(c,rate);
			assert(result<=65535);
			if(result!=65535) assert(result==uint64_t(c)*60/rate);
		}
	Trace trace;
	for(uint64_t i=0;i<70;++i) {
		Record r; r.command=r.expectedCommand=((i/2)%2)?0x12:0x0b;
		r.value=r.expectedValue=((i/2)%2)?31404:uint16_t(-7300); r.receiveCount=2;
		r.phase=(i%2)?2:1; r.requestSequence=i/2+1;
		r.source.sequence=9; r.source.signedAverageRate=-7300; trace.append(r);
	}
	assert(trace.used==64 && trace.total==70 && trace.overwritten==6 && trace.nextIndex==6);
	assert(trace.records[trace.nextIndex].eventSequence==7);
	assert(trace.records[(trace.nextIndex+63)%64].eventSequence==70);
	assert(trace.dropped==0 && trace.reserved==0);
	if(argc==2) {auto f=fopen(argv[1],"wb"); assert(f); assert(fwrite(&trace,sizeof(trace),1,f)==1); fclose(f);}
	puts("A51m time-policy boundary cases and 64-record trace ring passed");
}
