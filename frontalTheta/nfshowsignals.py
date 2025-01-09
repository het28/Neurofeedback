import numpy as np
import pygame
import nfcomm, nfdata, nfprocess
from pylsl import StreamInlet, resolve_stream, TimeoutError

# Initialize Pygame
pygame.init()

# Create a single window to hold both displays side by side
screen_width, screen_height = 1200, 600
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("EEG Signal Display")

# some parameters
prm = nfdata.params()
prm.srate = 250
scale = 0.2 # we might scale the values differnetly depending on the device

if prm.fbprotocol=="frontaltheta":
    fbp = nfprocess.frontaltheta()

lsl = nfcomm.lslreader(fbp.chanlist)
lsl.connect()

# Main loop with feedback implementation
running = True
clock = pygame.time.Clock()
channel_height = screen_height // len(fbp.chanlist)  # Height per channel
counter = 0
baseline = np.zeros(64)
prevsignal = np.zeros(len(fbp.chanlist))
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False

    # Get EEG data from LSL
    eeg_data = lsl.readdata()
        
    if eeg_data is not None and len(eeg_data)>0:
        eeg_data = eeg_data*scale
        # Clear the old drawings
        if counter + eeg_data.shape[1] > screen_width: # we need two rectangles
            pygame.draw.rect(screen,(0,0,0),pygame.Rect(min(counter,screen_width-1),1,screen_width - counter,screen_height))
            pygame.draw.rect(screen,(0,0,0),pygame.Rect(1,1,(counter+eeg_data.shape[1])%screen_width,screen_height))
        else:
            pygame.draw.rect(screen,(0,0,0),pygame.Rect(counter+1,1,eeg_data.shape[1],screen_height))
        # Display EEG signals        
        for i in np.arange(eeg_data.shape[1]):
            for ch in np.arange(eeg_data.shape[0]):
                signal = eeg_data[ch,i]
                if counter < screen_width:
                    if counter==0:
                        baseline[ch]=(ch * channel_height + channel_height // 2)-int(signal)
                    # Scale the signal for display within the assigned channel area
                    x1 = counter
                    y1 = int(prevsignal[ch] + baseline[ch])
                    x2 = counter +1
                    y2 = int(signal + baseline[ch])
                    pygame.draw.line(screen, (0, 255, 0), (x1, y1), (x2, y2), 1)
            counter = (counter+1) % screen_width
            prevsignal = signal = eeg_data[:,i]
    pygame.display.update()
    clock.tick(4)  # Control the update rate of the signal

pygame.quit()
