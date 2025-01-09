import sys
import pyautogui
import keyboard
import time
import math
import numpy
from random import random as rand

from pylsl import StreamInfo, StreamOutlet, local_clock

def main(argv):
    srate = 250
    nchan = 8

    # make a new stream outlet
    print("Creating a new streaminfo...")
    info = StreamInfo("BioSemi", "EEG", nchan, srate, "float32", "myuid34234")
    print("Opening an outlet...")
        # next make an outlet
    outlet = StreamOutlet(info)
    print("Now transmitting data...")

    width, height = pyautogui.size()

    f1 = 6.0
    f2 = 5.0
    f3 = 4.0

    ch1 = 1
    ch2 = 2
    ch3 = 6

    blocksize = 32
    startTime = local_clock()
    lastUpdate = math.floor(local_clock()-startTime)
    nsamp= 0
    isRunning = True    
    
    sent_samples = 0
    

    while isRunning:
        timeStamp = local_clock()
        if  timeStamp > startTime+(nsamp+blocksize)/srate:        
            t1 = (nsamp+1)/srate
            t2 = (nsamp+blocksize)/srate
            timevec = numpy.linspace(t1,t2,blocksize)
            #print(timevec)
            x, y = pyautogui.position()
            amp1 = max(0,x/width)
            amp2 = max(0,y/height)
            amp3 = math.sqrt(x**2+y**2)/math.sqrt(width**2+height**2)
            for i in range(len(timevec)):
                dat = 50*numpy.random.normal(0, 0.1, size=[nchan,1])+50
                linenoise = numpy.sin(50*timevec[i]*2*numpy.pi) * 10
                dat = dat + numpy.tile(linenoise,(nchan,1))
                #dat = numpy.zeros(dat.shape) # remove the noise for degugging
                sig1 = numpy.sin(f1*timevec[i]*2*numpy.pi)*amp1*50
                sig2 = numpy.sin(f2*timevec[i]*2*numpy.pi)*amp2*50
                sig3 = numpy.sin(f3*timevec[i]*2*numpy.pi)*amp3*25
                
                dat[ch1-1] += sig1 
                dat[ch2-1] += sig2 
                dat[ch3-1] += sig3
                #dat[-1]=i # check integrity for degubbing
                outlet.push_sample(dat)
            nsamp += blocksize
            if math.floor(timeStamp-startTime)>=lastUpdate+10:
                lastUpdate = math.floor(timeStamp -startTime)
                print("%3d sec of data sent."%(math.floor(timeStamp-startTime)))
        else:
            time.sleep((startTime+(nsamp+blocksize)/srate)-timeStamp)
            if keyboard.is_pressed(chr(27)): 
                isRunning = False
if __name__ == "__main__":
    main(sys.argv[1:])