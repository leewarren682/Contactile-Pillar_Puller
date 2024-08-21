import serial
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import csv
import time as tim

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

graphing_micros = []
graphing_forces = []
graphing_platformDistances = []


# Create a function to read and process data from Teensy
def animate(frame):
    global micros, forces, platformDistances  # Declare global variables
    global graphing_micros, graphing_forces, graphing_platformDistances  # Declare global variables


    line = ser.readline().decode('utf-8').strip() # Decode line from the serial port.
    sensorValues = line.split(',')

    # Parsing and saving lines of data
    current_time = float(sensorValues[0])
    micros.append(float(sensorValues[0]))
    forces.append(float(sensorValues[1]))
    platformDistances.append(float(sensorValues[2]))
    
    graphing_micros.append(float(sensorValues[0]))
    graphing_forces.append(float(sensorValues[1]))
    graphing_platformDistances.append(float(sensorValues[2]))

    # Limit the number of displayed points
    max_points = 20  # Adjust this value based on your needs
    if len(micros) > max_points:
        graphing_micros = graphing_micros[-max_points:]
        graphing_forces = graphing_forces[-max_points:]
        graphing_platformDistances = graphing_platformDistances[-max_points:]

    # Update the data of the lines
    line1.set_data(micros, platformDistances)
    line2.set_data(micros, forces)

    # Adjust the plot limits
    ax.relim()
    ax.autoscale_view()

    print({line})

    return line1, line2

ani = FuncAnimation(fig, animate, interval=1, blit=True) #20ms draw freq
plt.show()
    
# Function to save data to csv file when plot is closed
def on_close(event):
    # Generate a unique filename using a timestamp
    timestamp  = tim.strftime("%Y%m%d-%H%M%S")
    filename = f'pillar_puller_{timestamp}.csv'

    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Time', 'Forces', 'Platform Position'])
        for time, force, pos in zip(micros, forces, platformDistances):
            writer.writerow([time, force, pos])

    print(f"Data save to {filename}")

fig.canvas.mpl_connect('close_event', on_close)

