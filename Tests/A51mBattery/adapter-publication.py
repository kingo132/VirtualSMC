#!/usr/bin/env python3
import pathlib,subprocess,tempfile
root=pathlib.Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory(prefix='a51m-adapter-bridge-') as tmp:
 p=pathlib.Path(tmp)
 for h in ['Headers/kern_time.hpp','IOKit/pwr_mgt/IOPMPowerSource.h']:
  f=p/h;f.parent.mkdir(parents=True,exist_ok=True);f.write_text('#include "'+str(root/'Tests/A51mBattery/adapter-publication-stubs.hpp')+'"\n')
 # Compile the actual routing callback too, with owned original/completion state.
 text=(root/'Sensors/SMCBatteryManager/A51mAdapterExport.hpp').read_text()
 a=text.index('static bool completion(');b=text.index('\ninline void init()',a)
 callback=text[a:b]
 unit=(root/'Tests/A51mBattery/adapter-publication.cpp').read_text()
 pre='''
namespace HookFixture {
static bool routed=true,success=true; static unsigned originalCalls=0;
static const OSSymbol *detailsKey=nullptr;
static bool original(IOService *,const void *p){++originalCalls;delete static_cast<const uint32_t *>(p);return success;}
static auto originalCompletion=original;
#define FunctionCast(name,ptr) ptr
#define atomic_load_explicit(ptr,order) (*(ptr))
using A51mAdapter::publish;using A51mAdapter::isAdapterUpdate;
'''
 post='\n#undef FunctionCast\n#undef atomic_load_explicit\n}\n'
 unit=unit.replace('int main(){',pre+callback+post+'int main(){')
 spot='auto accepted=current();'
 extra='''
 HookFixture::detailsKey=&details;
 current()->removeObject("Watts");current()->removeObject("A51mFirmwareDesignRating");
 HookFixture::success=false;assert(!HookFixture::completion(&source,new uint32_t(0xd00)));assert(!watts());
 HookFixture::success=true;HookFixture::completion(&source,new uint32_t(0x1100));assert(!watts());
 HookFixture::routed=false;HookFixture::completion(&source,new uint32_t(0xd00));assert(!watts());
 HookFixture::routed=true;HookFixture::completion(&source,new uint32_t(0xd00));assert(watts()==480);
 assert(HookFixture::originalCalls==4); // Freed commands were never read after native completion.
 '''
 unit=unit.replace(spot,extra+spot);source=p/'publication.cpp';source.write_text(unit)
 exe=p/'test';subprocess.run(['clang++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=undefined','-I',str(p),'-I',str(root),str(source),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
