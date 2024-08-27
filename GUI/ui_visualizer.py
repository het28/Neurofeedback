import sys
import numpy as np
import mne
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import os
import tkinter as tk
import matplotlib
matplotlib.use('TkAgg')

# Function to load EEG data from a .vhdr file
def load_eeg_data(vhdr_file):
    if not os.path.exists(vhdr_file):
        raise FileNotFoundError(f"Error: File {vhdr_file} not found.")
    
    try:
        raw = mne.io.read_raw_brainvision(vhdr_file, preload=True)
        data, times = raw.get_data(return_times=True)
        return raw, data, times
    except Exception as e:
        raise RuntimeError(f"Error loading EEG data: {e}")

# Define the path to your files
vhdr_file = '/Users/Shared/Het/Masters_Magdeburg/Research Student LIN/Work/Artifact Detection/ArtifactData/artifacts_pj63.vhdr'
try:
    raw, data, times = load_eeg_data(vhdr_file)
except Exception as e:
    print(e)
    sys.exit(1)

# Apply a bandpass filter to the data
raw.filter(1.0, 40.0)

# Define a dictionary mapping trigger values to thresholds
trigger_thresholds = {
    1: 0.0007,  # rest with eyes open
    2: 0.0008,  # rest with eyes closed
    3: 0.0009,  # blink once per second
    4: 0.0010,  # blink fast
    5: 0.0011,  # move eyes left and right, once per second
    6: 0.0012,  # move eyes up and down, once per second
    7: 0.0013,  # clench teeth
    8: 0.0014,  # move head in a 1sec pace
    9: 0.0015,  # speak
    10: 0.0016  # make a non-relaxed face
}

# Initialize variables
ptr = 0
paused = False

# Function to calculate baseline threshold
def calculate_baseline_threshold(data, window_size):
    thresholds = []
    for channel in data:
        baseline = np.mean(channel[:window_size])
        std = np.std(channel[:window_size])
        threshold = baseline + 2 * std
        thresholds.append(threshold)
    return np.array(thresholds)

# Function to update the plot and feedback circle
def update_plot(frame):
    global ptr, data, times, raw, trigger_thresholds, paused

    if paused:
        return

    step = int(raw.info['sfreq'] * 1.5)
    start_idx = ptr
    end_idx = min(ptr + step, data.shape[1])

    if start_idx < end_idx:
        segment = data[:, start_idx:end_idx]
        time_segment = times[start_idx:end_idx] - times[0]

        events, _ = mne.events_from_annotations(raw)
        current_trigger = None
        for event_time, _, trigger in events:
            if start_idx <= event_time < end_idx:
                current_trigger = trigger
                break

        if current_trigger in trigger_thresholds:
            threshold = trigger_thresholds[current_trigger]
        else:
            threshold = 0.0007

        artifact_detected = np.any(np.abs(segment) > threshold)
        circle_color = 'red' if artifact_detected else 'green'

        # Update the feedback window and log artifacts
        update_feedback_window(segment, circle_color, time_segment, artifact_detected)

        ax.clear()
        for i in range(data.shape[0]):
            ax.plot(time_segment, segment[i], label=f'Ch {i+1}')

        mid_time = time_segment[len(time_segment) // 2]
        circle_radius_x = 0.05 * (data.max() - data.min())
        circle_radius_y = 0.1 * (data.max() - data.min())
        ax.add_patch(plt.Circle((mid_time, 0), circle_radius_x, color=circle_color, alpha=0.5))

        ax.set_title('EEG Real-time Visualizer')
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Amplitude (µV)')
        ax.set_xlim(mid_time - 0.5, mid_time + 0.5)
        ax.set_ylim(data.min(), data.max())

        ptr = end_idx
    else:
        print("End of data reached. Stopping visualization.")
        ani.event_source.stop()

# Function to handle mouse click
def on_click(event):
    global paused
    paused = not paused
    if not paused:
        ani.event_source.start()

# Function to update the feedback window and log artifacts
def update_feedback_window(segment, circle_color, time_segment, artifact_detected):
    global feedback_canvas, feedback_circle, feedback_log

    # Normalize the segment for display
    signal = segment[0]  # Assuming we display the first channel
    normalized_segment = (signal - np.min(signal)) / (np.max(signal) - np.min(signal))
    normalized_segment = (normalized_segment * 100)  # Scale to fit inside the circle

    feedback_canvas.delete("waveform")  # Clear previous waveforms

    # Draw the waveform inside the circle
    for i in range(len(normalized_segment) - 1):
        x1 = 150 + (i - len(normalized_segment) // 2)
        y1 = 150 - normalized_segment[i]  # Invert y-axis to fit the circle
        x2 = 150 + (i + 1 - len(normalized_segment) // 2)
        y2 = 150 - normalized_segment[i + 1]
        feedback_canvas.create_line(x1, y1, x2, y2, fill="blue", tags="waveform")

    # Update circle color based on artifact detection
    feedback_canvas.itemconfig(feedback_circle, fill=circle_color)

    # Log the artifact in the feedback log
    if artifact_detected:
        feedback_log.insert(tk.END, f"Artifact detected at {time_segment[0]:.2f} s\n")
        feedback_log.see(tk.END)  # Scroll to the latest log

# Setup for the feedback window
root = tk.Tk()

# Set up feedback canvas for EEG visualization
feedback_canvas = tk.Canvas(root, width=300, height=300)
feedback_canvas.pack(side=tk.LEFT)

# Create the initial circle
feedback_circle = feedback_canvas.create_oval(100, 100, 200, 200, outline="black", fill="green")

# Set up a text widget for artifact logging
feedback_log = tk.Text(root, width=30, height=20)
feedback_log.pack(side=tk.RIGHT)

# Create the plot window
fig, ax = plt.subplots()
fig.canvas.mpl_connect('button_press_event', on_click)
ani = FuncAnimation(fig, update_plot, interval=1000)

plt.show()
root.mainloop()
