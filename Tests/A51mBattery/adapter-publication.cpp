#include "Sensors/SMCBatteryManager/A51mAdapterPublication.hpp"
#include <cstdio>
using namespace A51mAdapter;
void number(OSDictionary*d,const char*k,uint64_t n){auto o=OSNumber::withNumber(n,32);assert(o&&d->setObject(k,o));o->release();}
int main(){auto baseline=Test::alive;{
 OSSymbol details("AdapterDetails");IOService controller("SMCSMBusController"),manager("AppleSmartBatteryManager");IOPMPowerSource source;
 source.provider=&manager;manager.provider=&controller;
 auto d=new OSDictionary;number(d,"FamilyCode",0);number(d,"Preserved",42);source.setup(&details,d);d->release();
 A51mDell::Telemetry raw{};raw.status=A51mDell::Status::Active;raw.adapterValid=(1U<<3)|(1U<<6);raw.adapterAx[3]=480;raw.adapterAx[6]=330;raw.adapterBx[6]=3;raw.adapterSampledNs=1;
 auto setRaw=[&]{auto data=new OSData(&raw,sizeof(raw));assert(controller.properties.setObject("A51mDellTelemetry",data));data->release();};setRaw();
 auto current=[&]{return OSDynamicCast(OSDictionary,source.getPSProperty(&details));};
 auto watts=[&]{auto n=OSDynamicCast(OSNumber,current()->getObject("Watts"));return n?n->unsigned32BitValue():0;};
 publish(&source,&details);assert(watts()==480);assert(current()->getObject("A51mFirmwareDesignRating")==kOSBooleanTrue);
 assert(OSDynamicCast(OSNumber,current()->getObject("Preserved"))->unsigned32BitValue()==42);
 assert(source.statusCalls==0&&!source.published.getObject("AdapterDetails")); // No partial-poll flush.
 source.updateStatus();assert(source.published.getObject("AdapterDetails")==current());
 auto accepted=current();publish(&source,&details);assert(current()==accepted); // No dictionary churn.
 raw.adapterAx[3]=370;setRaw();publish(&source,&details);assert(watts()==370);assert(source.statusCalls==1);
 source.connected=false;publish(&source,&details);assert(!watts()&&!current()->getObject("A51mFirmwareDesignRating"));
 source.connected=true;publish(&source,&details);assert(watts()==370);
 Test::now=MaxAgeNs+2;publish(&source,&details);assert(!watts());Test::now=2;
 publish(&source,&details);assert(watts()==370);
 raw.adapterValid=0;setRaw();publish(&source,&details);assert(!watts());
 raw.adapterValid=(1U<<3)|(1U<<6);setRaw();
 // Native data wins; the bridge owns neither this value nor its lifecycle.
 number(current(),"Watts",96);publish(&source,&details);assert(watts()==96);
 source.connected=false;publish(&source,&details);assert(watts()==96);source.connected=true;current()->removeObject("Watts");
 // Wrong provider, wrong class, absent dictionary, malformed record all fail closed.
 manager.meta.name="OtherManager";publish(&source,&details);assert(!watts());manager.meta.name="AppleSmartBatteryManager";
 controller.meta.name="OtherController";publish(&source,&details);assert(!watts());controller.meta.name="SMCSMBusController";
 source.meta.name="OtherBattery";publish(&source,&details);assert(!watts());source.meta.name="AppleSmartBattery";
 auto malformed=new OSData(&raw,8);controller.properties.setObject("A51mDellTelemetry",malformed);malformed->release();publish(&source,&details);assert(!watts());setRaw();
 // Every allocation failure leaves the prior dictionary, fields and refcounts intact.
 bool completed=false;for(int i=0;i<24;++i){auto old=current();Test::allocations=0;Test::failAt=i;publish(&source,&details);Test::failAt=-1;if(watts()){assert(watts()==370);completed=true;break;}assert(current()==old);}
 assert(completed);publish(nullptr,&details);publish(&source,nullptr);
 }assert(Test::alive==baseline);
 puts("PASS: production adapter publication; 480/370 W changes, native precedence, detach/expiry/invalid data removal, provider isolation, OOM ownership, and deferred native updateStatus; Apple runtime/UI not simulated");}
