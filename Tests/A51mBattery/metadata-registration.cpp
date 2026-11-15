// Owned fixtures for the actual key-registration blocks. No hardware access.
#include <set>
#include <cassert>
#include <cstddef>
#include <iostream>
#include <string>
bool testFlag=false;int testVersion=25; bool recorded=false;
bool checkKernelArgument(const char* name) {assert(std::string(name)=="-a51mbatmeta");return testFlag;}
void setProperty(const char*,bool v){recorded=v;}
int getKernelVersion(){return testVersion;}
namespace KernelVersion {constexpr int BigSur=20;}
constexpr unsigned short defaultBatteryCellVoltage=16000;
constexpr int KeyACEN=1,KeyACFP=2,KeyACID=3,KeyACIN=4,SmcKeyTypeCh8s=0;
int KeyBC1V(std::size_t i){return 100+int(i);}
struct ACIN{};struct ACID{};
struct State {unsigned adapterCount=0;};State st;
struct BatteryManager{static State* getShared(){return &st;}};
struct {std::set<int> data;} vsmcPlugin;
namespace VirtualSMCAPI {
 template<class T> int valueWithUint8(int,T* p){delete p;return 0;}
 template<class T> int valueWithFlag(bool,T* p){delete p;return 0;}
 template<class T> int valueWithData(void*,int,int,T* p){delete p;return 0;}
 int valueWithUint16(int){return 0;}
 void addKey(int k,std::set<int>& d,int){assert(d.insert(k).second);}
}
void productionRegistration(std::size_t batCount) {
/* ACTUAL_REGISTRATION */

}
int main(){int cases=0;
 for(bool flag:{false,true})for(int version:{19,20,25})for(unsigned adapters:{0u,1u,2u})for(std::size_t batteries:{0u,1u,2u}){
 testFlag=flag;testVersion=version;st.adapterCount=adapters;vsmcPlugin.data.clear();productionRegistration(batteries);
 assert(recorded==flag);
 for(int k:{KeyACEN,KeyACFP,KeyACIN})assert(vsmcPlugin.data.count(k)==(adapters>0));
 assert(vsmcPlugin.data.count(KeyACID)==(adapters>0&&!flag));
 for(std::size_t n=1;n<=2;n++)assert(vsmcPlugin.data.count(KeyBC1V(n))==(n<=batteries&&version>=20&&!flag));
 cases++;
 }
 std::cout<<"PASS: "<<cases<<" actual key-registration cases; AC presence unchanged; synthetic keys omitted only with explicit opt-in\n";
}
