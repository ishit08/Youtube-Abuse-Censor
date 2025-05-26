# YouTube Abuse Censor

A modern Flask web application that allows you to upload a video, automatically detects and censors abusive language in the audio, and returns a censored video. The app features a beautiful, responsive UI with light/dark themes and a funky background.

## Features
- Upload any video file (mp4, mov, etc.)
- Automatic speech-to-text using Whisper
- Detects and censors abusive words in multiple languages
- Returns a video with beeps over abusive words
- Modern, responsive UI with theme toggle
- Funky animated card background

## Demo
![Screenshot](Screenshot 1.png, Screenshot 2.png)

## Getting Started

### Prerequisites
- Python 3.8+
- [ffmpeg](https://ffmpeg.org/) installed and in your PATH

### Installation
1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/youtube-abuse-censor.git
   cd youtube-abuse-censor
   ```
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the App
```bash
python app.py
```
Visit [http://localhost:5000](http://localhost:5000) in your browser.

## Usage
1. Upload a video file using the web interface.
2. Wait for processing (progress shown).
3. Download your censored video.

## Project Structure
- `app.py` - Main Flask backend
- `templates/index.html` - Frontend UI
- `uploads/` - Temporary upload storage (auto-ignored by git)
- `venv/` - Virtual environment (auto-ignored by git)

## License
MIT # Youtube-Abuse-Censor
# Youtube-Abuse-Censor
