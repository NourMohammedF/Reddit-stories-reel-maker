import os, sys, subprocess, shlex, re
import random
from pathlib import Path

# Get the base directory (My Code folder)
# The script is directly in "My Code" folder
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR  # This IS "My Code"

# Define all paths relative to BASE_DIR
ENV_DIR = BASE_DIR / "libraries" / "chatterbox_env"
ENV_ACTIVATE = ENV_DIR / "Scripts" / "activate"
MODEL_CACHE = ENV_DIR / "chatterbox_model"
CLONE_MODELS_DIR = ENV_DIR / "clone_models"
STORY_TXT = BASE_DIR / "reddit stories" / "story.txt"
TITLE_TXT = BASE_DIR / "reddit stories" / "title.txt"
STORY_OUT = BASE_DIR / "text to speech" / "story_voice.wav"
TITLE_OUT = BASE_DIR / "text to speech" / "title_voice.wav"

# Auto-activate environment if not already active
if "chatterbox_env" not in sys.prefix and "VENV_ACTIVATED" not in os.environ:
    print("Activating virtual environment...")
    os.environ["VENV_ACTIVATED"] = "1"  # Prevent infinite loop
    
    # Use the Python executable from the virtual environment directly
    venv_python = ENV_DIR / "Scripts" / "python.exe"
    script_path = Path(__file__).resolve()
    
    if venv_python.exists():
        subprocess.call([str(venv_python), str(script_path)])
    else:
        print(f"❌ Virtual environment not found at: {ENV_DIR}")
    sys.exit()

import numpy as np
import torch
import scipy.io.wavfile
import librosa
import soundfile as sf

# === SET ENVIRONMENT VARIABLES BEFORE IMPORTING CHATTERBOX ===
# Set multiple cache environment variables to ensure model uses custom path
os.environ['HUGGINGFACE_HUB_CACHE'] = str(MODEL_CACHE)
os.environ['TRANSFORMERS_CACHE'] = str(MODEL_CACHE)
os.environ['HF_HOME'] = str(MODEL_CACHE)
os.environ['HF_DATASETS_CACHE'] = str(MODEL_CACHE)

# Suppress warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# Now import Chatterbox after setting environment variables
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Import and disable tqdm globally
try:
    from tqdm import tqdm
    # Create a dummy tqdm that does nothing
    def dummy_tqdm(*args, **kwargs):
        class Dummy:
            def __init__(self, *args, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def update(self, n=1):
                pass
            def close(self):
                pass
        return Dummy()
    
    # Replace tqdm with our dummy
    tqdm = dummy_tqdm
except ImportError:
    pass

from chatterbox.tts import ChatterboxTTS

def ensure_dir_exists(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)

def read_text(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return None

def save_wav(filename, audio_np, sr):
    # Use soundfile for better quality WAV writing
    sf.write(filename, audio_np, sr, subtype='PCM_16')
    print(f"Saved: {filename}")

def get_random_voice_model(clone_models_dir):
    """Randomly select a voice model from available audio files"""
    # Supported audio formats
    audio_extensions = {'.mp3', '.wav', '.flac', '.m4a', '.ogg', '.aac'}
    
    try:
        # Get all audio files in the directory
        audio_files = []
        for file in os.listdir(clone_models_dir):
            if any(file.lower().endswith(ext) for ext in audio_extensions):
                audio_files.append(file)
        
        if not audio_files:
            print(f"❌ No audio files found in {clone_models_dir}")
            print(f"Supported formats: {', '.join(audio_extensions)}")
            return None
        
        # Randomly select a voice model
        random_voice = random.choice(audio_files)
        full_path = Path(clone_models_dir) / random_voice
        
        print(f"🎲 Randomly selected voice: {random_voice}")
        print(f"📁 Total voice models available: {len(audio_files)}")
        
        return str(full_path)
        
    except Exception as e:
        print(f"❌ Error selecting voice model: {e}")
        return None

def validate_voice_clone(path):
    """Basic voice clone validation"""
    try:
        y, sr = librosa.load(path, sr=None, duration=10)  # Only check first 10 seconds
        duration = len(y) / sr
        
        print(f"📊 Voice clone analysis:")
        print(f"   Duration: {duration:.2f} seconds")
        
        # Basic criteria
        if duration < 2.0:
            print("❌ Voice sample too short (<2 seconds)")
            return False
        
        # Check audio quality
        rms_energy = np.sqrt(np.mean(y**2))
        print(f"   Loudness: {rms_energy:.3f} RMS")
        
        if rms_energy < 0.01:
            print("⚠️  Very quiet - may affect quality")
        
        print("   ✅ Voice clone validated")
        return True
        
    except Exception as e:
        print(f"❌ Voice clone validation error: {e}")
        return False

def preprocess_text(text, is_title=False):
    """Enhanced text preprocessing for optimal TTS results"""
    
    # Remove unwanted characters but keep meaningful punctuation
    text = re.sub(r'[^\w\s\.\,\!\?\-\:\;\'\"\(\)]', '', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Handle common text patterns for better pronunciation
    text = re.sub(r'(\d+)', lambda x: pronounce_number(x.group(1)), text)
    
    # Enhanced text cleaning for TTS
    text = re.sub(r'\.{2,}', '.', text)  # Replace multiple dots with single dot
    text = re.sub(r'\!{2,}', '!', text)  # Replace multiple exclamations
    text = re.sub(r'\?{2,}', '?', text)  # Replace multiple questions
    
    # For titles, skip strategic pause insertion and sentence splitting
    if is_title:
        # Just ensure proper spacing after punctuation for titles
        text = re.sub(r'\s*([\.\,\!\?\:])\s*', r'\1 ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    # For story text: Add strategic pauses and improve sentence structure
    sentences = re.split(r'[\.\!\?]', text)
    processed_sentences = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        # Handle long sentences by adding natural breaks
        if len(sentence) > 80:
            words = sentence.split()
            if len(words) > 12:
                # Find natural break points (commas, conjunctions)
                break_points = []
                for i, word in enumerate(words[:-1]):
                    if word.lower() in ['and', 'but', 'or', 'however', 'therefore', 'meanwhile', 'although', 'while']:
                        break_points.append(i)
                
                if break_points:
                    # Use the middle break point
                    mid_break = break_points[len(break_points) // 2]
                    sentence = ' '.join(words[:mid_break+1]) + ', ' + ' '.join(words[mid_break+1:])
        
        processed_sentences.append(sentence)
    
    result = '. '.join(processed_sentences)
    
    # Ensure proper spacing after punctuation
    result = re.sub(r'\s*([\.\,\!\?\:])\s*', r'\1 ', result)
    
    # Final cleanup
    result = re.sub(r'\s+', ' ', result).strip()
    
    return result

def pronounce_number(num_str):
    """Convert numbers to spoken form for better TTS"""
    try:
        num = int(num_str)
        if num < 100:
            return num_str  # Keep small numbers as digits
        else:
            # For larger numbers, add commas for better pronunciation
            return f"{num:,}"
    except:
        return num_str

def generate_long_text_audio(text, out_path, model, voice_clone, desc, max_length=120):
    """Enhanced chunking with overlap for smoother transitions"""
    sentences = re.split(r'[\.\!\?]', text)
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        if len(current_chunk) + len(sentence) < max_length:
            current_chunk += sentence + ". "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + ". "
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    print(f"📝 Split {desc} into {len(chunks)} chunks for optimal quality...")
    
    # Generate each chunk with quality settings
    audio_chunks = []
    for i, chunk in enumerate(chunks):
        print(f"🎙️  Generating {desc} chunk {i+1}/{len(chunks)}...")
        
        # Use different quality settings based on content type
        if desc == "title":
            # Titles get extra expressiveness and clarity
            exaggeration = 0.85
            cfg_weight = 0.85
            temperature = 0.6
        else:
            # Story gets balanced settings for natural flow
            exaggeration = 0.75
            cfg_weight = 0.8
            temperature = 0.7
        
        # Suppress warnings during generation
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            wav_tensor = model.generate(
                chunk,
                audio_prompt_path=voice_clone,
                exaggeration=exaggeration,
                cfg_weight=cfg_weight,
                temperature=temperature
            )
        chunk_audio = wav_tensor.cpu().numpy().flatten()
        
        # Enhanced fade in/out for professional quality
        fade_duration = min(1024, len(chunk_audio) // 8)
        if fade_duration > 0:
            fade_in = np.linspace(0, 1, fade_duration) ** 0.5  # Square root for smoother fade
            fade_out = np.linspace(1, 0, fade_duration) ** 0.5
            chunk_audio[:fade_duration] *= fade_in
            chunk_audio[-fade_duration:] *= fade_out
        
        audio_chunks.append(chunk_audio)
        
        # Natural pause between chunks (skip for titles)
        if i < len(chunks) - 1 and desc != "title":
            pause_samples = int(model.sr * 0.15)  # 150ms natural pause
            pause_fade = min(256, pause_samples // 4)
            if pause_fade > 0:
                pause_audio = np.zeros(pause_samples)
                # Fade the pause edges
                pause_audio[:pause_fade] = np.linspace(0, 0, pause_fade)
                pause_audio[-pause_fade:] = np.linspace(0, 0, pause_fade)
                audio_chunks.append(pause_audio)
            else:
                audio_chunks.append(np.zeros(pause_samples))
    
    # Concatenate all chunks with careful normalization
    full_audio = np.concatenate(audio_chunks)
    
    # Gentle normalization to prevent clipping while maintaining dynamics
    peak = np.max(np.abs(full_audio))
    if peak > 0.9:
        full_audio = full_audio * 0.9 / peak
    
    return full_audio

def generate_audio(text, out_path, desc, model, voice_clone):
    is_title = (desc == "title")
    processed_text = preprocess_text(text, is_title=is_title)
    print(f"🎯 Generating {desc} audio ({len(processed_text)} characters)...")
    print(f"📄 Text preview: {processed_text[:80]}...")
    
    # Use more aggressive chunking for better quality on long texts
    if len(processed_text) > 150:
        print(f"📦 Using chunked generation for optimal quality...")
        wav_np = generate_long_text_audio(processed_text, out_path, model, voice_clone, desc, max_length=120)
    else:
        # Single generation with optimized settings for shorter texts
        if desc == "title":
            # Titles: more expressive, clearer articulation
            exaggeration = 0.85
            cfg_weight = 0.85
            temperature = 0.6
        else:
            # Story: natural, balanced with good expressiveness
            exaggeration = 0.75
            cfg_weight = 0.8
            temperature = 0.7
            
        print(f"⚡ Single-pass generation with quality settings...")
        
        # Suppress warnings during generation
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            wav_tensor = model.generate(
                processed_text,
                audio_prompt_path=voice_clone,  
                exaggeration=exaggeration,
                cfg_weight=cfg_weight,
                temperature=temperature
            )
        wav_np = wav_tensor.cpu().numpy().flatten()
        
        # Gentle peak normalization for single generation
        peak = np.max(np.abs(wav_np))
        if peak > 0.95:
            wav_np = wav_np * 0.95 / peak
    
    # Save with high-quality settings
    save_wav(out_path, wav_np, model.sr)

def main():
    # Suppress unnecessary warnings
    import warnings
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    
    # Display paths for verification
    print("📂 Working Directory Structure:")
    print(f"   Base Directory: {BASE_DIR}")
    print(f"   Script Location: {SCRIPT_DIR}")
    print("=" * 50)

    ensure_dir_exists(STORY_OUT)
    ensure_dir_exists(TITLE_OUT)
    
    # Get random voice model
    print("🎲 Randomly selecting voice model...")
    voice_clone = get_random_voice_model(CLONE_MODELS_DIR)
    if not voice_clone:
        print("❌ No suitable voice models found. Using fallback.")
        fallback = CLONE_MODELS_DIR / "model_1.mp3"
        voice_clone = str(fallback)

    # Basic voice clone validation
    print("📊 Validating selected voice clone...")
    if not validate_voice_clone(voice_clone):
        print("⚠️  Voice clone has some issues but proceeding anyway...")

    story_text = read_text(STORY_TXT)
    title_text = read_text(TITLE_TXT)
    if not story_text or not title_text:
        print("❌ Missing story or title text.")
        return

    print("🚀 Loading Chatterbox model with optimal settings...")
    print(f"📁 Using model cache: {MODEL_CACHE}")
    
    try:
        # Try to load model - it should now use our custom cache directory
        model = ChatterboxTTS.from_pretrained(device="cuda")
        print("✅ Model loaded successfully from custom cache!")
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return

    # Generate audio with quality-optimized parameters
    print(f"🎙️  Using voice model: {Path(voice_clone).name}")
    print("=" * 50)
    
    generate_audio(title_text, TITLE_OUT, "title", model, voice_clone)
    print("-" * 30)
    generate_audio(story_text, STORY_OUT, "story", model, voice_clone)

    print("=" * 50)
    print("🎉 HIGH-QUALITY AUDIO GENERATION COMPLETE!")
    print("=" * 50)
    print("📁 Output files:")
    print(f"   Title: {TITLE_OUT}")
    print(f"   Story: {STORY_OUT}")

if __name__ == "__main__":
    main()