import time
from modules.hardware_service import HardwareService

s = HardwareService()
print('start collect_raw')
t0=time.time()
payload = s._collect_raw_payload()
print('collect_raw done', round(time.time()-t0,3))
print('payload keys', payload.keys())

print('start system')
t0=time.time()
system_data = s.system_service.collect()
print('system done', round(time.time()-t0,3), system_data)

print('start cpu')
t0=time.time()
cpu_data = s.cpu_service.collect(payload, system_data)
print('cpu done', round(time.time()-t0,3), cpu_data)

print('start memory')
t0=time.time()
memory_data = s.memory_service.collect()
print('memory done', round(time.time()-t0,3), memory_data)

print('start disk')
t0=time.time()
disk_data = s.disk_service.collect(payload)
print('disk done', round(time.time()-t0,3), disk_data)

print('start smart')
t0=time.time()
disk_data = s.smart_service.collect(disk_data)
print('smart done', round(time.time()-t0,3), disk_data)

print('start gpu')
t0=time.time()
gpu_data = s.gpu_service.collect(payload)
print('gpu done', round(time.time()-t0,3), gpu_data)

print('start motherboard')
t0=time.time()
motherboard_data = s.motherboard_service.collect()
print('motherboard done', round(time.time()-t0,3), motherboard_data)

print('start write files')
t0=time.time()
# mimic collect
from pathlib import Path

data = {
    'cpu': cpu_data,
    'memory': memory_data,
    'disks': disk_data,
    'gpu': gpu_data,
    'motherboard': motherboard_data,
    'system': system_data,
    'sensors': payload.get('sensors', []),
    'debug_file': str(Path(__file__).resolve().parent / 'hardware_debug.txt'),
    'log_file': str(Path(__file__).resolve().parent / 'hardware_service.log'),
    'dll_path': s._dll_path or '',
    'search_paths': s._search_paths,
    'collected_at': 'x',
}
s._write_debug_file(data)
s._write_log_file(data)
print('write files done', round(time.time()-t0,3))
