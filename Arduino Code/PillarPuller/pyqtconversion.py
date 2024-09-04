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
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
import sys


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


class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        QtWidgets.QApplication.setStyle('Fusion')
        self.setWindowTitle("Pillar Puller")
        
        # Initialize the UI
        self.initUI()
        
        # Initialize the buffer
        print("Creating buffer")
        self.buffer = serialBuffer()
        
        # Populate the buffer in a separate thread
        populate_thread = threading.Thread(target=self.buffer.populate)
        populate_thread.daemon = True
        populate_thread.start()

        # Set up a timer to update the plot periodically
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(50)  # Update every 50ms
    
    # Initialize all buttons, textboxes, etc.
    def initUI(self):
        # Create a central widget and set a layout for it.
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Data vs Time plot
        self.plot_graph = pg.PlotWidget()
        layout.addWidget(self.plot_graph)
        
        # Add buttons to the layout
        
        # CSV Generation
        self.csvName = QtWidgets.QPlainTextEdit(self)
        layout.addWidget(self.csvName)
        self.generateCSVButton = QtWidgets.QPushButton("Generate CSV", self)
        layout.addWidget(self.generateCSVButton)
        self.generateCSVButton.clicked.connect(lambda: self.generate_csv(self.csvName.toPlainText()))
        
        # To_Distance input
        self.distanceInput = QtWidgets.QPlainTextEdit(self)
        layout.addWidget(self.distanceInput)
        self.distanceButton = QtWidgets.QPushButton("Move to Distance", self)
        layout.addWidget(self.distanceButton)
        self.distanceButton.clicked.connect(lambda: self.buffer.send_command(f"move_to_position{self.distanceInput.toPlainText()}"))
        
        # Open button
        self.openButton = QtWidgets.QPushButton("Open", self)
        layout.addWidget(self.openButton)
        self.openButton.clicked.connect(lambda: self.buffer.send_command("open"))
        
        # Close button
        self.closeButton = QtWidgets.QPushButton("Close", self)
        layout.addWidget(self.closeButton)
        self.closeButton.clicked.connect(lambda: self.buffer.send_command("close"))
        
        # Stop button
        self.stopButton = QtWidgets.QPushButton("Stop", self)
        layout.addWidget(self.stopButton)
        self.stopButton.clicked.connect(lambda: self.buffer.send_command("stop"))
        
        # Home Button
        self.homeButton = QtWidgets.QPushButton("Home", self)
        layout.addWidget(self.homeButton)
        
        # Break button
        self.breakButton = QtWidgets.QPushButton("Break", self)
        layout.addWidget(self.breakButton)
        self.breakButton.clicked.connect(lambda: self.buffer.send_command("break"))
        
        # Zero Position Button
        self.zeroButton = QtWidgets.QPushButton("Zero Position", self)
        layout.addWidget(self.zeroButton)
        self.zeroButton.clicked.connect(lambda: self.buffer.send_command("zero_position"))
        
    def update_plot(self):
        micros, forces, platformDistances, filtered_forces = self.buffer.get_data()
        if micros and forces and platformDistances and filtered_forces:  # Check if there is data to plot
            # Plot only the latest 500 data points
            latest_micros = micros[-500:]
            latest_filtered_forces = filtered_forces[-500:]
            latest_platform_distances = platformDistances[-500:]
            
            self.plot_graph.clear()  # Clear the previous plot
            self.plot_graph.plot(latest_micros, latest_filtered_forces)  # Plot the new data
            self.plot_graph.plot(latest_micros, latest_platform_distances)  # Plot the new data
            
            # Set the range for the x and y axes
            self.plot_graph.setRange(xRange=(min(latest_micros), max(latest_micros)), yRange=(min(latest_filtered_forces + latest_platform_distances), max(latest_filtered_forces + latest_platform_distances)))
    
    # Function to generate a CSV file from the buffer
    def generate_csv(self, filename_entry):
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        if filename_entry:
            filename = f'{filename_entry}.csv'
        else:
            filename = f'pillar_puller_{timestamp}.csv'
    
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Time', 'Forces', 'Platform Position'])
            for i in range(len(self.buffer.micros)):
                writer.writerow([self.buffer.micros[i], self.buffer.forces[i], self.buffer.platformDistances[i]])
        
        # Create Plot
        plt.figure(figsize=(10, 6))
        plt.plot(self.buffer.micros, self.buffer.forces, label='Forces')
        plt.plot(self.buffer.micros, self.buffer.platformDistances, label='Platform Position')
        plt.xlabel('Time')
        plt.ylabel('Values')
        plt.title('Forces and Platform Position Over Time')
        plt.legend()
        plt.grid(True)
        
        # Label the maximum and minimum force values on the plot
        max_force = max(self.buffer.forces)
        max_force_index = self.buffer.forces.index(max_force)
        min_force = min(self.buffer.forces)
        min_force_index = self.buffer.forces.index(min_force)
        
        plt.annotate(max_force, (self.buffer.micros[max_force_index], max_force), textcoords="offset points", xytext=(0,10), ha='center')    

        # Save Plot as Image
        plot_filename = filename.replace('.csv', '.png')
        plt.savefig(plot_filename)
        plt.close()
    

app = QtWidgets.QApplication([])
main = MyWindow()
main.show()
app.exec()