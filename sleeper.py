import tkinter as tk
import os
import sys

class ShutdownApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sleep Warning")
        
        # Countdown variables
        self.countdown_time = 10  # 2 minutes in seconds

        # Create and place widgets
        self.label = tk.Label(root, text=f"Your PC will sleep in {self.countdown_time // 60} minutes.")
        self.label.pack(pady=20)

        self.countdown_label = tk.Label(root, text=self.format_time(self.countdown_time))
        self.countdown_label.pack(pady=20)

        self.sleep_now_button = tk.Button(root, text="Sleep Now", command=self.sleep_now)
        self.sleep_now_button.pack(side=tk.LEFT, padx=20, pady=20)

        self.cancel_button = tk.Button(root, text="Cancel Sleep", command=self.cancel_sleep)
        self.cancel_button.pack(side=tk.RIGHT, padx=20, pady=20)

        # Start countdown
        self.update_countdown()

    def format_time(self, seconds):
        minutes, seconds = divmod(seconds, 60)
        return f"{minutes:02}:{seconds:02}"

    def update_countdown(self):
        if self.countdown_time > 0:
            self.countdown_label.config(text=self.format_time(self.countdown_time))
            self.countdown_time -= 1
            self.root.after(1000, self.update_countdown)  # Update every second
        else:
            self.perform_sleep()

    def sleep_now(self):
        self.perform_sleep()

    def cancel_sleep(self):
        self.root.destroy()

    def perform_sleep(self):
        self.root.destroy()  # Close the Tkinter window before going to sleep
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")  # Command to put Windows to sleep
        sys.exit()  # Ensure the Python script exits completely after sleep

if __name__ == "__main__":
    root = tk.Tk()
    app = ShutdownApp(root)
    root.mainloop()
