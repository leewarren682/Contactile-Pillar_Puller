import tkinter as tk

win = tk.Tk() # Create a window to act as the root widget

# Initialise the window with title and minimum size
win.title("Pillar Puller")
win.minsize(200, 200)

# Label the widget
label = tk.Label(win, text="click to choose a profile")
label.grid(column=1, row=1)