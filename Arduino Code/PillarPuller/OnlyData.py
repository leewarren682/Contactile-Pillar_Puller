import serial
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import csv
import time as tim

# Constants
SERIAL_PORT = 'COM10'
BAUD_RATE = 115200

# Initialize serial connection
ser = serial.Serial(SERIAL_PORT, BAUD_RATE)

# Initialise empty lists to store data
micros = []
forces = []
platformDistances = []

# Create a function to read and process data from Teensy
def process():
    global micros, forces, platformDistances  # Declare global variables


    line = ser.readline().decode('utf-8').strip() # Decode line from the serial port.
    sensorValues = line.split(',')

    # Parsing and saving lines of data
    current_time = float(sensorValues[0])
    micros.append(float(sensorValues[0]))
    forces.append(float(sensorValues[1]))
    platformDistances.append(float(sensorValues[2]))

    print({line})

# Function to save data to csv file when plot is closed
def save_data():
    # Generate a unique filename using a timestamp
    timestamp  = tim.strftime("%Y%m%d-%H%M%S")
    filename = f'pillar_puller_{timestamp}.csv'

    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Time', 'Forces', 'Platform Position'])
        for time, force, pos in zip(micros, forces, platformDistances):
            writer.writerow([time, force, pos])
    
    return filename

try:
    while(True):
        process()
except KeyboardInterrupt:
    filename = save_data()
    print(f"Data save to {filename}")


# Function to plot the most recent data file and display it.
# Give information about where the breaking point was.