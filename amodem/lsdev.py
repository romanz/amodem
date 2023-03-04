from ctypes import *

class PADeviceInfo(Structure):
    _fields_ = [
        ("structVersion", c_int),
        ("name", c_char_p),
        ("hostApi", c_int),
        ("maxInputChannels", c_int),
        ("maxOutputChannels", c_int),
        ("defaultLowInputLatency", c_double),
        ("defaultLowOutputLatency", c_double),
        ("defaultHighInputLatency", c_double),
        ("defaultHighOutputLatency", c_double),
        ("defaultSampleRate", c_double)
    ]

def printDeviceDetails(device):
    contents = device.contents
    print(str(contents.name, 'ascii'))
    print(f"Input Channels: {contents.maxInputChannels}")
    print(f"Output Channels: {contents.maxOutputChannels}")
    print(f"Default Sample Rate: {contents.defaultSampleRate}")

def getDevices(interface):
    num_devices = interface.call('GetDeviceCount', restype=c_int)
    for i in range(num_devices):
        device_i = interface.call('GetDeviceInfo', i, restype=POINTER(PADeviceInfo))
        device_str = str(device_i.contents.name, 'ascii')
        print(f"Device #{i}: {device_str}")

def getParticularDevice(interface, device_id):
    device = interface.call('GetDeviceInfo', device_id, restype=POINTER(PADeviceInfo))
    printDeviceDetails(device)
