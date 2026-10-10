# MyCode - Video Production Pipeline

Automated video production pipeline for creating faceless YouTube/TikTok videos from Reddit stories.

## Features

- **Story Sourcing**: Fetches trending stories from Reddit
- **Script Generation**: Uses AI (Gemini) to generate engaging video scripts
- **Text-to-Speech**: Converts scripts to natural-sounding audio
- **Video Assembly**: Combines audio, visuals, subtitles, and effects
- **Thumbnail Generation**: Creates eye-catching thumbnails
- **Multi-platform Upload**: Uploads to YouTube and TikTok

## Pipeline

```
Reddit → Script (Gemini) → TTS → Subtitles → Video Assembly → Thumbnail → Upload
```

## Setup

1. Copy `upload.config.example.json` to `upload.config.json` and fill in your API keys
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   npm install
   ```
3. Configure YouTube API credentials in `upload.config.json`

## Files

| File | Description |
|------|-------------|
| `main.py` | Main pipeline orchestrator |
| `reddit_stories.py` | Reddit story fetching |
| `generate_script.py` | AI script generation |
| `text_to_speech.py` | TTS conversion |
| `transcriber.py` | Audio transcription |
| `final_video_output.py` | Video rendering |
| `thumbnail.py` | Thumbnail generation |
| `upload_youtube.js` | YouTube upload via Puppeteer |
| `upload_tiktok.py` | TikTok upload |

## Configuration

See `upload.config.example.json` for required API keys:
- YouTube Data API v3
- Google Generative AI (Gemini)
- TikTok API (optional)

## License

MIT