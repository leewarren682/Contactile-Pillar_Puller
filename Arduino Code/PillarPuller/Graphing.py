import serial
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np

# Constants
SERIAL_PORT = 'COM10'
BAUD_RATE = 115200
TIME_RANGE = 1000000 # 1 seconds in micro seconds

# Initialize serial connection
ser = serial.Serial(SERIAL_PORT, BAUD_RATE)

# Initialise subplots
fig, ax = plt.subplots()

# Initialize lines (empty at the start)
line1, = ax.plot([], [], label='Platform Distances')
line2, = ax.plot([], [], label='Forces')
ax.legend(loc='upper left')
ax.set_title('Pillar Puller Data')

# Initialise empty lists to store data
micros = []
forces = []
platformDistances = []

# Initialize a counter to plot every x data points.
counter = 0

# Create a function to read and process data from Teensy
def animate(frame):
    global micros, forces, platformDistances, counter  # Declare global variables

    # Read data from the serial connection
    line = ser.readline().decode('utf-8').strip()  # Decode line from the serial port.
    sensorValues = line.split(',')

    # Parsing and saving lines of data
    current_time = float(sensorValues[0])
    force = float(sensorValues[1])
    platform_distance = float(sensorValues[2])

    # Increment the counter
    counter += 1

     # Only append every 5th value
    if counter % 5 == 0:
        micros.append(current_time)
        forces.append(force)
        platformDistances.append(platform_distance)

        # Limit the number of displayed points
        max_points = 10  # Adjust this value based on your needs
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

ani = FuncAnimation(fig, animate, interval=20, blit=False, frames = 5000)  # 20ms draw freq
plt.show()