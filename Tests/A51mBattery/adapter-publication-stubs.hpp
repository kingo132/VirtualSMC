#pragma once
#include <cstdint>
#include <cstring>
#include <cassert>
#include <map>
#include <string>
#include <vector>
namespace Test {inline unsigned alive=0,allocations=0;inline int failAt=-1;inline uint64_t now=2;inline bool alloc(){return failAt<0 || int(allocations++)!=failAt;}}
struct OSObject {int refs=1;OSObject(){++Test::alive;}virtual ~OSObject(){--Test::alive;}void retain(){++refs;}void release(){assert(refs>0);if(!--refs)delete this;}};
#define OSDynamicCast(t,o) dynamic_cast<t *>(o)
struct OSNumber:OSObject{uint64_t value;explicit OSNumber(uint64_t n):value(n){}static OSNumber*withNumber(uint64_t n,int){return Test::alloc()?new OSNumber(n):nullptr;}uint32_t unsigned32BitValue(){return uint32_t(value);}};
struct OSBoolean:OSObject{};
inline OSBoolean booleanTrue;inline OSBoolean*kOSBooleanTrue=&booleanTrue;
struct OSSymbol:OSObject{std::string value;explicit OSSymbol(const char*s):value(s){}};
struct OSDictionary:OSObject{
 std::map<std::string,OSObject*>values;
 ~OSDictionary(){for(auto&p:values)p.second->release();}
 OSObject*getObject(const char*k){auto i=values.find(k);return i==values.end()?nullptr:i->second;}
 bool setObject(const char*k,OSObject*o){if(!Test::alloc())return false;o->retain();auto old=getObject(k);if(old)old->release();values[k]=o;return true;}
 void removeObject(const char*k){auto i=values.find(k);if(i!=values.end()){i->second->release();values.erase(i);}}
 static OSDictionary*withDictionary(OSDictionary*d){if(!Test::alloc())return nullptr;auto copy=new OSDictionary;for(auto&p:d->values)if(!copy->setObject(p.first.c_str(),p.second)){copy->release();return nullptr;}return copy;}
};
struct OSData:OSObject{std::vector<uint8_t>bytes;OSData(const void*p,size_t n):bytes((const uint8_t*)p,(const uint8_t*)p+n){}size_t getLength(){return bytes.size();}const void*getBytesNoCopy(){return bytes.data();}};
struct Meta{const char*name;const char*getClassName(){return name;}};
struct IOService:OSObject{
 Meta meta;IOService*provider=nullptr;OSDictionary properties;
 explicit IOService(const char*n):meta{n}{}Meta*getMetaClass(){return &meta;}IOService*getProvider(){return provider;}
 OSObject*copyProperty(const char*k){auto o=properties.getObject(k);if(o)o->retain();return o;}
 void setProperty(const char*k,uint64_t n,int bits){auto o=OSNumber::withNumber(n,bits);if(o){properties.setObject(k,o);o->release();}}
};
struct IOPMPowerSource:IOService{
 OSDictionary internal,published;bool connected=true;unsigned statusCalls=0;
 IOPMPowerSource():IOService("AppleSmartBattery"){}
 bool externalConnected(){return connected;}OSObject*getPSProperty(const OSSymbol*k){return internal.getObject(k->value.c_str());}
 void updateStatus(){++statusCalls;for(auto&p:internal.values)published.setObject(p.first.c_str(),p.second);}
 protected:void setPSProperty(const OSSymbol*k,OSObject*o){internal.setObject(k->value.c_str(),o);}
 public:void setup(const OSSymbol*k,OSObject*o){setPSProperty(k,o);}
};
inline uint64_t getCurrentTimeNs(){return Test::now;}
