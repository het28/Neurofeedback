import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import paho.mqtt.client as mqtt
import json
import queue
import time
from scipy.signal import butter, lfilter

# MQTT broker address
broker_address = "172.31.1.1"
topic_info = "state/device/info"
topic_samples = "data/samples"
topic_action_start = "action/sampling/start"
topic_action_stop = "action/sampling/stop"

# Global variables
scale_to_uV = None
data_queue = queue.Queue()
raw_data_queue = queue.Queue()  # Queue to store raw data
window_size = 1000  # Adjust window size to show data over a period of time
colors = ['b', 'r']  # Colors for raw and filtered HR channel
fs = 500.0  # Sampling frequency (Hz)

# Butterworth bandpass filter parameters
lowcut = 0.5  # Low cutoff frequency (Hz)
highcut = 5.0  # High cutoff frequency (Hz)
order = 6  # Filter order

# Butterworth bandpass filter
def butter_bandpass(lowcut, highcut, fs, order=6):
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(order, [low, high], btype='band')
    return b, a

def bandpass_filter(data, lowcut, highcut, fs, order=6):
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    y = lfilter(b, a, data, axis=1)
    return y

# Function to handle MQTT connection
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker.")
        client.subscribe(topic_info)
        client.subscribe(topic_samples)
        start_sampling(client)
    else:
        print("Failed to connect, return code %d\n", rc)

def on_message(client, userdata, message):
    if message.topic == topic_info:
        handle_info_message(message.payload)
    elif message.topic == topic_samples:
        handle_samples_message(message.payload)

def start_sampling(client):
    sampling_params = {
        "channel_label": ["HR"],
        "data_format": 0.0,
        "gain": 12.0,
        "impedance_interval": 0.0,
        "layout": 1.0,
        "marker_id": "",
        "output_rate": 20.0,
        "radio_bandw": 13.0,
        "radio_chan": 1.0,
        "reference": ["Fpz"],
        "sampling_rate": 500.0
    }
    client.publish(topic_action_start, json.dumps(sampling_params))

def stop_sampling(client):
    client.publish(topic_action_stop)
    time.sleep(1)
    client.disconnect()

def handle_info_message(payload):
    global scale_to_uV
    info_data = json.loads(payload)
    scale_to_uV = info_data["scale_to_uV"]
    print("Scale to uV:", scale_to_uV)

def handle_samples_message(payload):
    global scale_to_uV
    if scale_to_uV is not None:
        samples_data = np.frombuffer(payload, dtype=np.uint32)
        start_sample = samples_data[0]
        end_sample = samples_data[1]
        num_samples = end_sample - start_sample
        num_channels = (len(samples_data) - 2) // num_samples
        eeg_signal = samples_data[2:].reshape((num_channels, num_samples))
        eeg_signal_uV = eeg_signal * scale_to_uV

        # Add raw data to raw data queue
        raw_data_queue.put(eeg_signal_uV[0])

        # Apply Butterworth bandpass filter
        eeg_signal_uV_filtered = bandpass_filter(eeg_signal_uV[:1, :], lowcut, highcut, fs)

        # Add filtered data to queue
        data_queue.put(eeg_signal_uV_filtered[0])
    else:
        print("Error: scale_to_uV is not defined.")

def update_plot(frame):
    try:
        while not raw_data_queue.empty() and not data_queue.empty():
            raw_signal_uV = raw_data_queue.get_nowait()
            filtered_signal_uV = data_queue.get_nowait()

            # Shift the current data to the left and add new data to the end
            raw_data[:, :-len(raw_signal_uV)] = raw_data[:, len(raw_signal_uV):]
            raw_data[:, -len(raw_signal_uV):] = raw_signal_uV

            filtered_data[:, :-len(filtered_signal_uV)] = filtered_data[:, len(filtered_signal_uV):]
            filtered_data[:, -len(filtered_signal_uV):] = filtered_signal_uV

            for i, line in enumerate(raw_lines):
                line.set_ydata(raw_data[i])

            for i, line in enumerate(filtered_lines):
                line.set_ydata(filtered_data[i])

            ax.set_xlim(t[0], t[-1])
            ax.set_ylim(np.min(raw_data) - 50, np.max(raw_data) + 50)  # Dynamically adjust y-axis
            ax2.set_xlim(t[0], t[-1])
            ax2.set_ylim(np.min(filtered_data) - 50, np.max(filtered_data) + 50)  # Dynamically adjust y-axis
    except queue.Empty:
        pass
    return raw_lines + filtered_lines

# Set up MQTT client
client = mqtt.Client(client_id="Client2")
client.on_connect = on_connect
client.on_message = on_message
client.connect(broker_address)
client.loop_start()

# Set up the plot
fig, (ax, ax2) = plt.subplots(2, 1, figsize=(12, 12))
t = np.arange(0, window_size) * (1 / fs)
raw_data = np.zeros((1, window_size))
filtered_data = np.zeros((1, window_size))
raw_lines = [ax.plot(t, np.zeros(window_size), color=colors[0])[0]]
filtered_lines = [ax2.plot(t, np.zeros(window_size), color=colors[1])[0]]

# Initial y-axis limits
ax.set_ylim(-100, 100)
ax.set_title("Raw Heart Rate Signal (HR)")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Amplitude (uV)")

ax2.set_ylim(-100, 100)
ax2.set_title("Filtered Heart Rate Signal (HR)")
ax2.set_xlabel("Time (s)")
ax2.set_ylabel("Amplitude (uV)")

ani = animation.FuncAnimation(fig, update_plot, blit=True, interval=50)

# Show the plot
plt.show()

# Clean up on exit
client.loop_stop()
stop_sampling(client)
