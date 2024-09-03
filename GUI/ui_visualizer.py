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

# Function to extract theta activity (4-8 Hz) from EEG data
def extract_theta_activity(data, sfreq):
    theta_band = (4, 8)
    filtered_data = mne.filter.filter_data(data, sfreq, theta_band[0], theta_band[1])
    theta_power = np.mean(np.abs(filtered_data) ** 2, axis=0)
    return theta_power

# Define the path to your files
vhdr_file = '/Users/Shared/Het/Masters_Magdeburg/Research Student LIN/Work/Artifact Detection/ArtifactData/artifacts_pj63.vhdr'
try:
    raw, data, times = load_eeg_data(vhdr_file)
except Exception as e:
    print(e)
    sys.exit(1)

# Apply a bandpass filter to the data
raw.filter(1.0, 40.0)
sfreq = raw.info['sfreq']

# Define a dictionary mapping artifact ranges
trigger_ranges = {
    1: (0.0005, 0.0006),  # rest with eyes open
    2: (0.0006, 0.0008),  # rest with eyes closed
    3: (0.0008, 0.0012),  # blink once per second
    4: (0.0012, 0.0016),  # blink fast
    5: (0.0016, 0.0018),  # move eyes left and right, once per second
    6: (0.0018, 0.0020),  # move eyes up and down, once per second
    7: (0.0020, 0.0022),  # clench teeth
    8: (0.0022, 0.0024),  # move head in a 1sec pace
    9: (0.0024, 0.0026),  # speak
    10: (0.0026, 0.0028)  # make a non-relaxed face
}

# Set the threshold for circle size scaling
threshold = 0.0005

# Initialize variables
ptr = 0
paused = False

# Function to detect artifacts based on ranges and update circle size
def detect_artifact_and_update(segment):
    global trigger_ranges, feedback_canvas, feedback_circle

    max_amplitude = np.max(np.abs(segment))
    detected_artifact = None

    for artifact, (low, high) in trigger_ranges.items():
        if low <= max_amplitude < high:
            detected_artifact = artifact
            break

    # Resize circle based on the maximum amplitude and threshold
    scale_factor = max_amplitude / threshold
    circle_size = max(50, min(200, 150 * scale_factor))
    
    if detected_artifact:
        feedback_canvas.coords(feedback_circle, 150 - circle_size/2, 150 - circle_size/2, 150 + circle_size/2, 150 + circle_size/2)
        feedback_canvas.itemconfig(feedback_circle, fill='red')
    else:
        feedback_canvas.coords(feedback_circle, 150 - circle_size/2, 150 - circle_size/2, 150 + circle_size/2, 150 + circle_size/2)
        feedback_canvas.itemconfig(feedback_circle, fill='green')

    return detected_artifact

# Function to update the plot and feedback circle
def update_plot(frame):
    global ptr, data, times, raw, paused, sfreq

    if paused:
        return

    step = int(raw.info['sfreq'] * 1.5)
    start_idx = ptr
    end_idx = min(ptr + step, data.shape[1])

    if start_idx < end_idx:
        segment = data[:, start_idx:end_idx]
        time_segment = times[start_idx:end_idx] - times[0]

        # Detect artifact and update feedback
        detected_artifact = detect_artifact_and_update(segment)

        # Log the detected artifact
        if detected_artifact:
            feedback_log.insert(tk.END, f"Artifact {detected_artifact} detected at {time_segment[0]:.2f} s\n")
            feedback_log.see(tk.END)  # Scroll to the latest log

        # Update the theta window
        theta_activity = extract_theta_activity(segment, sfreq)
        max_theta = np.max(theta_activity)
        scaled_theta = max(0, min(1, max_theta / np.max(theta_activity)))

        update_theta_window(scaled_theta, 'red' if detected_artifact else 'green', max_theta, theta_activity)

        ax.clear()
        for i in range(data.shape[0]):
            ax.plot(time_segment, segment[i], label=f'Ch {i+1}')

        mid_time = time_segment[len(time_segment) // 2]
        circle_radius_x = 0.05 * (data.max() - data.min())
        circle_radius_y = 0.1 * (data.max() - data.min())
        ax.add_patch(plt.Circle((mid_time, 0), circle_radius_x, color='green', alpha=0.5))

        ax.set_title('EEG Real-time Visualizer')
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Amplitude (µV)')
        ax.set_xlim(mid_time - 0.5, mid_time + 0.5)
        ax.set_ylim(data.min(), data.max())

        ptr = end_idx
    else:
        print("End of data reached. Stopping visualization.")
        ani.event_source.stop()

# Function to handle mouse click (for pausing)
def on_click(event):
    global paused
    paused = not paused
    if not paused:
        ani.event_source.start()

# Function to update the theta window with a circle based on the scaled theta value, log raw theta values
def update_theta_window(scaled_theta, circle_color, max_theta, theta_activity):
    global theta_canvas, theta_circle, theta_log

    # Calculate the new circle size based on the scaled theta value
    circle_radius = 50 + 150 * scaled_theta  # Size between 50 and 200

    # Update the circle's size
    theta_canvas.coords(theta_circle, 150 - circle_radius/2, 150 - circle_radius/2, 150 + circle_radius/2, 150 + circle_radius/2)
    theta_canvas.itemconfig(theta_circle, fill=circle_color)

    # Log the raw and normalized theta activity
    theta_log.delete(1.0, tk.END)  # Clear previous log
    theta_log.insert(tk.END, f"Max Theta (raw): {max_theta:.2f}\n")
    theta_log.insert(tk.END, f"Normalized Theta: {scaled_theta:.2f}\n")
    theta_log.see(tk.END)  # Scroll to the latest log

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

# Setup for the theta window
theta_window = tk.Toplevel(root)
theta_window.title("Theta Activity")
theta_canvas = tk.Canvas(theta_window, width=300, height=300, bg='grey')
theta_canvas.pack()

# Create the initial theta circle
theta_circle = theta_canvas.create_oval(100, 100, 200, 200, outline="black", fill="green")

# Set up a text widget for theta activity logging
theta_log = tk.Text(theta_window, width=30, height=10)
theta_log.pack()

# Create the plot window
fig, ax = plt.subplots()
fig.canvas.mpl_connect('button_press_event', on_click)
ani = FuncAnimation(fig, update_plot, interval=1000)

plt.show()
root.mainloop()