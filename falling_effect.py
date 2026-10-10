import sys
import os
import subprocess

# Auto-activate virtual environment
def setup_and_activate_venv():
    # Get the script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define venv path - script is in "E:\My Code", venv is in "E:\My Code\libraries\falling_effect_env"
    venv_path = os.path.join(script_dir, 'libraries', 'falling_effect_env')
    
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
from moviepy.editor import VideoFileClip, concatenate_videoclips, AudioFileClip, CompositeAudioClip
from scipy.ndimage import rotate as scipy_rotate
import numpy as np
import random

def calculate_animation_duration(height, initial_speed, acceleration):
    a = 0.5 * acceleration
    b = initial_speed
    c = -height
    
    discriminant = b**2 - 4 * a * c
    if discriminant >= 0:
        t1 = (-b + np.sqrt(discriminant)) / (2 * a)
        t2 = (-b - np.sqrt(discriminant)) / (2 * a)
        return max(t1, t2)
    else:
        return 0

def apply_falling_rotation_effect(input_path, output_path, sfx_folder_path):
    # Load the video
    video = VideoFileClip(input_path)
    video_duration = video.duration
    height = video.h
    
    # Define initial falling speed and acceleration
    initial_falling_speed = 0
    acceleration = 14000
    
    # Calculate the duration for the falling effect to complete
    animation_duration = calculate_animation_duration(height, initial_falling_speed, acceleration)
    
    if animation_duration <= 0:
        raise ValueError("Animation duration must be positive. Check the parameters.")
    
    # Define the parts of the video
    main_part = video.subclip(0, video_duration - animation_duration)
    effect_part = video.subclip(video_duration - animation_duration, video_duration)
    
    # Define the falling and rotating effects
    def falling_rotation_effect(get_frame, t):
        frame = get_frame(t)
        rotation_angle = 30 * t
        y_offset = int(0.5 * acceleration * t**2 + initial_falling_speed * t)
        
        rotated_frame = scipy_rotate(frame, angle=rotation_angle, reshape=False, mode='nearest')
        
        height, width, _ = rotated_frame.shape
        result_frame = np.zeros_like(rotated_frame)
        if y_offset < height:
            result_frame[y_offset:, :, :] = rotated_frame[:height-y_offset, :, :]
        
        return result_frame

    # Apply the effect to the last part of the video
    animated_effect_part = effect_part.fl(lambda gf, t: falling_rotation_effect(gf, t))
    
    # Load and modify the SFX
    sfx_files = [os.path.join(sfx_folder_path, file) for file in os.listdir(sfx_folder_path) if file.endswith('.wav')]
    if not sfx_files:
        raise FileNotFoundError("No SFX files found in the specified folder.")
    
    sfx_path = random.choice(sfx_files)
    sfx_clip = AudioFileClip(sfx_path).volumex(0.1)
    
    # Extract the audio parts
    original_audio = video.audio
    effect_audio = original_audio.subclip(video_duration - animation_duration, video_duration)
    
    # Create audio for the effect part with SFX
    sfx_audio = sfx_clip.subclip(0, animation_duration)
    combined_effect_audio = CompositeAudioClip([effect_audio, sfx_audio.set_start(0)])
    
    # Create audio for the entire video
    main_audio_part = original_audio.subclip(0, video_duration - animation_duration)
    final_audio = CompositeAudioClip([main_audio_part, combined_effect_audio.set_start(video_duration - animation_duration)])
    
    # Create final video with audio
    final_video = concatenate_videoclips([main_part, animated_effect_part])
    final_video = final_video.set_audio(final_audio)
    
    # Save the output video
    final_video.write_videofile(output_path, codec='libx264')

# Specify paths
base_dir = os.path.dirname(os.path.abspath(__file__))
input_video_path = os.path.join(base_dir, 'video intro', 'video_intro.mp4')
output_video_path = os.path.join(base_dir, 'video intro', 'video_intro_falling.mp4')
sfx_folder_path = os.path.join(base_dir, 'sfx')

# Apply the effect and save the video
apply_falling_rotation_effect(input_video_path, output_video_path, sfx_folder_path)