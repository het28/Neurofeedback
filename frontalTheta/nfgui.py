import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
import os

class NeurofeedbackGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Neurofeedback Control Panel")
        self.root.geometry("400x300")
        
        # Create data directory if it doesn't exist
        self.data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            print(f"Created data directory at: {self.data_dir}")
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="Neurofeedback Control Panel", font=('Helvetica', 14, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=10)
        
        # Visualization Section
        viz_frame = ttk.LabelFrame(main_frame, text="Visualization", padding="5")
        viz_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Button(viz_frame, text="Show EEG Signals", command=self.start_signal_display).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(viz_frame, text="Show Feedback Square", command=self.start_square_display).grid(row=0, column=1, padx=5, pady=5)
        
        # Protocol Section
        protocol_frame = ttk.LabelFrame(main_frame, text="Protocol Control", padding="5")
        protocol_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Button(protocol_frame, text="Start Training", command=self.start_training).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(protocol_frame, text="Start Neurofeedback", command=self.start_neurofeedback).grid(row=0, column=1, padx=5, pady=5)
        
        # Subject Code Entry
        subj_frame = ttk.Frame(main_frame)
        subj_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        ttk.Label(subj_frame, text="Subject Code:").grid(row=0, column=0, padx=5)
        self.subject_code = ttk.Entry(subj_frame, width=15)
        self.subject_code.grid(row=0, column=1, padx=5)
        self.subject_code.insert(0, "test")
        
        # Status Bar
        self.status_var = tk.StringVar()
        self.status_var.set(f"Ready - Data directory: {self.data_dir}")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)

    def start_signal_display(self):
        try:
            subprocess.Popen([sys.executable, "generateThetaSignal.py"])  # Start signal generator first
            subprocess.Popen([sys.executable, "nfshowsignals.py"])
            self.status_var.set("Signal display and generator started")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start signal display: {str(e)}")

    def start_square_display(self):
        try:
            subprocess.Popen([sys.executable, "nfshowsquare.py"])
            self.status_var.set("Square display started")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start square display: {str(e)}")

    def start_training(self):
        subject = self.subject_code.get()
        if not subject:
            messagebox.showwarning("Warning", "Please enter a subject code")
            return
        try:
            subprocess.Popen([sys.executable, "nfrun.py", "-m", "calib", "-s", subject])
            self.status_var.set(f"Training started for subject {subject}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start training: {str(e)}")

    def start_neurofeedback(self):
        subject = self.subject_code.get()
        if not subject:
            messagebox.showwarning("Warning", "Please enter a subject code")
            return
        try:
            subprocess.Popen([sys.executable, "nfrun.py", "-m", "nf", "-s", subject])
            self.status_var.set(f"Neurofeedback started for subject {subject}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start neurofeedback: {str(e)}")

def main():
    root = tk.Tk()
    app = NeurofeedbackGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()