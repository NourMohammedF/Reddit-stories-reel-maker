import sys
import subprocess
from pathlib import Path

# Get the base directory of the script
base_dir = Path(__file__).parent.absolute()

# HARDCODED: ImageMagick location (adjust if needed)
imagemagick_base = Path("E:/My Code/libraries/video_intro")

venv_dir = base_dir / 'libraries' / 'video_intro'
venv_python = venv_dir / 'Scripts' / 'python.exe'  # Windows

def is_venv_active():
    """Check if we're running in the virtual environment"""
    return sys.prefix == str(venv_dir)

def restart_in_venv():
    """Restart the script using the virtual environment Python"""
    if not venv_python.exists():
        print(f"ERROR: Virtual environment not found at {venv_dir}")
        print("Please create and set up the virtual environment first.")
        sys.exit(1)
    
    print(f"Activating virtual environment from {venv_dir}...")
    # Run the script again using venv's Python
    result = subprocess.run([str(venv_python), __file__] + sys.argv[1:])
    sys.exit(result.returncode)

# Main activation logic
if not is_venv_active():
    restart_in_venv()

# ============ YOUR ORIGINAL CODE STARTS HERE ============
print("Running in virtual environment!")

from pydub import AudioSegment
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, vfx, AudioFileClip
from moviepy.config import change_settings

# Specify the full path to magick.exe - MUST BE STRING
IMAGEMAGICK_BINARY = str(imagemagick_base / 'ImageMagick-7.1.1-Q16-HDRI' / 'magick.exe')

# Verify the path exists
if not Path(IMAGEMAGICK_BINARY).exists():
    print(f"ERROR: ImageMagick not found at {IMAGEMAGICK_BINARY}")
    sys.exit(1)

print(f"Using ImageMagick at: {IMAGEMAGICK_BINARY}")

# Update MoviePy's settings
change_settings({"IMAGEMAGICK_BINARY": IMAGEMAGICK_BINARY})

# File paths
title_path = base_dir / 'reddit stories' / 'title.txt'
voice_path = base_dir / 'text to speech' / 'title_voice.wav'
output_path = base_dir / 'video intro' / 'video_intro.mp4'
video_dir = base_dir / 'video intro' / 'tell_me'

try:
    # Read title text from file
    with open(title_path, "r", encoding="utf-8") as file:
        title_text = file.read().strip()

    # Load audio
    voice = AudioSegment.from_file(voice_path)

    # Set a constant font size
    fontsize = 35
    interline = 5
    align = 'west'
    max_chars_per_line = 45

    # Split the title_text into lines to handle text wrapping
    words = title_text.split()
    text_lines = []
    current_line = ""

    for word in words:
        if len(current_line) + len(word) + 1 <= max_chars_per_line:
            current_line += " " + word
        else:
            text_lines.append(current_line.strip())
            current_line = word

    # Append the last line
    if current_line:
        text_lines.append(current_line.strip())

    # Calculate the number of lines
    num_lines = len(text_lines)

    # Select the appropriate video based on the number of lines
    video_filename = f"{num_lines}.mp4"
    video_path = video_dir / video_filename

    if not video_path.exists():
        raise FileNotFoundError(f"Video file for {num_lines} lines not found: {video_path}")

    # Load video
    video = VideoFileClip(str(video_path))

    # Set video duration to match audio duration
    video = video.set_duration(len(voice) / 1000.0)

    # Create the TextClip with the appropriate settings
    text_clip = TextClip('\n'.join(text_lines), fontsize=fontsize, font='Comic-Sans-MS-Bold', 
                         color='#292929', align=align, interline=interline)

    # Position the text at the west (left) side of the video
    x_position = int(video.w * 0.13)  # Offset from the left edge
    y_center = (video.h - text_clip.h) // 2.02

    # Create the final TextClip with west alignment
    title_clip = (text_clip
                  .set_position((x_position, y_center))
                  .set_duration(len(voice) / 1000.0)
                  .crossfadein(1.1))  # Pop-up effect

    # Composite title onto video
    final_video = CompositeVideoClip([video, title_clip])

    # Add audio to final video
    final_video = final_video.set_audio(AudioFileClip(str(voice_path)))

    # Save the final video
    final_video.write_videofile(str(output_path), codec='libx264', audio_codec='aac', fps=video.fps)
    
    print(f"\nVideo successfully created at: {output_path}")

except Exception as e:
    print(f"Error occurred: {e}")
    import traceback
    traceback.print_exc()