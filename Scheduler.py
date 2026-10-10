import schedule
import time
import subprocess
from datetime import datetime

# Define the times you want to run the script in 12-hour format (two times a day)
run_times = ['06:00 PM']

def convert_to_24_hour(time_str):
    # Convert 12-hour format to 24-hour format
    return datetime.strptime(time_str, '%I:%M %p').strftime('%H:%M')

def run_main_script():
    # Path to your main Python script
    main_script_path = 'C:\\Users\\Nour\\Desktop\\My Code\\main.py'
    subprocess.run(['python', main_script_path])


# Schedule the script to run at the specified times (convert to 24-hour format)
for run_time in run_times:
    schedule.every().day.at(convert_to_24_hour(run_time)).do(run_main_script)

# Keep the script running and check the schedule
while True:
    schedule.run_pending()
    time.sleep(5)  # Check every 5 seconds