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
import numpy as np

customtkinter.set_appearance_mode("Dark")  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme("dark-blue")  # Themes: "blue" (standard), "green", "dark-blue"

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
                        print(line)
                    except ValueError as e:
                        print(f"Error converting sensor values to float: {e}")
                else:
                    print(f"Received incomplete data: {line}")

    def get_data(self):
        return self.micros, self.forces, self.platformDistances, self.filtered_forces

    def send_command(self, command):
        self.ser.write((command + '\n').encode('utf-8'))


class App(customtkinter.CTk):
    def __init__(self, buffer):
        super().__init__()

        # configure window
        self.title("Contactile")
        self.center_geometry(1920, 1080)
        # self.iconbitmap("assets/logo.ico")

        # configure grid layout (2x2)
        self.columnconfigure(0, weight=1) # Column for the sidebar
        self.columnconfigure(1, weight=5) # Column for the tabview
        self.rowconfigure(0, weight=7) # Row for the sidebar and tabview
        self.rowconfigure(1, weight=1) # Row for the status window
        self.rowconfigure(2, weight=0) # Row for the progress bar

        # Create sidebar
        self.sidebar_left = customtkinter.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_left.grid(row=0, column=0, rowspan=3, sticky="nsew")

        # Configure grid layout for sidebar_left
        self.sidebar_left.columnconfigure(0, weight=1)
        for i in range(20):  # Assuming you have 11 buttons
            self.sidebar_left.rowconfigure(i, weight=1)

        # Construct the path to the logo.png file
        current_dir = os.path.dirname(__file__)
        logo_path = os.path.join(current_dir, 'assets', 'logo.png')

        # Logo in sidebar
        self.logo = customtkinter.CTkFrame(self.sidebar_left, corner_radius=0)
        self.logo.columnconfigure((0,1), weight=1)
        self.logo.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="nw")
        self.logo_src = customtkinter.CTkImage(light_image=Image.open(logo_path), size=(32, 32))
        self.logo_img = customtkinter.CTkLabel(self.logo, image=self.logo_src, text='', bg_color="transparent")
        self.logo_img.grid(row=0, column=0)
        self.logo_label = customtkinter.CTkLabel(self.logo, text="Template", font=customtkinter.CTkFont(size=24, weight="bold"))
        self.logo_label.grid(row=0, column=1, padx=(20,0), pady=(0,0))

        # create central tabview
        self.tabview = customtkinter.CTkTabview(self)
        self.tabview.grid(row=0, column=1, sticky="nsew", padx=(2,2), pady=(0,2))
        self.tabview.add("Home")
        self.tabview.add("Tab 2")
        self.tabview.tab("Home").grid_columnconfigure(0, weight=1)
        self.tabview.tab("Tab 2").grid_columnconfigure(0, weight=1)

        # create lower tabview
        self.tabview_lower = customtkinter.CTkTabview(self)
        self.tabview_lower.grid(row=1, column=1, sticky="nsew", padx=(2,2), pady=(2,2))
        self.tabview_lower.add("Status")
        self.tabview_lower.tab("Status").grid_columnconfigure(0, weight=1)
        self.tabview_lower.tab("Status").grid_rowconfigure(0, weight=1)

        # Create status window
        self.status_text = customtkinter.CTkTextbox(self.tabview_lower.tab("Status"), corner_radius=2, font=customtkinter.CTkFont(size=16))
        self.status_text.grid(sticky="nsew")

        # Create a logger to write to the status window
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %I:%M:%S%p")
        self.text_handler = TextHandler(self.status_text, formatter)
        
        # Add a handler to the system logger
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(self.text_handler)
        self.logger.setLevel(logging.DEBUG)

        # Store the buffer
        self.buffer = buffer

        # Create a status bar for long running processes
        self.progressbar = customtkinter.CTkProgressBar(self)
        self.progressbar.grid(row=2, column=1, sticky="ew")

        self.progressbar.configure(mode="indeterminate")
        self.progressbar.start()  

        self.logger.warning('Progress bar started running as indeterminate')

    def center_geometry(self, width, height):
        ''' Set the window size and center on screen '''
        self.update_idletasks()
        self.geometry(f"{1920}x{1080}")

        print(self.geometry())

        # Get screen resolution
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        x = screen_width/2 - width/2
        y = screen_height/2 - height/2

        self.geometry(f"{width}x{height}+{int(x)}+{int(y)}")

    def on_closing(self):
        self.buffer.ser.close()  # Close the serial port

    # Function to set up the graph
    def setup_graph(self):
        self.fig, self.ax = plt.subplots()
        self.ax.set_aspect('auto')
        self.line1, = self.ax.plot([], [], label='Platform Distances')
        self.line2, = self.ax.plot([], [], label='Forces')
        self.line3, = self.ax.plot([], [], label='Filtered Forces')  # Add line for filtered forces
        self.ax.legend(loc='upper left')
        self.ax.set_title('Pillar Puller Data')

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tabview.tab("Home"))
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")




    def plot_graph(self, data, N0, N1):
        self.micros = []
        self.forces = []
        self.platformDistances = []
        self.filtered_forces = []
        self.counter = 0
        
        for frame in range (N0, N1): # Animation frame
            

        micros, forces, platformDistances, filtered_forces = self.buffer.get_data()
        
        # Use multiprocessing to plot the graph
        self.ax.clear()
        self.ax.plot(micros[N0:N1], forces[N0:N1], label='Forces')
        self.ax.plot(micros[N0:N1], platformDistances[N0:N1], label='Platform Distances')
        self.ax.plot(micros[N0:N1], filtered_forces[N0:N1], label='Filtered Forces')
        self.ax.legend(loc='upper left')
        self.ax.set_title('Pillar Puller Data')
        self.canvas.draw()
        

### WARNING: This is not thread safe. Look at https://github.com/beenje/tkinter-logging-text-widget for a thread-safe logger
class TextHandler(logging.Handler):
    """This class allows you to log to a Tkinter Text or ScrolledText widget"""
    def __init__(self, text, formatter=None):
        logging.Handler.__init__(self)
        
        self.text = text # Destination Text or ScrolledText widget

        if formatter is not None:
            self.setFormatter(formatter)
        

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text.configure(state='normal')
            self.text.insert(tkinter.END, msg + '\n')
            self.text.configure(state='disabled')
            # Autoscroll to the bottom
            self.text.yview(tkinter.END)

        # This is necessary because we can't modify the Text from other threads
        self.text.after(0, append)

if __name__ == "__main__":
    # [Optional] Set up the console logger
    logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", 
                        datefmt="%Y-%m-%d %I:%M:%S%p", 
                        level=logging.INFO)
    buffer = serialBuffer()


    # Populate the buffer in a separate thread
    populate_thread = threading.Thread(target=buffer.populate)  # Create a thread to populate the buffer
    populate_thread.daemon = True
    populate_thread.start()

    app = App(buffer)
    app.mainloop()
    app.on_closing()

    buffer.ser.close()