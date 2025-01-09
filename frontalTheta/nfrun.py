import nfcomm 
import nfdata
import nfprocess
import scipy.io
import argparse

def main():
    parser = argparse.ArgumentParser(description="Run NeuroFeedback") 
    parser.add_argument('-m', '--mode', type=str, help='Run Mode (calibrate or nf(default))') 
    parser.add_argument('-s', '--subjectcode', type=str, help='Subject Code')
    parser.add_argument('-p', '--pretrainedmodel', type=dict, help='Pretrained Model') 
    parser.add_argument('-f', '--samplingrate', type=int, help='Sampling Frequency')
    parser.add_argument('-d', '--runlength', type=int, help='Duration of a Run')
    args = parser.parse_args() 
    if args.mode: 
        mode = args.mode
    else:
        mode = "nf"
        
    if args.subjectcode: 
        subjcode = args.subjectcode
    else:
        subjcode = "test"
        
    debuglevel = 0

    # some parameters
    prm = nfdata.params()
    modelfilename = prm.datapath + f"{subjcode}_model.mat"
    
    if mode == "nf":
        runlength = prm.nfrunlength
        # load model data
        try:
            model = scipy.io.loadmat(modelfilename)            
        except Exception as e:
            print(f"Error: {e}")
            print(f"Using default model. Please make sure that the model file exists.")
            model = {'artifactthresh':1000,'badchanthresh':1000,'loweredge':-1,'upperedge':-1}        
    else:
        runlength = prm.calibrunlength
    
    if args.samplingrate:
        srate = args.samplingrate
    else:
        srate = prm.srate
    if args.runlength:
        runlength = args.runlength
    
 

    if prm.fbmodule=="blueSquareUDP":
        fbm = nfcomm.udpfeedback()
        fbm.connect()
    # todo: add other modules

    if prm.fbprotocol=="frontaltheta":
        fbp = nfprocess.frontaltheta()
        
    fbm.sendcolor(fbp.startcolor)
    #todo: add other protocols

    if debuglevel==1: print(fbp.chanlist)

    # eeg data structure
    eeg = nfdata.rawdata(len(fbp.chanlist), round( srate*runlength))
    eeg.srate = srate


    lsl = nfcomm.lslreader(fbp.chanlist)
    lsl.connect()   
    
    print('Starting %s run of duration %d ms at %d Hz.' %(mode, runlength, srate))
    print('User ID is %s' %(subjcode))

    if mode == "nf":
        print('model edges are %.1f and %.1f; thresholds are %.1f and %.1f'
              % (model['loweredge'] , model['upperedge'] ,
                 model['artifactthresh'] , model['badchanthresh']))
        
    snippet = nfprocess.datasnippet(fbp,srate)
    print("Reading data ...")
    while eeg.sampcount < eeg.nsamp:
        # grab new data
        chunk = lsl.readdata()
        if len(chunk.shape)==2 and chunk.shape[1]>0:
            eeg.adddata( chunk)
        # check whether we have enaough new data grabbed
        if eeg.sampcount > snippet.nextfbevent:
            if mode=="nf": # we only process the data in nf mode
                snippet.refresh( eeg) # copies data from buffer to snippet            
                success = fbp.process( snippet, model)
                if success <0 and fbp.sendartifactfb:
                    fbm.sendcolor(fbp.artifactcolor)
                else:
                    fbm.sendfeedback( fbp.feedbackvalue)
    if mode[0] == "c": # calibration
        model = fbp.train(eeg)
    else:
        model['loweredge'] = fbp.low_edge
        model['upperedge'] = fbp.high_edge
        
    # hide the square
    fbm.sendcolor((0,0,0))
    # save the model
    scipy.io.savemat(modelfilename,model)
    
    # finalize
    outcome = fbp.outcome       

    # save the data
    data = nfdata.io.preparedata4mat(eeg,outcome)
    filename = nfdata.io.generatefilename(prm,subjcode)
    scipy.io.savemat(filename, data)
                    
    if debuglevel==1:
        print(eeg.sampcount)
        print(eeg.nsamp)
        print(outcome.position)
        print(outcome.amplitude)
        print(outcome.feedbackvalue)
        
    print("Run finished.")
    
if __name__ == "__main__": 
    main()