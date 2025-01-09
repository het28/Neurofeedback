import socket
import re
import numpy as np
from pylsl import StreamInlet, resolve_stream

class udpfeedback:

    def __init__(self):
        self.UDP_IP="127.0.0.1"
        self.UDP_PORT = 1977
    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
    def int2bstr(self,number):
        numstr = str(number)
        return  numstr.encode("ASCII")
    def sendcolor(self,color):
        MESSAGE =   b"(" + self.int2bstr(color[0]) + \
                    b"," + self.int2bstr(color[1]) + \
                    b"," + self.int2bstr(color[2]) + b")"
        self.sock.sendto(MESSAGE, (self.UDP_IP, self.UDP_PORT))
    def sendfeedback(self,feedback):
        blueval = min(255, round(feedback * 255))
        blueval = max(blueval,0)
        self.sendcolor([0,0,blueval])
    def bindListener(self):
        self.sock.bind((self.UDP_IP, self.UDP_PORT))
        self.sock.settimeout(0.5)
    def recievemsg(self):
        values = tuple()
        try:
            data = self.sock.recvfrom(16) # buffer size is 16 bytes
            string = data[0].decode('utf-8')
            match = re.match(r'\((\d+),(\d+),(\d+)\)', string) 
            if match: 
                values = tuple(map(int, match.groups())) 
        except socket.timeout:
            pass
        finally:
            pass
        return values

    def close(self):
        self.sock.close()
  
class lslreader:
    def __init__(self,chanlist):
        self.inlet = -1
        self.chanlist = chanlist
        self.neegchan = len(chanlist)
    def connect(self):
        # Find and resolve EEG stream
        print("Looking for an EEG stream...")
        streams = resolve_stream('type', 'EEG')
        if not streams:
            print("No EEG stream found.")
            return -1
        self.inlet = StreamInlet(streams[0])
        return 0
    def readdata(self):
        try:
            chunk, timestamp = self.inlet.pull_chunk()
            chunk = np.array(chunk)

            if len(chunk.shape)>1 and chunk.shape[0]>0 :
                if chunk.shape[1]== self.neegchan+1: # seems to have an additional channel
                    chunk=np.delete(chunk,self.neegchan,1) #delete last channel                          
                return np.transpose(chunk)
            else:
                return np.zeros((0,0))
        except Exception as e:
            print(f"Error: {e}")
            return np.zeros((0,0))