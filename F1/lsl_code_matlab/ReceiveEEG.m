%% instantiate the library
disp('Loading the library...');
lib = lsl_loadlib();

% resolve a stream...
disp('Resolving an EEG stream...');
chan2Disp = 1;
result = {};
while isempty(result)
%     result = lsl_resolve_byprop(lib,'type','EEG'); 
    result = lsl_resolve_byprop(lib,'name','F1-Stream'); 
end

% create a new inlet
disp('Opening an inlet...');
inlet = lsl_inlet(result{1});
info = inlet.info();
% get meta data
% sr = info.desc().child('acquisition').child('settings');
hdr.srate = 500;% hdr.srate = str2double( sr.child_value('srate'));
% 
% ch = info.desc().child('channels').child('channel');
hdr.label = cell(4);% hdr.label = cell(info.channel_count(),1);

% for k = 1:info.channel_count()
%     obj.hdr.label{k} = ch.child_value('label');
%     ch = ch.next_sibling();
% end

disp('Now receiving data...');

fH = figure;
bufsiz = 2500; % 5sec @500Hz
rawbuf = zeros(length(hdr.label),bufsiz);
buf = zeros(length(hdr.label),500); % 5sec @100Hz
time = linspace(0,5,500); % 5sec @100Hz
pH = plot(time,buf(chan2Disp,:));
pnt=0;
lastT=inf;
cnt=0;
[b,a]= butter(3,[1.0,20]./(hdr.srate/10),'bandpass');
while true
    % get data from the inlet
    %[vec,ts] = inlet.pull_sample();
    [data,timestamps] = inlet.pull_chunk();
    if ~isempty( timestamps)
        cnt = cnt + size(data,2);
        bs = min(size(data,2), bufsiz);
        idx1 = mod(cnt-bs+1:cnt,bufsiz)+1;
        rawbuf(:,idx1)=data(:, end-bs+1:end);
        idx2 = mod(cnt+1:cnt+size(rawbuf,2),size(rawbuf,2))+1;
        idx3 = mod(round(cnt/5)+1:round(cnt/5)+size(buf,2),size(buf,2))+1;
        buf(:,idx3) = downsample( rawbuf(:,idx2)',5)';
%         pH.YData = filter(b,a,detrend(buf(chan2Disp, idx3),0)); 
         pH.YData = detrend(buf(chan2Disp, idx3),0); 
    end
    pause(0.01);
    drawnow;
%     % and display it
%     fprintf('%.2f\t',vec);
%     fprintf('%.5f\n',ts);
end