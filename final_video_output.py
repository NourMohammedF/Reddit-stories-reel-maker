import sys
import os
import subprocess

# Auto-activate virtual environment
def setup_and_activate_venv():
    # Get the script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define venv path - script is in "E:\My Code", venv is in "E:\My Code\libraries\final_video_output_env"
    venv_path = os.path.join(script_dir, 'libraries', 'final_video_output_env')
    
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
import re
import random
from moviepy.editor import VideoFileClip, concatenate_videoclips, AudioFileClip, CompositeAudioClip
from moviepy.audio.fx.all import audio_loop

def add_intro_and_music_with_original_audio(intro_path, main_video_path, music_folder, output_path):
    try:
        # Load video clips
        intro_clip = VideoFileClip(intro_path)
        main_video_clip = VideoFileClip(main_video_path)

        # Adjust main video to match intro video's resolution and fps if needed
        main_video_clip = main_video_clip.resize(height=intro_clip.h).set_fps(intro_clip.fps)

        # Calculate durations
        intro_duration = intro_clip.duration
        main_video_duration = main_video_clip.duration
        total_duration = intro_duration + main_video_duration

        # Select a random music file from the folder
        music_files = os.listdir(music_folder)
        random_music_file = random.choice(music_files)
        music_path = os.path.join(music_folder, random_music_file)

        # Load and loop music clip for the FULL duration
        music_clip = AudioFileClip(music_path).volumex(0.2)
        music_clip = audio_loop(music_clip, duration=total_duration)

        # Get original audio from video clips
        intro_audio = intro_clip.audio
        main_video_audio = main_video_clip.audio

        # Combine original audio with music for BOTH intro and main video
        intro_with_music_audio = CompositeAudioClip([intro_audio, music_clip.subclip(0, intro_duration)])
        main_video_with_music_audio = CompositeAudioClip([main_video_audio, music_clip.subclip(intro_duration, total_duration)])
        
        # Set the audio for both clips
        intro_clip_final = intro_clip.set_audio(intro_with_music_audio)
        main_video_clip_final = main_video_clip.set_audio(main_video_with_music_audio)
        
        # Concatenate video clips with method='compose' to avoid timing issues
        final_clip = concatenate_videoclips([intro_clip_final, main_video_clip_final], method='compose')

        # Write the final clip to a file
        final_clip.write_videofile(output_path, codec='libx264', audio_codec='aac', threads=8, preset='medium')

    finally:
        # Close all clips to free up resources
        if 'intro_clip' in locals():
            intro_clip.close()
        if 'main_video_clip' in locals():
            main_video_clip.close()
        if 'music_clip' in locals():
            music_clip.close()
        if 'final_clip' in locals():
            final_clip.close()


def rename_video_with_title(output_path, title_file):
    # Read title from the text file
    with open(title_file, 'r', encoding='utf-8') as file:
        title = file.read().strip()

    # Get the directory and file extension
    output_dir = os.path.dirname(output_path)
    ext = os.path.splitext(output_path)[1]

    # Generate the new filename with an incrementing number
    def get_next_available_filename(base_name, extension, directory):
        # Find all files in the directory with the base name and extension
        files = os.listdir(directory)
        pattern = re.compile(rf'{re.escape(base_name)}(\d+)?{re.escape(extension)}')
        numbers = []
        for file in files:
            match = pattern.match(file)
            if match:
                number = match.group(1)
                if number is not None:
                    numbers.append(int(number))
        # Determine the next available number
        next_number = max(numbers, default=0) + 1
        return f'{base_name}{next_number}{extension}'

    new_output_filename = get_next_available_filename('#', ext, output_dir)
    new_output_path = os.path.join(output_dir, new_output_filename)
    
    # Rename the output video file
    os.rename(output_path, new_output_path)
    print(f'Video renamed to: {new_output_path}')

# Example usage:
base_dir = os.path.dirname(os.path.abspath(__file__))
intro_path = os.path.join(base_dir, 'video intro', 'final_intro.mp4')
main_video_path = os.path.join(base_dir, 'final story', 'final_video.mp4')
music_folder = os.path.join(base_dir, 'final story', 'random song')
output_path = os.path.join(base_dir, 'ready', 'output_video.mp4')
title_file = os.path.join(base_dir, 'reddit stories', 'title.txt')

add_intro_and_music_with_original_audio(intro_path, main_video_path, music_folder, output_path)
rename_video_with_title(output_path, title_file)