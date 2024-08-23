import csv
import time
import serial
import threading
import tkinter
import tkinter.messagebox
import customtkinter
from PIL import Image, ImageTk
import logging
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

customtkinter.set_appearance_mode("Light")  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme("dark-blue")  # Themes: "blue" (standard), "green", "dark-blue"

class serialBuffer():
    # Constants
    SERIAL_PORT = 'COM10'
    BAUD_RATE = 115200

    def __init__(self):
        self.micros = []
        self.forces = []
        self.platformDistances = []
        self.ser = serial.Serial(self.SERIAL_PORT, self.BAUD_RATE)

    def populate(self):
        while self.ser.is_open:
            line = self.ser.readline().decode('utf-8').strip()  # Decode line from the serial port.
            sensorValues = line.split(',')
            # Read the data from the serial connection
            current_time = float(sensorValues[0])
            force = float(sensorValues[1])
            platform_distance = float(sensorValues[2])
            # Append the data to the lists
            self.micros.append(current_time)
            self.forces.append(force)
            self.platformDistances.append(platform_distance)

    def get_data(self):
        return self.micros, self.forces, self.platformDistances

class App(customtkinter.CTk):
    def __init__(self, buffer):
        super().__init__()

        # configure window
        self.title("Contactile")
        self.center_geometry(1920, 1080)
        # self.iconbitmap("assets/logo.ico")

        # configure grid layout (2x2)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=5)
        self.rowconfigure(0, weight=7)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=0)

        # Create sidebar
        self.sidebar_left = customtkinter.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_left.grid(row=0, column=0, rowspan=3, sticky="nsew")
        # Logo in sidebar
        self.logo = customtkinter.CTkFrame(self, corner_radius=0)
        self.logo.columnconfigure((0,1), weight=1)
        self.logo.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="nw")
        self.logo_src = customtkinter.CTkImage(light_image=Image.open("assets/logo.png"), size=(32, 32))
        self.logo_img = customtkinter.CTkLabel(self.logo, image=self.logo_src, text='', bg_color="transparent")
        self.logo_img.grid(row=0, column=0)
        self.logo_label = customtkinter.CTkLabel(self.logo, text="Template", font=customtkinter.CTkFont(size=24, weight="bold"))
        self.logo_label.grid(row=0, column=1, padx=(20,0), pady=(0,0))

        # Add entry box and button for CSV generation
        self.filename_entry = customtkinter.CTkEntry(self, placeholder_text="Enter filename")
        self.filename_entry.grid(row=0, column=0, padx=20, pady=(0, 5), sticky="ew")
        self.generate_csv_button = customtkinter.CTkButton(self, text="Generate CSV", command=lambda: self.generate_csv(self.filename_entry.get()))
        self.generate_csv_button.grid(row=0, column=0, padx=20, pady=(70, 10), sticky="ew")

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
        self.log_buffer_periodically()

        # Set up the graph
        self.setup_graph()

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
        micros, forces, platformDistances = self.buffer.get_data()
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

    # Function to log the most recent data point from the buffer periodically
    def log_buffer_periodically(self):
        ''' Log the most recent data point from the buffer periodically '''
        micros, forces, platformDistances = self.buffer.get_data()
        if micros and forces and platformDistances:  # Check if there is data in the buffer
            self.logger.info(f"Time: {micros[-1]}, Forces: {forces[-1]}, Platform Position: {platformDistances[-1]}")
        self.after(2, self.log_buffer_periodically)  # Schedule this method to run again after 100 ms (0.1 second)

    # Function to set up the graph
    def setup_graph(self):
        self.fig, self.ax = plt.subplots()
        self.line1, = self.ax.plot([], [], label='Platform Distances')
        self.line2, = self.ax.plot([], [], label='Forces')
        self.ax.legend(loc='upper left')
        self.ax.set_title('Pillar Puller Data')

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tabview.tab("Home"))
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        self.micros = []
        self.forces = []
        self.platformDistances = []
        self.counter = 0

        self.ani = FuncAnimation(self.fig, self.animate, interval=10, blit=True)

    # Function to animate the graph
    def animate(self, frame):
        micros, forces, platformDistances = self.buffer.get_data()

        if len(micros) > 0 and len(forces) > 0 and len(platformDistances) > 0:
            current_time = micros[-1]
            force = forces[-1]
            platform_distance = platformDistances[-1]

            self.counter += 1

            if self.counter % 2 == 0:
                self.micros.append(current_time)
                self.forces.append(force)
                self.platformDistances.append(platform_distance)

                max_points = 100
                length = max(min(len(self.micros), max_points), 1)

                self.micros = self.micros[-length:]
                self.forces = self.forces[-length:]
                self.platformDistances = self.platformDistances[-length:]

                self.line1.set_ydata(self.platformDistances)
                self.line2.set_ydata(self.forces)

                if length <= max_points:
                    xs = list(range(0, length))
                    if length > 1:
                        self.ax.set_xlim(0, length - 1)
                    else:
                        self.ax.set_xlim(-0.5, 0.5)
                    self.line1.set_xdata(xs)
                    self.line2.set_xdata(xs)

                ymin = float("inf")
                ymax = float("-inf")
                for line in [self.line1, self.line2]:
                    a = line.get_alpha()
                    if a is None or a > 0:
                        lmin = np.min(line.get_ydata())
                        lmax = np.max(line.get_ydata())
                        if lmin < ymin:
                            ymin = lmin
                        if lmax > ymax:
                            ymax = lmax

                yrange = ymax - ymin
                self.ax.set_ylim(ymin - 0.1 * yrange, ymax + 0.1 * yrange)

        return self.line1, self.line2

    def on_closing(self):
        if tkinter.messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.destroy()

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