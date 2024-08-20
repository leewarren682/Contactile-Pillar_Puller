import serial
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import csv
import time as tim

# Constants
SERIAL_PORT = 'COM10'
BAUD_RATE = 115200
TIME_RANGE = 2000000 # 2 seconds in micro seconds

# Initialize serial connection
ser = serial.Serial(SERIAL_PORT, BAUD_RATE)

# Initialise empty lists to store data
micros = []
forces = []
platformDistances = []
graph_micros = []
graph_forces = []
graph_platformDistances = []

# Create a function to read and process data from Teensy
def process():
    line = ser.readline().decode('utf-8').strip()
    sensorValues = line.split(',')
    micros.append(float(sensorValues[0]))
    forces.append(float(sensorValues[1]))
    platformDistances.append(float(sensorValues[2]))

    graph_micros.append(float(sensorValues[0]))
    graph_forces.append(float(sensorValues[1]))
    graph_platformDistances.append(float(sensorValues[2]))

    if (graph_micros[-1] - graph_micros[0] >= TIME_RANGE):
        graph_micros.pop()
        graph_forces.pop()
        graph_platformDistances.pop()
        print(len(graph_micros))
    # Print the received values
    print(f'Micros: {sensorValues[0]}, Force: {sensorValues[1]}, Platform Distance: {sensorValues[2]}')

while(1):
    process()
# # Function to update the plot
# def update_plot(frame):
#     process()
#     plt.cla()
#     plt.plot(micros, forces, label ='Forces')
#     plt.plot(micros, platformDistances, label ='Platform Distance')
#     plt.xlabel('Time')
#     plt.ylabel('Sensor Value')
#     plt.legend()

# # Function to save data to csv file when plot is closed
# def on_close(event):
#     # Generate a unique filename using a timestamp
#     timestamp  = tim.strftime("%Y%m%d-%H%M%S")
#     filename = f'pillar_puller_{timestamp}.csv'

#     with open(filename, 'w', newline='') as csvfile:
#         writer = csv.writer(csvfile)
#         writer.writerow(['Time', 'Forces', 'Platform Position'])
#         for time, force, pos in zip(micros, forces, platformDistances):
#             writer.writerow([time, force, pos])

#     print(f"Data save to {filename}")

# # Register the callback function when the plot window is closed
# fig, ax = plt.subplots()
# fig.canvas.mpl_connect('close_event', on_close)

# ani = FuncAnimation(fig, update_plot, interval = 1)
# plt.show()