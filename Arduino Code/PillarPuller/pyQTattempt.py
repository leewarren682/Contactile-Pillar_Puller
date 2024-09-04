import csv
import os
import time
import serial
import threading
import tkinter
import tkinter.messagebox
import customtkinter
from PIL import Image, ImageTk
import logging
import time
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from multiprocessing import Pool
import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore, QtGui, QtWidgets


# Create a class purely to handle the serial Buffer
class serialBuffer():
    # Constants
    SERIAL_PORT = 'COM3'
    BAUD_RATE = 115200

    def __init__(self):
        self.micros = []
        self.forces = []
        self.platformDistances = []
        self.filtered_forces = []
        self.ser = serial.Serial(self.SERIAL_PORT, self.BAUD_RATE)

    def populate(self):
        while self.ser.is_open and self.ser.readable():
            line = self.ser.readline().decode('utf-8').strip()
            if ',' in line:
                sensorValues = line.split(',')
                if len(sensorValues) >= 4:
                    try:
                        current_time = float(sensorValues[0])
                        force = float(sensorValues[1])
                        platform_distance = float(sensorValues[2])
                        filtered_force = float(sensorValues[3])

                        # Append the data to the lists
                        self.micros.append(current_time)
                        self.forces.append(force)
                        self.platformDistances.append(platform_distance)
                        self.filtered_forces.append(filtered_force)
                    except ValueError as e:
                        print(f"Error converting sensor values to float: {e}")
                else:
                    print(f"Received incomplete data: {line}")

    def get_data(self):
        return self.micros, self.forces, self.platformDistances, self.filtered_forces

    def send_command(self, command):
        self.ser.write((command + '\n').encode('utf-8'))


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # Temperature vs time plot
        self.plot_graph = pg.PlotWidget()
        self.setCentralWidget(self.plot_graph)
        print("Creating buffer")
        
        self.buffer = serialBuffer()
        # Populate the buffer in a separate thread
        populate_thread = threading.Thread(target=self.buffer.populate)  # Create a thread to populate the buffer
        populate_thread.daemon = True
        populate_thread.start()

        # Set up a timer to update the plot periodically
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(50)  # Update every 50ms

    def update_plot(self):
        micros, forces, platformDistances, filtered_forces = self.buffer.get_data()
        if micros and forces and platformDistances and filtered_forces:  # Check if there is data to plot
            # Plot only the latest 50 data points
            latest_micros = micros[-500:]
            latest_filtered_forces = filtered_forces[-500:]
            latest_platform_distances = platformDistances[-500:]
            
            self.plot_graph.clear()  # Clear the previous plot
            self.plot_graph.plot(latest_micros, latest_filtered_forces)  # Plot the new data
            self.plot_graph.plot(latest_micros, latest_platform_distances)  # Plot the new data
            
            # Set the range for the x and y axes
            self.plot_graph.setRange(xRange=(min(latest_micros), max(latest_micros)), yRange=(min(latest_filtered_forces + latest_platform_distances), max(latest_filtered_forces + latest_platform_distances)))


app = QtWidgets.QApplication([])
main = MainWindow()
main.show()
app.exec()