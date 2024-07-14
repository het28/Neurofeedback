import os
import mne
import matplotlib.pyplot as plt
import numpy as np
from mne.preprocessing import ICA

vhdr_file = '/Users/Shared/Het/Masters_Magdeburg/Research Student LIN/Work/Artifact Detection/ArtifactData/artifacts_pj63.vhdr'
output_fif_file = '/Users/Shared/Het/Masters_Magdeburg/Research Student LIN/Work/Artifact Detection/ArtifactData/artifacts_cleaned.fif'
raw = mne.io.read_raw_brainvision(vhdr_file, preload=True)

channel_types = {'LHEOG': 'eog', 'RHEOG': 'eog', 'LMAST': 'misc', 'VEOG': 'eog', 'IZ': 'eeg'}
raw.set_channel_types(channel_types)

montage = mne.channels.make_standard_montage('standard_1020')
raw.set_montage(montage, on_missing='ignore')
raw.filter(1., 40., fir_design='firwin')
ica = ICA(n_components=20, random_state=97, max_iter='auto')
ica.fit(raw)

ica.plot_components()

raw_clean = raw.copy()
ica.apply(raw_clean)

raw_clean.save(output_fif_file, overwrite=True)

data_clean, times = raw_clean[:]

class ArtifactDetector:
    def __init__(self, times, data_clean, raw_clean):
        self.times = times
        self.data_clean = data_clean
        self.raw_clean = raw_clean
        self.artifact_times = []

        self.fig, self.ax = plt.subplots(figsize=(15, 10))
        for i in range(data_clean.shape[0]):
            self.ax.plot(times, data_clean[i] * 1e6 + i * 100, label=raw_clean.ch_names[i])  # Shift each channel for visibility
        self.ax.set_title('Cleaned EEG Data')
        self.ax.set_xlabel('Time (s)')
        self.ax.set_ylabel('Amplitude (µV)')
        self.ax.legend(loc='upper right')
        self.ax.grid(True)

        self.fig.tight_layout()
        self.cid = self.fig.canvas.mpl_connect('button_press_event', self.onclick)
        plt.show()

    def onclick(self, event):
        self.ax.axvline(x=event.xdata, color='r', linestyle='--')
        self.artifact_times.append(event.xdata)
        self.fig.canvas.draw()

detector = ArtifactDetector(times, data_clean, raw_clean)

plt.savefig('eeg_cleaned_plot_channels_combined.png')

plt.show()

def plot_comparison(raw, raw_clean):
    data_raw, times = raw[:]
    data_clean, _ = raw_clean[:]

    fig, axes = plt.subplots(2, 1, figsize=(15, 10), sharex=True)

    for i in range(data_raw.shape[0]):
        axes[0].plot(times, data_raw[i] * 1e6 + i * 100, label=raw.ch_names[i])
    axes[0].set_title('Raw EEG Data')
    axes[0].set_ylabel('Amplitude (µV)')
    axes[0].legend(loc='upper right')
    axes[0].grid(True)

    for i in range(data_clean.shape[0]):
        axes[1].plot(times, data_clean[i] * 1e6 + i * 100, label=raw_clean.ch_names[i])
    axes[1].set_title('Cleaned EEG Data')
    axes[1].set_xlabel('Time (s)')
    axes[1].set_ylabel('Amplitude (µV)')
    axes[1].legend(loc='upper right')
    axes[1].grid(True)

    fig.tight_layout()
    plt.savefig('eeg_comparison_plot.png')
    plt.show()

plot_comparison(raw, raw_clean)
