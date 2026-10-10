import os
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

# Function to shutdown the PC
def shutdown_now():
    os.system("shutdown /s /t 1")  # Shutdown immediately

# Function to cancel the shutdown
def cancel_shutdown():
    os.system("shutdown /a")  # Abort shutdown
    root.destroy()  # Close the GUI

# Function to update the countdown timer
def update_timer():
    global remaining_time
    if remaining_time > 0:
        timer_label.config(text=f"Time remaining: {remaining_time} seconds")
        remaining_time -= 1
        root.after(1000, update_timer)  # Update every 1 second
    else:
        shutdown_now()  # Shutdown when time runs out

# Create the main window
root = tk.Tk()
root.title("Shutdown Timer")
root.geometry("400x200")
root.resizable(False, False)  # Disable resizing

# Make the window always appear on top
root.attributes("-topmost", True)  # Always on top

# Center the window on the screen
window_width = 400
window_height = 200
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
x = (screen_width // 2) - (window_width // 2)
y = (screen_height // 2) - (window_height // 2)
root.geometry(f"{window_width}x{window_height}+{x}+{y}")

# Set a modern font with bold text
modern_font = ("Segoe UI", 14, "bold")  # Added "bold" here

# Filmora-inspired color scheme
background_color = "#2d2d2d"  # Dark gray background
accent_color = "#ffffff"  # White for accents
button_color = "#20b2aa"  # Teal for buttons
text_color = "#000000"  # Black text

# Set the background color
root.configure(bg=background_color)

# Create a label for the countdown timer
timer_label = tk.Label(
    root,
    text=f"Time remaining: 15 seconds",
    font=modern_font,  # Uses the bold font
    bg=background_color,
    fg=text_color
)
timer_label.place(relx=0.5, rely=0.3, anchor="center")

# Create a frame for the buttons
button_frame = tk.Frame(root, bg=background_color)
button_frame.place(relx=0.5, rely=0.7, anchor="center")

# Create the "Shutdown Now" button
shutdown_button = ttk.Button(
    button_frame,
    text="Shutdown Now",
    command=shutdown_now,
    style="Filmora.TButton"
)
shutdown_button.pack(side=tk.LEFT, padx=10)

# Create the "Cancel Shutdown" button
cancel_button = ttk.Button(
    button_frame,
    text="Cancel Shutdown",
    command=cancel_shutdown,
    style="Filmora.TButton"
)
cancel_button.pack(side=tk.RIGHT, padx=10)

# Style the buttons
style = ttk.Style()
style.configure(
    "Filmora.TButton",
    font=modern_font,  # Uses the bold font
    padding=10,
    background=button_color,
    foreground=text_color,
    borderwidth=0,
    focusthickness=3,
    focuscolor=accent_color
)
style.map(
    "Filmora.TButton",
    background=[("active", accent_color)],  # Change to white on hover
    foreground=[("active", text_color)]
)

# Set the initial countdown time
remaining_time = 20

# Start the countdown timer
update_timer()

# Run the GUI
root.mainloop()