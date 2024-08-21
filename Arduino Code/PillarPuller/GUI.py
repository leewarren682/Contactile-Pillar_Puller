import tkinter as tk

# Create the main application window
root = tk.Tk()

# Set the title of the main window
root.title("Pillar Puller Control Panel")

# Set the size of the main window (optional)
root.geometry("400x300")

# Add a simple label widget to the main window
label = tk.Label(root, text="Please select a profile")
label.pack(pady=20) # Use widget's .pack() method to add to the window

# Add a clickable button to the main window
button = tk.Button(
    text="profile1",
    width=25,
    height=5,
    bg="purple",
    fg="white"
)

button.pack()

# Run the application's main event loop
root.mainloop()
