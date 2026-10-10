import os
import sys
import subprocess
from pathlib import Path

# Get the base directory (My Code folder)
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR  # This IS "My Code"

# Define all paths relative to BASE_DIR
ENV_DIR = BASE_DIR / "libraries" / "whisper_env"
ENV_ACTIVATE = ENV_DIR / "Scripts" / "activate"
MODEL_DIR = BASE_DIR / "libraries" / "whisper_env" / "whisper"  # Local model directory
INPUT_DIRECTORY = BASE_DIR / "text to speech"
OUTPUT_DIRECTORY = BASE_DIR / "transcriber"

STORY_VOICE_FILE = "story_voice.wav"
TITLE_VOICE_FILE = "title_voice.wav"

# Auto-activate environment if not already active
if "whisper_env" not in sys.prefix and "VENV_ACTIVATED" not in os.environ:
    print("Activating virtual environment...")
    os.environ["VENV_ACTIVATED"] = "1"  # Prevent infinite loop
    
    # Use the Python executable from the virtual environment directly
    venv_python = ENV_DIR / "Scripts" / "python.exe"
    script_path = Path(__file__).resolve()
    
    if venv_python.exists():
        subprocess.call([str(venv_python), str(script_path)])
    else:
        print(f"❌ Virtual environment not found at: {ENV_DIR}")
        print("Please run setup first to create the virtual environment.")
    sys.exit()

# === NOW WE'RE IN THE VIRTUAL ENVIRONMENT ===
print("✅ Running in virtual environment")
print(f"📂 Python executable: {sys.executable}")
print("=" * 50)

import warnings
warnings.filterwarnings("ignore", message="Failed to launch Triton kernels")
import whisper
import torch
import datetime

def format_time(milliseconds):
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

def transcribe_wav_to_srt(input_wav, output_srt):
    # Load Whisper model on GPU if available
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    # Set download root to use local model directory
    os.environ["XDG_CACHE_HOME"] = str(MODEL_DIR.parent)
    
    # Load model from local directory
    model = whisper.load_model("medium", device=device, download_root=str(MODEL_DIR))

    # Transcribe the WAV file with word timestamps
    result = model.transcribe(input_wav, word_timestamps=True, language="en")

    if 'segments' not in result:
        print(f"Transcription error: No segments found in {input_wav}")
        return

    words = []
    for segment in result['segments']:
        if 'words' in segment:
            words.extend(segment['words'])

    with open(output_srt, 'w', encoding='utf-8') as srt_file:
        i = 1
        j = 0
        while j < len(words):
            word = words[j]
            start_time = format_time(word['start'] * 1000)
            text = word['word']

            if len(word['word'].strip()) < 3 and j + 1 < len(words):
                next_word = words[j + 1]
                text += " " + next_word['word']
                j += 1
                word = next_word

            if j < len(words) - 1:
                end_time = format_time(words[j + 1]['start'] * 1000)
            else:
                end_time = format_time(word['end'] * 1000)

            srt_file.write(f"{i}\n{start_time} --> {end_time}\n{text.strip()}\n\n")
            i += 1
            j += 1

    print(f"Transcription completed successfully for {input_wav}")

def main():
    # Display paths for verification
    print("📂 Working Directory Structure:")
    print(f"   Base Directory: {BASE_DIR}")
    print(f"   Script Location: {SCRIPT_DIR}")
    print(f"   Model Directory: {MODEL_DIR}")
    print(f"   Input Directory: {INPUT_DIRECTORY}")
    print(f"   Output Directory: {OUTPUT_DIRECTORY}")
    print("=" * 50)
    
    # Create directories if they don't exist
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    
    # Transcribe story voice
    story_input = INPUT_DIRECTORY / STORY_VOICE_FILE
    story_output = OUTPUT_DIRECTORY / "story_sub.srt"
    
    if story_input.exists():
        print(f"🎙️  Transcribing story voice...")
        transcribe_wav_to_srt(str(story_input), str(story_output))
    else:
        print(f"❌ Story voice file not found: {story_input}")
    
    print("-" * 50)
    
    # Transcribe title voice
    title_input = INPUT_DIRECTORY / TITLE_VOICE_FILE
    title_output = OUTPUT_DIRECTORY / "title_sub.srt"
    
    if title_input.exists():
        print(f"🎙️  Transcribing title voice...")
        transcribe_wav_to_srt(str(title_input), str(title_output))
    else:
        print(f"❌ Title voice file not found: {title_input}")
    
    print("=" * 50)
    print("🎉 TRANSCRIPTION COMPLETE!")
    print("=" * 50)
    print("📁 Output files:")
    print(f"   Story subtitle: {story_output}")
    print(f"   Title subtitle: {title_output}")

if __name__ == "__main__":
    main()