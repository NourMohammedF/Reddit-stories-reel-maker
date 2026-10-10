import sys
import os
import subprocess

# Auto-activate virtual environment
def setup_and_activate_venv():
    # Get the script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define venv path - script is in "E:\My Code", venv is in "E:\My Code\libraries\final_intro_env"
    venv_path = os.path.join(script_dir, 'libraries', 'final_intro_env')
    
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
from moviepy.editor import VideoFileClip, CompositeVideoClip, vfx

def remove_greenscreen(clip):
    # Remove green screen (chroma key) from video using mask_color
    return clip.fx(vfx.mask_color, color=[0, 0, 0], thr=50, s=5)


def crop_to_reels_aspect_ratio(clip):
    width, height = clip.size
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

    return clip.crop(x1=x1, y1=y1, x2=x2, y2=y2).resize((1080, 1920))  # Resize to full HD (1920x1080)

def main(intro_path, random_videos_dir, output_file):
    # Choose intro video
    intro_clip = VideoFileClip(intro_path)

    # Choose random video
    random_video_path = random.choice([os.path.join(random_videos_dir, f) for f in os.listdir(random_videos_dir)])
    random_clip = VideoFileClip(random_video_path)

    # Select a random start point in the random video
    random_start = random.uniform(0, random_clip.duration - intro_clip.duration)
    random_clip = random_clip.subclip(random_start, random_start + intro_clip.duration)

    # Remove green screen from the intro video
    intro_clip_no_bg = remove_greenscreen(intro_clip)

    
    # Resize intro clip to match height of random clip
    intro_clip_no_bg = intro_clip_no_bg.resize(height=random_clip.h)

    # Centering the intro video without scaling
    intro_clip_no_bg = intro_clip_no_bg.set_position(('center', 'center'))

    # Composite the clips
    final_clip = CompositeVideoClip([random_clip, intro_clip_no_bg.set_duration(random_clip.duration)])

    # Crop final clip to reels aspect ratio (9:16) and full HD resolution (1080p)
    final_clip = crop_to_reels_aspect_ratio(final_clip)

    # Write the final video to file
    final_clip.write_videofile(output_file, codec='libx264', audio_codec='aac')

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    intro_path = os.path.join(base_dir, 'video intro', 'video_intro_falling.mp4')
    random_videos_dir = os.path.join(base_dir, 'final story', 'minecraft videos')
    output_file = os.path.join(base_dir, 'video intro', 'final_intro.mp4')

    main(intro_path, random_videos_dir, output_file)