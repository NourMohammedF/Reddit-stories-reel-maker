import sys
import os
import subprocess

# Auto-activate virtual environment
def setup_and_activate_venv():
    # Get the script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define venv path - script is in "E:\My Code", venv is in "E:\My Code\libraries\final_story_env"
    venv_path = os.path.join(script_dir, 'libraries', 'final_story_env')
    
    # Check if running in virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    
    if not in_venv:
        # Check if venv exists
        if not os.path.exists(venv_path):
            print(f"Virtual environment not found at: {venv_path}")
            print("Please create it first using the setup instructions.")
            sys.exit(1)
        
        # Determine the Python executable in venv
        if sys.platform == 'win32':
            venv_python = os.path.join(venv_path, 'Scripts', 'python.exe')
        else:
            venv_python = os.path.join(venv_path, 'bin', 'python')
        
        # Re-run the script with venv Python
        print(f"Activating virtual environment: {venv_path}")
        subprocess.run([venv_python] + sys.argv)
        sys.exit(0)

# Call the setup function before imports
setup_and_activate_venv()

# Now import the required packages (will use venv packages)
import random
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, AudioFileClip, CompositeAudioClip
import pysrt
from moviepy.config import change_settings
from datetime import datetime
from pathlib import Path

base_dir = Path(__file__).parent.absolute()

# Specify the full path to magick.exe
IMAGEMAGICK_BINARY = base_dir / 'libraries' / 'video_intro' /'ImageMagick-7.1.1-Q16-HDRI' / 'magick.exe'

# Update MoviePy's settings
change_settings({"IMAGEMAGICK_BINARY": IMAGEMAGICK_BINARY})

def crop_to_reels_aspect_ratio(video_clip):
    width, height = video_clip.size
    target_aspect_ratio = 9 / 16

    if width / height > target_aspect_ratio:
        # Video is wider than target aspect ratio
        new_width = int(height * target_aspect_ratio) 
        new_height = height
    else:
        # Video is taller than target aspect ratio or exactly the target aspect ratio
        new_width = width
        new_height = int(width / target_aspect_ratio)

    x_center = width / 2
    y_center = height / 2
    x1 = x_center - new_width / 2
    y1 = y_center - new_height / 2
    x2 = x_center + new_width / 2
    y2 = y_center + new_height / 2

    return video_clip.crop(x1=x1, y1=y1, x2=x2, y2=y2).resize((1080, 1920))  # Resize to standard  (1920x1080)

def add_subtitles_to_random_video(video_folder, subtitle_path, voice_path, output_path):
    # List all video files in the specified folder
    video_files = [os.path.join(video_folder, f) for f in os.listdir(video_folder)]
    
    if not video_files:
        raise ValueError("No video files found in the specified folder.")
    
    # Select a random video file
    video_path = random.choice(video_files)
    
    # Load video clip
    video_clip = VideoFileClip(video_path)
    
    # Load subtitles from SRT file
    subtitles = pysrt.open(subtitle_path)
    
    # Create an empty list to hold subtitle TextClips
    subtitle_clips = []
    
    # Easing function for smooth zoom-out effect
    def ease_out(t):
        return 1 - (1 - t) * (1 - t)  # Quadratic ease-out function

    # Iterate over each subtitle entry
    for subtitle in subtitles:
        start = subtitle.start.to_time()
        end = subtitle.end.to_time()
        start_dt = datetime.combine(datetime.min, start)
        end_dt = datetime.combine(datetime.min, end)
        duration = (end_dt - start_dt).total_seconds()
        
        # Skip subtitles with zero or very small duration to avoid division by zero
        if duration <= 0.01:
            continue
            
        subtitle_text = subtitle.text

        # Create a TextClip with the subtitle text
        txt_clip = TextClip(subtitle_text, fontsize=120, color='white', font='Impact',
                            stroke_color='black', stroke_width=5, kerning=-3 ).set_duration(duration)

        txt_clip = txt_clip.set_position('center')
        start_seconds = (start_dt - datetime.combine(start_dt.date(), datetime.min.time())).total_seconds()
        txt_clip = txt_clip.set_start(start_seconds)

        # Add an ease-out zoom effect to the TextClip
        zoom_txt_clip = txt_clip.resize(lambda t: max(1, 1 + 0.08 * ease_out(t / duration)))
        zoom_txt_clip = zoom_txt_clip.set_duration(duration)

        # Ensure mask exists
        if zoom_txt_clip.mask is None:
            zoom_txt_clip = zoom_txt_clip.add_mask()

        fade_duration = min(0.4, duration / 4)

        # Modify the mask to fade in/out based on t
        def fade_opacity(get_frame, t):
            if t < fade_duration:
                alpha = t / fade_duration
            elif t > duration - fade_duration:
                alpha = max(0, (duration - t) / fade_duration)
            else:
                alpha = 1.0
            return get_frame(t) * alpha

        zoom_txt_clip.mask = zoom_txt_clip.mask.fl(fade_opacity)

        subtitle_clips.append(zoom_txt_clip)

        
    # Load voiceover audio clip
    voice_clip = AudioFileClip(voice_path)
    
    # Calculate durations
    voice_duration = voice_clip.duration
    video_duration = video_clip.duration
    
    # Determine the maximum duration
    max_duration = min(voice_duration, video_duration)
    
    # Select a random start time within valid range
    max_start_time = video_duration - voice_duration
    start_time = random.uniform(0, max_start_time)
    
    # Trim video clip starting from random start time for the duration of the voice clip
    trimmed_video_clip = video_clip.subclip(start_time, start_time + voice_duration)
    
    # Crop the video to reels aspect ratio and resize to standard 720p
    cropped_video_clip = crop_to_reels_aspect_ratio(trimmed_video_clip)
    
    # Apply fade in and fade out effects
    faded_video_clip = cropped_video_clip.fadein(0.5).fadeout(0.5)  # 0.5 second fade in and fade out
    
    # Set the audio of the video with subtitles to the voice audio track
    video_with_subtitles = faded_video_clip.set_audio(voice_clip)
    
    # Overlay all subtitle clips on the video with subtitles
    video_with_subtitles = CompositeVideoClip([video_with_subtitles] + subtitle_clips)
    
    # Write the result to a file
    output_file = os.path.join(output_path, 'final_video.mp4')
    video_with_subtitles.write_videofile(output_file, codec='libx264', audio_codec='aac')


# Example usage
if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    video_folder = os.path.join(base_dir, 'final story', 'minecraft videos')
    subtitle_path = os.path.join(base_dir, 'transcriber', 'story_sub.srt')
    voice_path = os.path.join(base_dir, 'text to speech', 'story_voice.wav')
    output_path = os.path.join(base_dir, 'final story')
    
    add_subtitles_to_random_video(video_folder, subtitle_path, voice_path, output_path)