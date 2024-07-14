function generateThetaSignal()

srate = 500;
nchan = 8;

%% instantiate the library
if ~exist('lib','var'),
    disp('Loading library...');
    lib = lsl_loadlib();
    
    % make a new stream outlet
    disp('Creating a new streaminfo...');
    info = lsl_streaminfo(lib,'BioSemi','EEG',nchan,srate,'cf_float32','sdfwerr32432');
    
    disp('Opening an outlet...');
    outlet = lsl_outlet(info);
end
% send data into the outlet, sample by sample
disp('Now transmitting data...');
screensize = get(0,'screensize');
posRight = [screensize(3), screensize(4)];

f1 = [2.5; 5.0; 8.5];
f2 = [4.25; 5.25; 6.0];
f3 = [4.75; 5.75; 6.25];
ch1 = [2,1,3];
ch2 = [4,5,6];
ch3 = [6, 7, 8];

blocksize = 16;
startTime = GetSecs();
lastUpdate = floor(GetSecs()-startTime);
nsamp= 0;
isRunning = true;

while isRunning
    timeStamp = GetSecs();
    if  timeStamp > startTime+(nsamp+blocksize)/srate
        
        t1 = (nsamp+1)/srate;
        t2 = (nsamp+blocksize)/srate;
        t = linspace(t1,t2,blocksize);
        pnt = get(0,'PointerLocation');
        amp1 = max(0,(pnt(1))/posRight(1));
        amp2 = max(0,(pnt(2))/posRight(2));
        amp3 = sqrt(sum(pnt(1:2).^2))./sqrt(sum(posRight(1:2).^2));
        dat = 50*randn(nchan,blocksize)+50;
        
        sig1 = sin(f1*t*2*pi)*amp1*50;
        sig2 = sin(f2*t*2*pi)*amp2*50;
        sig3 = sin(f3*t*2*pi)*amp3*50;
        dat(ch1,:) = (dat(ch1,:) + sig1);
        dat(ch2,:) = (dat(ch2,:) + sig2);
        dat(ch3,:) = (dat(ch3,:) + sig3);
        outlet.push_chunk(dat);
        nsamp = nsamp + blocksize;
        if floor(timeStamp-startTime)>=lastUpdate+10
            lastUpdate = floor(timeStamp -startTime);
            fprintf('%i sec of data sent.\n',floor(timeStamp-startTime));
        end
%     outlet.push_sample(randn(8,1));
    else
        pause((startTime+(nsamp+blocksize)/srate)-timeStamp);
        [keyIsDown, keyCode]=GetAsyncKeyState();
        if keyIsDown && keyCode(27)>0
            isRunning = false;
        end
    end
end