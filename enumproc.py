from ctypes import *
psapi = windll.psapi
kernel = windll.kernel32


def c_buffer(size, type=c_byte):
    class my_buffer(Array):
        _length_=size
        _type_=type
        def clear(self):
            for i in range(self._length_):
                self[i]=0
    return my_buffer()

def EnumProcesses():
    arr = c_ulong * 1024
    lpidProcess= arr()
    cb = sizeof(lpidProcess)
    cbNeeded = c_ulong()
    hModule = c_ulong()
    count = c_ulong()
    modname = c_buffer(256)
    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_READ = 0x0010
    
    #Call Enumprocesses to get hold of process id's
    psapi.EnumProcesses(byref(lpidProcess),
                        cb,
                        byref(cbNeeded))
    
    nReturned = cbNeeded.value//sizeof(c_ulong())
   
    pidProcess = [i for i in lpidProcess][:nReturned]
    
    for pid in pidProcess:
        
        #Get handle to the process based on PID
        hProcess = kernel.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
                                      False, pid)
        if hProcess:
            psapi.EnumProcessModules(hProcess, byref(hModule), sizeof(hModule), byref(count))
            psapi.GetModuleBaseNameA(hProcess, hModule.value, modname, sizeof(modname))

            name = str(modname,"utf-8").strip("\0")

            print(name)

            modname.clear()

            kernel.CloseHandle(hProcess)
if __name__ == '__main__':
    EnumProcesses()
