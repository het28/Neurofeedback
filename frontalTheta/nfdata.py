import numpy as np
import os, time, glob

class params:
    def __init__(self):
        self.fbmodule = "blueSquareUDP" # sends color values via UDP
        self.fbprotocol = "frontaltheta"
        self.datapath = "../data/" 
        self.nfrunlength = 5*60 # default run length in sec
        self.calibrunlength = 60 # default training run length in sec
        self.srate = 250 # default srate

class rawdata:
    def __init__(self,nchan,nsamp):
        self.nchan = nchan
        self.nsamp = nsamp
        self.srate = 0 # in Hz will be set during execution
        self.eegsignals = np.zeros((nchan,nsamp))
        self.sampcount = 0
    def adddata(self,data: np.array):
        if len(data.shape)==2:
            nsamp = data.shape[1]
            nd = self.eegsignals.shape[1]
            nsamp = min(nsamp,nd-self.sampcount)
            if nsamp>0:                                           
                self.eegsignals[:, range(self.sampcount,self.sampcount+nsamp)] = data[:,range(nsamp)]
                self.sampcount += nsamp 

class fbdata:
    def __init__(self):
        self.position = list()
        self.amplitude = list()
        self.feedbackvalue = list()
        self.loweredge = list()
        self.upperedge = list()
        self.timestamp = list()
        self.preprocdata = list()

    def adddata(self,position:int,amplitude:float,feedbackvalue:float,lowedge:float,upedge:float,tstamp:float):
        self.position.append(position)
        self.amplitude.append(amplitude)
        self.feedbackvalue.append(feedbackvalue)
        self.loweredge.append(lowedge)
        self.upperedge.append(upedge)
        self.timestamp.append(tstamp)
    def addpreprocdata(self,signal:np.array):
        self.preprocdata.append(signal)
class io:
    def preparedata4mat(eeg:rawdata, outcome:fbdata):
        data = { 'eegsignals':np.array(eeg.eegsignals), 
                 'srate':np.array(eeg.srate),
                 'timestamp':np.array(outcome.timestamp),
                 'position':np.array(outcome.position),
                 'amplitude':np.array(outcome.amplitude),
                 'feedbackvalue':np.array(outcome.feedbackvalue),
                 'loweredge':np.array(outcome.loweredge),
                 'upperedge':np.array(outcome.upperedge),
                 'preprocdata':np.array(outcome.preprocdata)} 
        return data 
    def generatefilename(prm:params, subjcode):
        timestamp = time.strftime("%Y%m%d-%H%M%S") 
        flist = glob.glob(os.path.join(prm.datapath, f"{subjcode}_run*.mat")) 
        filename = f"{subjcode}_run{len(flist)}_{timestamp}.mat" 
        return os.path.join(prm.datapath, filename)
