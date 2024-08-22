import serial
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import csv
import time as tim
import tkinter as tk
import threading

# Constants
SERIAL_PORT = 'COM10'
BAUD_RATE = 115200

# Initialize serial connection
ser = serial.Serial(SERIAL_PORT, BAUD_RATE)

# Flag to control the data reading loop
running = False

# Create a function to read and process data from Teensy
def process():
    global running
    running = True
    timestamp = tim.strftime("%Y%m%d-%H%M%S")
    if filename_entry.get():
        filename = f'{filename_entry.get()}.csv'
    else:
        filename = f'pillar_puller_{timestamp}.csv'
    
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Time', 'Forces', 'Platform Position'])
        
        while running:
            line = ser.readline().decode('utf-8').strip()  # Decode line from the serial port.
            sensorValues = line.split(',')
            current_time = float(sensorValues[0])
            force = float(sensorValues[1])
            platform_distance = float(sensorValues[2])
            writer.writerow([current_time, force, platform_distance])

            # Update the label with the most recent reading
            data_var.set(f'Time: {current_time}, Force: {force}, Platform Position: {platform_distance}')

            print(line)
        
        print(f'Data saved to {filename}')

# Function to trigger stop data reading and save data to csv file
def stop():
    global running
    running = False

# -------------------- GUI IMPLEMENTATION -----------------------------------
# Create the main application window
root = tk.Tk()

# Set the title of the main window
root.title("Pillar Puller Control Panel")

# Set the size of the main window (optional)
root.geometry("400x300")

# Add a simple label widget to the main window
label = tk.Label(root, text="Please select a profile")
label.pack(pady=20)  # Use widget's .pack() method to add to the window

# Create a StringVar to hold the data text
data_var = tk.StringVar()
data_var.set("No data yet")

# Add a label to display the most recent reading
data_label = tk.Label(root, textvariable=data_var)
data_label.pack(pady=20)

# Add a clickable button to the main window
start_button = tk.Button(
    text="profile1",
    width=25,
    height=5,
    bg="purple",
    fg="white",
    command=lambda: threading.Thread(target=process).start()
)

start_button.pack()

# Add a stop button to the main window
stop_button = tk.Button(
    text="Stop",
    width=25,
    height=5,
    bg="red",
    fg="white",
    command=stop
)

stop_button.pack()

# Add a text input box which allows us to give a filename, otherwise use the default filename.
filename_entry = tk.Entry(root)
filename_entry.pack()

# Run the application's main event loop
root.mainloop()