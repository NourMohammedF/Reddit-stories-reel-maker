import os
import random
import time
from tiktokautouploader import upload_tiktok

# Path to the text file containing the description
description_file_path = 'C:\\Users\\Nour\\Desktop\\My Code\\reddit stories\\title.txt'
subreddit_file_path = 'C:\\Users\\Nour\\Desktop\\My Code\\reddit stories\\story_subreddit.txt'
video_folder = 'C:\\Users\\Nour\\Desktop\\My Code\\ready'

# Read the title from the title text file
with open(description_file_path, 'r', encoding='utf-8') as file:
    title = file.read().strip()  # Remove any leading/trailing whitespace

# Read the subreddit name from the subreddit text file
with open(subreddit_file_path, 'r', encoding='utf-8') as file:
    subreddit_name = file.read().strip()  # Remove any leading/trailing whitespace

description = f"r/{subreddit_name} : {title}"

# Get a list of all video files in the 'ready' folder
video_files = [f for f in os.listdir(video_folder) if f.endswith('.mp4')]

# Select a random video from the list
if video_files:
    video_path = os.path.join(video_folder, random.choice(video_files))
else:
    raise FileNotFoundError("No video files found in the specified folder.")

accountname = 'tell_mee_stories'
hashtags = [
  '#Stories', 
  '#tell_mee_stories',
  '#minecraftparkour',
  '#Reddit', 
  '#Shorts', 
  '#Stories', 
  '#NoSleep', 
  '#CreepyStories', 
  '#Horror', 
  '#RedditNarrations', 
  '#TrueHorror', 
  '#Viral', 
  '#HorrorCommunity', 
  '#SpookyStories', 
  '#TerrifyingTales', 
  '#HorrorContent', 
  '#CreepyReddit', 
  '#ShortHorror', 
  '#HorrorLovers', 
  '#CreepyVibes', 
  '#ParanormalStories', 
  '#ViralShorts'
]

# Upload the TikTok video
upload_tiktok(video=video_path, description=description, accountname=accountname, schedule=None, hashtags=hashtags, headless=False)

# Wait for 10 seconds before shutting down
time.sleep(10)