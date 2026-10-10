import subprocess
import os

base_path = os.path.dirname(os.path.abspath(__file__))

files_to_run = [
    'text_to_speech.py',
    'transcriber.py',
    'video_intro.py',
    'falling_effect.py',
    'final_intro.py',
    'final_story.py',
    'final_video_output.py'
]

for file in files_to_run:
    file_path = os.path.join(base_path, file)
    print(f"Executing: {file}")
    print("=" * 50)
    
    try:
        subprocess.run(['python', file_path], check=True)
        print(f"✅ {file} completed successfully\n")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error executing {file}: {e}")
        print("Stopping execution due to error.\n")
        break
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
        print("Stopping execution due to missing file.\n")
        break

print("=" * 50)
print("🎉 All scripts executed!")