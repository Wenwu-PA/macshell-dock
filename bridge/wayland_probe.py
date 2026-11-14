"""Read the Wayland registry without binding globals or creating any surface."""
import os
from pathlib import Path
import socket
import struct


def globals_available():
    display=os.environ.get('WAYLAND_DISPLAY')
    if not display:raise RuntimeError('WAYLAND_DISPLAY is absent')
    path=Path(display)
    if not path.is_absolute():
        runtime=os.environ.get('XDG_RUNTIME_DIR')
        if not runtime:raise RuntimeError('XDG_RUNTIME_DIR is absent')
        path=Path(runtime)/path
    names=set();buffer=b''
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
        client.settimeout(3);client.connect(str(path))
        # wl_display.get_registry(new_id=2), then wl_display.sync(new_id=3).
        client.sendall(struct.pack('=III',1,(12<<16)|1,2)+struct.pack('=III',1,12<<16,3))
        while True:
            chunk=client.recv(65536)
            if not chunk:raise RuntimeError('Wayland disconnected before registry sync')
            buffer+=chunk
            while len(buffer)>=8:
                obj,header=struct.unpack_from('=II',buffer);size=header>>16;opcode=header&65535
                if size<8 or size%4:raise RuntimeError('Malformed Wayland message')
                if len(buffer)<size:break
                payload=buffer[8:size];buffer=buffer[size:]
                if obj==3 and opcode==0:return names
                if obj==1 and opcode==0:raise RuntimeError('Wayland registry request rejected')
                if obj==2 and opcode==0:
                    if len(payload)<12:raise RuntimeError('Malformed registry global')
                    length=struct.unpack_from('=I',payload,4)[0]
                    if length<1 or 8+length>len(payload):raise RuntimeError('Malformed registry interface')
                    names.add(payload[8:8+length-1].decode('ascii'))
