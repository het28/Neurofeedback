import numpy as np
from scipy.signal import firwin, lfilter
from scipy.signal.windows import hamming
from scipy.fft import fft
import pygame

# Function to generate multi-channel EEG-like signals 
def generate_eeg_signals(mouse_x_position, width):
    # Set up parameters for EEG signal generation
    sampling_rate = 256  # Hz
    duration = 1  # second
    time = np.linspace(0, duration, sampling_rate)
    eeg_frequencies = [1, 4, 8, 12, 20, 30, 40, 60]
    num_channels = 8

    # Map the mouse x-position to a base amplitude range
    amplitude = 0.1 + (mouse_x_position / width) * 0.9

    # Generate each channel with a mix of EEG-like frequency components
    eeg_data = []
    for channel in range(num_channels):
        signal = np.zeros_like(time)
        for freq in eeg_frequencies:
            signal += amplitude * np.sin(2 * np.pi * freq * time + np.random.rand() * 2 * np.pi)
        signal += np.random.normal(0, 0.1, size=time.shape) 
        eeg_data.append(signal)

    return np.array(eeg_data)

def process_eeg_data(eeg_data, sampling_rate=256):
    # High pass filter at 0.5 Hz
    nyquist_rate = sampling_rate / 2.0
    high_pass_cutoff = 0.5 / nyquist_rate
    fir_coeff = firwin(numtaps=101, cutoff=high_pass_cutoff, pass_zero=False)
    
    filtered_data = []
    for channel_data in eeg_data:
        filtered_channel = lfilter(fir_coeff, 1.0, channel_data)
        filtered_data.append(filtered_channel)
    
    filtered_data = np.array(filtered_data)

    # Average reference
    avg_ref_data = filtered_data - np.mean(filtered_data, axis=0)

    return avg_ref_data

def compute_feedback_value(eeg_segment, sampling_rate=256):
    # Calculate the spectral power using FFT
    window = hamming(len(eeg_segment))
    freqs = np.fft.fftfreq(len(eeg_segment), 1/sampling_rate)
    fft_values = fft(eeg_segment * window)
    power = np.abs(fft_values)**2

    # Calculate power at 4, 5, and 6 Hz
    idx_4hz = np.where(np.isclose(freqs, 4, atol=0.5))[0]
    idx_5hz = np.where(np.isclose(freqs, 5, atol=0.5))[0]
    idx_6hz = np.where(np.isclose(freqs, 6, atol=0.5))[0]

    p4 = np.log(np.mean(power[idx_4hz]))
    p5 = np.log(np.mean(power[idx_5hz]))
    p6 = np.log(np.mean(power[idx_6hz]))

    p = np.mean([p4, p5, p6])

    return p

# Initialize Pygame
pygame.init()

# Create a single window to hold both displays side by side
total_width, total_height = 1200, 600
screen = pygame.display.set_mode((total_width, total_height))
pygame.display.set_caption("EEG Signal Display and Feedback")

# Define dimensions for each sub-window
eeg_screen_width = 800
feedback_screen_width = total_width - eeg_screen_width

# Parameters for feedback calculation
low_edge = 0.1
high_edge = 1.0
prev_feedback = 0

# Main loop with feedback implementation
running = True
clock = pygame.time.Clock()

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False

    # Get the mouse x-position (provided by you)
    mouse_x, _ = pygame.mouse.get_pos()

    # Generate EEG signals
    eeg_signals = generate_eeg_signals(mouse_x, eeg_screen_width)

    # Process EEG data
    processed_data = process_eeg_data(eeg_signals)

    # Assume we are working with the Fz channel for feedback
    eeg_segment = processed_data[1]  # Fz channel

    # Compute feedback value
    p = compute_feedback_value(eeg_segment)

    # Calculate the feedback value based on the algorithm
    feedback = (p - low_edge) / (high_edge - low_edge)
    
    # Adjust edges based on the feedback value
    if feedback < 0:
        feedback = 0
        low_edge = low_edge - (high_edge - low_edge) / 30
    else:
        low_edge = low_edge + (high_edge - low_edge) / 100

    if feedback > 1:
        feedback = 1
        high_edge = high_edge + (high_edge - low_edge) / 30
    else:
        high_edge = high_edge - (high_edge - low_edge) / 100

    # Cap the feedback change
    if abs(feedback - prev_feedback) > 0.05:
        feedback = prev_feedback + 0.05 * np.sign(feedback - prev_feedback)

    prev_feedback = feedback

    # Display EEG signals
    eeg_rect = pygame.Rect(0, 0, eeg_screen_width, total_height)
    screen.fill((0, 0, 0), eeg_rect)
    channel_height = total_height // 8  # Height per channel
    for ch in range(8):
        signal = eeg_signals[ch]
        for i in range(len(signal) - 1):
            # Scale the signal for display within the assigned channel area
            x1 = i * (eeg_screen_width / len(signal))
            y1 = (ch * channel_height + channel_height // 2) - int(signal[i] * 50)
            x2 = (i + 1) * (eeg_screen_width / len(signal))
            y2 = (ch * channel_height + channel_height // 2) - int(signal[i + 1] * 50)
            pygame.draw.line(screen, (0, 255, 0), (x1, y1), (x2, y2), 1)
    pygame.display.update(eeg_rect)

    # Display feedback (colored square)
    feedback_rect = pygame.Rect(eeg_screen_width, 0, feedback_screen_width, total_height)
    screen.fill((0, 0, 0), feedback_rect)
    color_intensity = int(feedback * 255)
    pygame.draw.rect(screen, (0, color_intensity, 255 - color_intensity), pygame.Rect(eeg_screen_width + 150, 150, 100, 100))
    pygame.display.update(feedback_rect)

    clock.tick(4)  # Control the update rate of the signal

pygame.quit()
