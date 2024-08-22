import serial
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import csv
import time as tim
import tkinter as tk
import threading
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Constants
SERIAL_PORT = 'COM10'
BAUD_RATE = 115200

# Initialize serial connection
ser = serial.Serial(SERIAL_PORT, BAUD_RATE)

# Flag to control the data reading loop
running = False

# Initialize subplots for graphing
fig, ax = plt.subplots()

# Initialize lines (empty at the start)
line1, = ax.plot([], [], label='Platform Distances')
line2, = ax.plot([], [], label='Forces')
ax.legend(loc='upper left')
ax.set_title('Pillar Puller Data')

# Initialize empty lists to store data
micros = []
forces = []
platformDistances = []

# Initialize a counter to plot every x data points.
counter = 0

# Create a function to read and process data from Teensy
def process():
    global running, micros, forces, platformDistances, counter  # Declare global variables
    running = True
    timestamp = tim.strftime("%Y%m%d-%H%M%S")
    if filename_entry.get():
        filename = f'{filename_entry.get()}.csv'
    else:
        filename = f'pillar_puller_{timestamp}.csv'
    
    # Disable the start button
    start_button.config(state=tk.DISABLED)
    
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Time', 'Forces', 'Platform Position'])
        
        try:
            while running:
                line = ser.readline().decode('utf-8').strip()  # Decode line from the serial port.
                sensorValues = line.split(',')
                current_time = float(sensorValues[0])
                force = float(sensorValues[1])
                platform_distance = float(sensorValues[2])
                writer.writerow([current_time, force, platform_distance])
                
                # Update the label with the most recent reading
                data_var.set(f'Time: {current_time}, Force: {force}, Platform Position: {platform_distance}')
                
                # Increment the counter
                counter += 1

                # Only append every 2nd value
                if counter % 2 == 0:
                    micros.append(current_time)
                    forces.append(force)
                    platformDistances.append(platform_distance)

                    # Limit the number of displayed points
                    max_points = 100  # Adjust this value based on your needs
                    length = max(min(len(micros), max_points), 1)

                    micros = micros[-length:]
                    forces = forces[-length:]
                    platformDistances = platformDistances[-length:]

                    # Update the data of the lines
                    line1.set_ydata(platformDistances)
                    line2.set_ydata(forces)

                    # Fill plot as data arrives, then start scrolling
                    if length <= max_points:
                        # X values
                        xs = list(range(0, length))
                        if length > 1:
                            ax.set_xlim(0, length - 1)
                        else:
                            ax.set_xlim(-0.5, 0.5)  # Set a small range to avoid singular transformation
                        line1.set_xdata(xs)
                        line2.set_xdata(xs)

                    # Auto scale y axis (only visible plots)
                    ymin = float("inf")
                    ymax = float("-inf")
                    for line in [line1, line2]:
                        a = line.get_alpha()
                        if a is None or a > 0:
                            lmin = np.min(line.get_ydata())
                            lmax = np.max(line.get_ydata())
                            if lmin < ymin:
                                ymin = lmin
                            if lmax > ymax:
                                ymax = lmax

                    yrange = ymax - ymin
                    ax.set_ylim(ymin - 0.1 * yrange, ymax + 0.1 * yrange)

                print(line)
        finally:
            # Re-enable the start button
            start_button.config(state=tk.NORMAL)
            print(f'Data saved to {filename}')

# Function to trigger stop data reading and save data to csv file
def stop():
    global running
    running = False
    # Re-enable the start button
    start_button.config(state=tk.NORMAL)

# Function to handle window close event
def on_closing():
    stop()
    root.destroy()

# -------------------- GUI IMPLEMENTATION -----------------------------------
# Create the main application window
root = tk.Tk()

# Set the title of the main window
root.title("Pillar Puller Control Panel")

# Set the size of the main window (optional)
root.geometry("800x600")

# Add a simple label widget to the main window
label = tk.Label(root, text="Please select a profile")
label.pack(pady=20)  # Use widget's .pack() method to add to the window

# Create a StringVar to hold the data text
data_var = tk.StringVar()
data_var.set("No data yet")

# Add a label to display the most recent reading
data_label = tk.Label(root, textvariable=data_var)
data_label.pack(pady=20)

# Add an entry widget for the filename
filename_entry = tk.Entry(root)
filename_entry.pack(pady=10)

# Add a clickable button to the main window
start_button = tk.Button(
    text="Manual Mode",
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

# Create a canvas to embed the Matplotlib figure
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.draw()
canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

# Bind the window close event to the on_closing function
root.protocol("WM_DELETE_WINDOW", on_closing)

# Function to update the plot
def animate(frame):
    global micros, forces, platformDistances, counter  # Declare global variables

    # Flush the input buffer to clear old data
    ser.reset_input_buffer()

    # Read data from the serial connection
    line = ser.readline().decode('utf-8').strip()  # Decode line from the serial port.
    sensorValues = line.split(',')

    # Parsing and saving lines of data
    current_time = float(sensorValues[0])
    force = float(sensorValues[1])
    platform_distance = float(sensorValues[2])

    # Increment the counter
    counter += 1

     # Only append every 2nd value
    if counter % 2 == 0:
        micros.append(current_time)
        forces.append(force)
        platformDistances.append(platform_distance)

        # Limit the number of displayed points
        max_points = 100  # Adjust this value based on your needs
        length = max(min(len(micros), max_points), 1)

        micros = micros[-length:]
        forces = forces[-length:]
        platformDistances = platformDistances[-length:]

        # Update the data of the lines
        line1.set_ydata(platformDistances)
        line2.set_ydata(forces)

        # Fill plot as data arrives, then start scrolling
        if length <= max_points:
            # X values
            xs = list(range(0, length))
            if length > 1:
                ax.set_xlim(0, length - 1)
            else:
                ax.set_xlim(-0.5, 0.5)  # Set a small range to avoid singular transformation
            line1.set_xdata(xs)
            line2.set_xdata(xs)

        # Auto scale y axis (only visible plots)
        ymin = float("inf")
        ymax = float("-inf")
        for line in [line1, line2]:
            a = line.get_alpha()
            if a is None or a > 0:
                lmin = np.min(line.get_ydata())
                lmax = np.max(line.get_ydata())
                if lmin < ymin:
                    ymin = lmin
                if lmax > ymax:
                    ymax = lmax

        yrange = ymax - ymin
        ax.set_ylim(ymin - 0.1 * yrange, ymax + 0.1 * yrange)

    return line1, line2

# Schedule the plot update to run in the main thread
ani = FuncAnimation(fig, animate, interval=20, blit=False, frames=5000)  # 20ms draw freq

# Run the application's main event loop
root.mainloop()