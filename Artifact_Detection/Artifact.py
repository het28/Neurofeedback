import os
import mne
import matplotlib.pyplot as plt

# Define the path to your files
vhdr_file = '/Users/Shared/Het/Masters_Magdeburg/Research Student LIN/Work/Artifact Detection/ArtifactData/artifacts_pj63.vhdr'

# Read the raw EEG data using mne
raw = mne.io.read_raw_brainvision(vhdr_file, preload=True)

# Plot the raw data
raw.plot()

# Save the figure
plt.savefig('eeg_plot.png')

# Show the plot
plt.show()
