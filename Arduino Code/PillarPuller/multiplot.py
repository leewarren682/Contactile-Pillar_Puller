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
from bokeh.plotting import figure, output_file, save
from bokeh.layouts import column
from bokeh.io import show

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

        # Create a lock for thread safety
        self.lock = threading.Lock()

        # Create and start threads for updating the lines
        self.platform_distances_thread = threading.Thread(target=self.update_platform_distances)
        self.forces_thread = threading.Thread(target=self.update_forces)

        self.platform_distances_thread.start()
        self.forces_thread.start()

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

        # Add entry box and button for CSV generation
        self.filename_entry = customtkinter.CTkEntry(self.sidebar_left, placeholder_text="Enter filename")
        self.filename_entry.grid(row=1, column=0, padx=20, pady=(1, 1), sticky="ew")
        self.generate_csv_button = customtkinter.CTkButton(self.sidebar_left, text="Generate CSV", command=lambda: self.generate_csv(self.filename_entry.get()))
        self.generate_csv_button.grid(row=2, column=0, padx=20, pady=(1, 1), sticky="ew")

        # Add entry box and button for target_position
        self.position_entry = customtkinter.CTkEntry(self.sidebar_left, placeholder_text="Enter a position (mm)")
        self.position_entry.grid(row=3, column=0, padx=20, pady=(1, 1), sticky="ew")
        self.generate_position_button = customtkinter.CTkButton(self.sidebar_left, text="Move to Distance", command=lambda: self.move_to_position(self.position_entry.get()))
        self.generate_position_button.grid(row=4, column=0, padx=20, pady=(1, 1), sticky="ew")

        # Add button to open
        self.open_button = customtkinter.CTkButton(self.sidebar_left, text="open", command=self.open_rig)
        self.open_button.grid(row=7, column=0, padx=20, pady=(1, 1), sticky="ew")

        # Add button to close
        self.close_button = customtkinter.CTkButton(self.sidebar_left, text="close", command=self.close)
        self.close_button.grid(row=8, column=0, padx=20, pady=(1, 1), sticky="ew")

        # Add button to stop
        self.stop_button = customtkinter.CTkButton(self.sidebar_left, text="stop", command=self.stop)
        self.stop_button.grid(row=9, column=0, padx=20, pady=(1, 1), sticky="ew")

        # Add button to home
        self.homing_button = customtkinter.CTkButton(self.sidebar_left, text="home", command=self.home)
        self.homing_button.grid(row=10, column=0, padx=20, pady=(1, 1), sticky="ew")

        # Add button to open until a break is detected
        self.open_until_break_button = customtkinter.CTkButton(self.sidebar_left, text="break", command=self.open_until_break)
        self.open_until_break_button.grid(row=11, column=0, padx=20, pady=(1, 1), sticky="ew")

        # Add a button to zero's the position value to 0.
        self.zero_position_button = customtkinter.CTkButton(self.sidebar_left, text="zero position", command=self.zero_position)
        self.zero_position_button.grid(row=12, column=0, padx=20, pady=(1, 1), sticky="ew")


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

        # Schedule the periodic buffer logging
        # self.log_buffer_periodically()

        # Set up the graph
        self.setup_graph()

    def update_platform_distances(self):
        while True:
            with self.lock:
                micros, forces, platformDistances, filtered_forces = self.buffer.get_data()
                if len(micros) > 0 and len(platformDistances) > 0:
                    self.line1.set_ydata(platformDistances)
                    self.line1.set_xdata(list(range(len(platformDistances))))
                    self.ax.figure.canvas.draw()

            time.sleep(0.05)  # Adjust the sleep time as needed

    def update_forces(self):
        while True:
            with self.lock:
                micros, forces, platformDistances, filtered_forces = self.buffer.get_data()
                if len(micros) > 0 and len(forces) > 0:
                    self.line2.set_ydata(forces)
                    self.line2.set_xdata(list(range(len(forces))))
                    self.ax.figure.canvas.draw()

            time.sleep(0.05)  # Adjust the sleep time as needed

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

        # Save Plot as Image
        plot_filename = filename.replace('.csv', '.png')
        plt.savefig(plot_filename)
        plt.close()
        
    # Function which tells the Teensy to stop the motor.
    def stop(self):
        self.buffer.send_command("stop")
    
    # Funcion which tells the Teensy to open.
    def open_rig(self):
        self.buffer.send_command("open")
    
    # Function which tells the Teensy to close.
    def close(self):
        self.buffer.send_command("close")

    # Function which tells the Teensy to move to a specific position.
    def move_to_position(self, position):
        self.buffer.send_command(f"move_to_position{position}")
    
    # Function which tells the Teensy to home.
    def home(self):
        self.buffer.send_command("home")

    def open_until_break(self):
        self.buffer.send_command("break")

    def zero_position(self):
        self.buffer.send_command("zero_position")

    # Function to log the most recent data point from the buffer periodically
    def log_buffer_periodically(self):
        ''' Log the most recent data point from the buffer periodically '''
        micros, forces, platformDistances, filtered_forces = self.buffer.get_data()
        if micros and forces and platformDistances:  # Check if there is data in the buffer
            self.logger.info(f"Time: {micros[-1]}, Forces: {forces[-1]}, Platform Position: {platformDistances[-1]}, Filtered Forces: {filtered_forces[-1]}")
        self.after(5000, self.log_buffer_periodically)  # Schedule this method to run again after 5000 ms (5 second)

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


        self.micros = []
        self.forces = []
        self.platformDistances = []
        self.filtered_forces = []
        self.counter = 0


        self.ani = FuncAnimation(self.fig, self.animate, interval=2, blit=True)

    # Function to animate the graph
    def animate(self, frame):
        micros, forces, platformDistances, filtered_forces = self.buffer.get_data()

        if len(micros) > 0 and len(forces) > 0 and len(platformDistances) > 0:
            current_time = micros[-1]
            force = forces[-1]
            platform_distance = platformDistances[-1]
            filtered_force = filtered_forces[-1]

            self.counter += 1

            if self.counter % 2 == 0:
                self.micros.append(current_time)
                self.forces.append(force)
                self.platformDistances.append(platform_distance)
                self.filtered_forces.append(filtered_force)

                max_points = 40 # Adjust this value to see how many points u want to plot on the graph / modulus value
                length = max(min(len(self.micros), max_points), 1)

                self.micros = self.micros[-length:]
                self.forces = self.forces[-length:]
                self.platformDistances = self.platformDistances[-length:]
                self.filtered_forces = self.filtered_forces[-length:]

                self.line1.set_ydata(self.platformDistances)
                self.line2.set_ydata(self.forces)
                self.line3.set_ydata(self.filtered_forces)

                if length <= max_points:
                    xs = list(range(0, length))
                    if length > 1:
                        self.ax.set_xlim(0, length - 1)
                    else:
                        self.ax.set_xlim(-0.5, 0.5)
                    self.line1.set_xdata(xs)
                    self.line2.set_xdata(xs)
                    self.line3.set_xdata(xs)

                ymin = float("inf")
                ymax = float("-inf")
                for line in [self.line1, self.line2, self.line3]:
                    a = line.get_alpha()
                    if a is None or a > 0:
                        lmin = np.min(line.get_ydata())
                        lmax = np.max(line.get_ydata())
                        if lmin < ymin:
                            ymin = lmin
                        if lmax > ymax:
                            ymax = lmax

                # With Redraw
                yrange = ymax - ymin
                new_ymin = ymin - 0.1 * yrange
                new_ymax = ymax + 0.1 * yrange
                current_ymin, current_ymax = self.ax.get_ylim()

                if new_ymin != current_ymin or new_ymax != current_ymax:
                    self.ax.set_ylim(new_ymin, new_ymax)
                    self.ax.figure.canvas.draw()


        return self.line1, self.line2, self.line3

    def on_closing(self):
        self.buffer.ser.close()  # Close the serial port



def plot_with_bokeh(micros, forces, platformDistances, filtered_forces):
    # Output to an HTML file
    output_file("plot.html")

    # Create a new plot with a title and axis labels
    p1 = figure(title="Forces Over Time", x_axis_label='Time (micros)', y_axis_label='Forces')
    p2 = figure(title="Platform Distances Over Time", x_axis_label='Time (micros)', y_axis_label='Platform Distances')
    p3 = figure(title="Filtered Forces Over Time", x_axis_label='Time (micros)', y_axis_label='Filtered Forces')

    # Add a line renderer with legend and line thickness
    p1.line(micros, forces, legend_label="Forces", line_width=2)
    p2.line(micros, platformDistances, legend_label="Platform Distances", line_width=2)
    p3.line(micros, filtered_forces, legend_label="Filtered Forces", line_width=2)

    # Arrange plots in a column
    layout = column(p1, p2, p3)

    # Save and show the results
    save(layout)
    show(layout)


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
    
    # Get data from the buffer
    micros, forces, platformDistances, filtered_forces = buffer.get_data()

    # Plot data using Bokeh
    plot_with_bokeh(micros, forces, platformDistances, filtered_forces)

    app = App(buffer)
    app.mainloop()
    app.on_closing()

    buffer.ser.close()