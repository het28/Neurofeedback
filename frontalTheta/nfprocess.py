import nfdata
import numpy as np
import scipy.signal
from scipy.fftpack import fft 
import time
import matplotlib.pyplot as plt

class datasnippet:
    def __init__(self,fbp,srate):
        self.srate = srate
        self.refreshsamps = round( fbp.fbrefresh * srate)
        self.windowsamps = round( fbp.windowwidth * srate)
        self.curfbevent = self.windowsamps
        self.nextfbevent = self.windowsamps
        self.chunk = np.zeros((len( fbp.chanlist),self.windowsamps))

    def refresh(self,eeg: nfdata.rawdata):
        startsamp = max(0,self.nextfbevent-self.windowsamps)
        self.chunk = eeg.eegsignals[:, range(startsamp, startsamp+self.windowsamps)]
        snippet=self
        self.curfbevent = self.nextfbevent
        self.nextfbevent += self.refreshsamps
        if self.nextfbevent >= eeg.nsamp:
            self.nextfbevent = eeg.nsamp-1

class process:
    def rereference(snippet: datasnippet, targetchans: np.array, refchans: np.array, weights: np.array=np.zeros(0)):
        # targetchans is a list of chan indices we want to keep 
        # refchans is an array of reference channels to be subtracted where each target chan has its own list of refchans
        # weights has same size as refchans and defines the weighting of each reference channel
        res = np.zeros((targetchans.shape[0],snippet.chunk.shape[1]))
        if weights.shape[1]==0:
            weights = np.zeros(refchans.shape) + (1/refchans.shape[1])
            
        for k in range( len(targetchans)):
            res[k,:] = snippet.chunk[targetchans[k],:]
            for k2 in range( refchans.shape[1]):
                res[k,:] -= snippet.chunk[refchans[k,k2],:] * weights[k,k2]
        return res
    
    def fftpowamp(signal:np.array,srate,targetfreqs):
        p = np.zeros(len(targetfreqs))
        if len(targetfreqs)==1:
            fres = 1
        else:
            fres = max(0.05, min(1,min(np.diff(targetfreqs))))
        n = round(srate/fres)
        window = np.hamming(signal.shape[1]) 
        freqs = np.fft.fftfreq(n, 1 / srate) 
        signaltapered = signal*window
        
        fft_values = fft(signaltapered , n)
        power = np.abs(fft_values)**2
    
        for k in range(len(targetfreqs)):
            idx = np.where(np.isclose(freqs, targetfreqs[k], atol=fres/2))[0]
            p[k] = np.log(power[0,idx]) 
        return p
    
    def highpassfilter(signal,cutoff:float,srate:float):
        b, a = scipy.signal.butter(3, cutoff / (0.5 * srate), btype='high')                
        filtered_data = np.zeros(signal.shape)
        for ch in range(signal.shape[0]):
            filtered_data[ch,:] = scipy.signal.filtfilt( b, a, signal[ch,:],padtype='odd')
        return filtered_data
    
    def notchfilter(signal,cutoff:tuple,srate:float):
        b, a = scipy.signal.butter(2, cutoff / (0.5 * srate), btype='bandstop')                
        filtered_data = np.zeros(signal.shape)
        for ch in range(signal.shape[0]):
            filtered_data[ch,:] = scipy.signal.filtfilt( b, a, signal[ch,:],padtype='odd')
        return filtered_data
    def bandpassfilter(signal,cutoff:tuple,srate:float):
        b, a = scipy.signal.butter(2, cutoff / (0.5 * srate), btype='bandpass')                
        filtered_data = np.zeros(signal.shape)
        for ch in range(signal.shape[0]):
            filtered_data[ch,:] = scipy.signal.filtfilt( b, a, signal[ch,:],padtype='odd')
        return filtered_data
    
    def precheck(fbp,snippet:datasnippet,model):
        curdata = process.notchfilter(snippet.chunk, fbp.stopband, snippet.srate)
        curdata = process.bandpassfilter( curdata, np.array([0.5, 30]), snippet.srate)
        stddev = np.std(curdata,axis=1)
        goodchan = np.array(np.where(stddev[fbp.referencechans]<=model['badchanthresh'])[1])
        isArtifact = np.any(np.abs(curdata[fbp.outcomechans,:])>model['artifactthresh'],axis=1)
        isArtifact = isArtifact or max(goodchan.shape)<2
        return isArtifact,goodchan
    
class protocol:
    def __init__(self):
        self.starttime = 0
        self.chanlist = []        
        self.windowwidth = 1.0 # in sec
        self.fbrefresh = 0.5 # in sec
        self.outcomechans = []
        self.referencechans = []
        self.refweights = []        
        self.stopband = ()
        self.highpass = []
        

class frontaltheta(protocol):
    def __init__(self):
        self.starttime = time.time()
        # parameters specific to Brandmeyer et al. 2020
        self.chanlist = ['Fpz','Fz','F7','F8','Cz','P7','P8','Oz']
        self.windowwidth = 1.0 # in sec
        self.fbrefresh = 0.25 # in sec
        self.startcolor = (0,100,0) # color shown when feedback is inactive
        self.artifactcolor = (100,100,100) # color shown when artifact is detected
        self.sendartifactfb = False
        self.detectartifacts = False
        self.outcomechans = np.array([1]) # Fz is second channel
        self.referencechans = np.array([np.setdiff1d( np.arange(len(self.chanlist)), self.outcomechans)])
        self.refweights = np.array(np.zeros(self.referencechans.shape) + (1/self.referencechans.shape[1]))
        self.stopband = np.array([42.5,57.5])
        self.highpass = 0.5
        self.targetfrequencies = [4,5,6]
        # stucture that stores the outcome
        self.outcome = nfdata.fbdata()
        # Parameters for feedback calculation
        self.low_edge = -1 # (we need a trained model to estimate initial values)
        self.high_edge = -1 #  
        self.prev_feedback = 0.5
        self.feedbackvalue = 0.5

    def apply( self, amplitude):
        # Calculate the feedback value based on the algorithm Brandmeyer et al. 2020
        if self.low_edge<0:
            self.low_edge = amplitude*0.95
            self.high_edge = amplitude*1.05
            
        feedback = (amplitude - self.low_edge) / (self.high_edge - self.low_edge)
        # Adjust edges based on the feedback value
        if feedback < 0:
            feedback = 0
            self.low_edge = self.low_edge - (self.high_edge - self.low_edge) / 30
        else:
            self.low_edge = self.low_edge + (self.high_edge - self.low_edge) / 100

        if feedback > 1:
            feedback = 1
            self.high_edge = self.high_edge + (self.high_edge - self.low_edge) / 30
        else:
            self.high_edge = self.high_edge - (self.high_edge - self.low_edge) / 100

        # Cap the feedback change
        if abs(feedback - self.prev_feedback) > 0.05:
            feedback = self.prev_feedback + 0.05 * np.sign(feedback - self.prev_feedback)

        self.prev_feedback = feedback
        return feedback

    def process(self,snippet:datasnippet,model:dict):        
        savePreprocessed = False
        success = 0
        if self.detectartifacts:
            # artifactrejection
            hasArtifact,goodchans = process.precheck(self,snippet,model)
        
            if hasArtifact:
                # print(goodchans)
                success = -1
        else:
            hasArtifact=False
            goodchans=np.arange(self.referencechans.shape[1])
        signal = process.rereference(snippet,self.outcomechans,self.referencechans[:,goodchans],self.refweights[:,goodchans])
        signal =np.array([snippet.chunk[1,:]]) 
        # filter
        signal = process.notchfilter( signal,self.stopband,snippet.srate)
        signal = process.highpassfilter(signal,self.highpass, snippet.srate)
        # frequency decomposition
        amplitudes = process.fftpowamp( signal,snippet.srate, self.targetfrequencies)
        amplitude = np.mean(amplitudes)
        if hasArtifact==False:
            self.feedbackvalue = self.apply(amplitude)
        self.outcome.adddata(snippet.curfbevent,amplitude,self.feedbackvalue, self.low_edge, self.high_edge, time.time()-self.starttime)
        if savePreprocessed:
            self.outcome.addpreprocdata(signal)
        return success
        
    def train( self, eeg:nfdata.rawdata):
        model = {'loweredge':0,'upperedge':0,'artifactthresh':100, 'badchanthresh':100}
        
        data = process.notchfilter(eeg.eegsignals, self.stopband, eeg.srate)
        data = process.bandpassfilter( data, np.array([0.5, 30]),eeg.srate)
        
        # iterate across data
        windowsamp = round(self.windowwidth*eeg.srate)
        onsets = np.arange(0,data.shape[1]-windowsamp,round(0.5*windowsamp))
        stddevs = np.zeros([data.shape[0],len(onsets)])
        for k in range(len(onsets)):
            curdat = data[:,range(onsets[k],onsets[k]+windowsamp)]
            stddevs[:,k] = np.std(curdat, axis=1)
        medianstddevs = np.median(stddevs,axis=1)
        model['badchanthresh'] = np.median(medianstddevs)*4
        model['artifactthresh'] = medianstddevs[self.outcomechans]*4
        # calculate the amplitudes to estimate edges
        amplist = []
        snippet = datasnippet(self,eeg.srate)
        for k in range(len(onsets)):
            snippet.chunk = data[:,range(onsets[k],onsets[k]+windowsamp)]
            snippet.curfbevent = onsets[k]          
            self.process(snippet,model)
        amps = np.array(self.outcome.amplitude )            
        stddev= np.std(amps)
        mean = np.mean(amps)         
        model['loweredge']= np.max((np.min(amps),mean-stddev*0.95))
        model['upperedge'] = np.min((np.max(amps),mean+stddev*0.95))
        return model