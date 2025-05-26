import os
from flask import Flask, render_template, request, send_file
import whisper
import ffmpeg
from pydub import AudioSegment
from pydub.generators import Sine
import tempfile
import shutil
import traceback
import string
import subprocess
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['PROPAGATE_EXCEPTIONS'] = True
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create uploads directory if it doesn't exist
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# List of Hindi abusive words (to be expanded)
ABUSIVE_WORDS = [
    # मादरचोद variations
    'madarchod', 'मादरचोद', 'मादर चोद', 'मादरचोद', 'मादर चोद', 'मादरचोद', 'मादर चोद',
    'madar', 'मादर', 'मादर', 'मादर',
    'chod', 'चोद', 'चोद', 'चोद',
    'madar chod', 'मादर चोद',
    'madar chod', 'मादर चोद',
    
    # बहनचोद variations
    'behanchod', 'बहनचोद', 'बहन चोद', 'बहनचोद', 'बहन चोद',
    'behen', 'बहन', 'बहन', 'बहन',
    'behen chod', 'बहन चोद',
    'behenchod', 'बहनचोद',
    
    # चूतिया variations
    'chutiya', 'चूतिया', 'चूतिया', 'चूतिया', 'चतय', 'चूतीया', 'चूतिय', 'चूतीय', 'चुटी',
    'chuti', 'चूती', 'चूती',
    'chut', 'चूत', 'चूत',
    'chutiya', 'चूतिया',
    
    # भोसडीके variations
    'bhosdike', 'भोसडीके', 'भोसडी के', 'भोसडीके',
    'bhosdi', 'भोसडी', 'भोसडी',
    'bhosdi ke', 'भोसडी के',
    'bhosdike', 'भोसडीके',
    
    # रंडी variations
    'randi', 'रंडी', 'रंडी',
    'rand', 'रंड',
    'randi', 'रंडी',
    
    # कुत्ते variations
    'kutte', 'कुत्ते', 'कुत्ते',
    'kutta', 'कुत्ता',
    'kutte', 'कुत्ते',
    
    # हरामी variations
    'harami', 'हरामी', 'हरामी',
    'harami', 'हरामी',
    
    # साला variations
    'saala', 'साला', 'साला',
    'sala', 'साला',
    'saala', 'साला',
    
    # गांडू variations
    'gaandu', 'गांडू', 'गांडू',
    'gandu', 'गंडू',
    'gaandu', 'गांडू',
    
    # लंड variations
    'lund', 'लंड', 'लंड',
    'loda', 'लौड़ा', 'लौड़ा',
    'lund', 'लंड',
    
    # बहन के लोडे variations
    'bhen ke lode', 'बहन के लोडे', 'बहन के लोडे',
    'bhen ke', 'बहन के',
    'lode', 'लोडे',
    'bhen ke lode', 'बहन के लोडे',
    
    # चोदू variations
    'chodu', 'चोदू', 'चोदू',
    'chodu', 'चोदू',
    
    # माँ के लौड़े variations
    'maa ke laude', 'माँ के लौड़े', 'माँ के लौड़े',
    'maa ke', 'माँ के',
    'laude', 'लौड़े',
    'maa ke laude', 'माँ के लौड़े',
    
    # गांड मार variations
    'gand mar', 'गांड मार', 'गांड मार',
    'gand', 'गांड',
    'gand mar', 'गांड मार',
    
    # छिनाल variations
    'chinal', 'छिनाल', 'छिनाल',
    'chinal', 'छिनाल',
    
    # चूस ले variations
    'chus le', 'चूस ले', 'चूस ले',
    'chus', 'चूस',
    'chus le', 'चूस ले',
    
    # Additional variations
    'madar', 'मादर',
    'chod', 'चोद',
    'bhosdi', 'भोसडी',
    'randi', 'रंडी',
    'kutta', 'कुत्ता',
    'harami', 'हरामी',
    'saala', 'साला',
    'gaandu', 'गांडू',
    'lund', 'लंड',
    'loda', 'लौड़ा',
    'chutiya', 'चूतिया',
    'chuti', 'चूती',
    'chut', 'चूत',
    'bhosdike', 'भोसडीके',
    'rand', 'रंड',
    'kutte', 'कुत्ते',
    'gandu', 'गंडू',
    'lode', 'लोडे',
    'chodu', 'चोदू',
    'laude', 'लौड़े',
    'gand', 'गांड',
    'chinal', 'छिनाल',
    'chus', 'चूस'
]

def levenshtein(a, b):
    if len(a) < len(b):
        return levenshtein(b, a)
    if len(b) == 0:
        return len(a)
    previous_row = range(len(b) + 1)
    for i, ca in enumerate(a):
        current_row = [i + 1]
        for j, cb in enumerate(b):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (ca != cb)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

@app.route('/')
def index():
    try:
        logger.info("Rendering index page")
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index: {str(e)}")
        return f"Error: {str(e)}", 500

@app.route('/upload', methods=['POST'])
def upload_video():
    logger.info('--- upload_video called ---')
    try:
        if 'video' not in request.files:
            logger.error('No video file uploaded')
            return 'No video file uploaded', 400
        
        video_file = request.files['video']
        if video_file.filename == '':
            logger.error('No selected file')
            return 'No selected file', 400

        logger.info('Creating temporary directory...')
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = os.path.join(temp_dir, 'input.mp4')
            video_file.save(video_path)
            logger.info(f'Saved uploaded video to {video_path}')

            try:
                logger.info('Extracting audio from video...')
                audio_path = os.path.join(temp_dir, 'audio.wav')
                ffmpeg.input(video_path).output(audio_path).run()
                logger.info(f'Audio extracted to {audio_path}')

                logger.info('Loading Whisper model...')
                model = whisper.load_model("medium")
                logger.info('Model loaded')

                logger.info('Transcribing audio...')
                result = model.transcribe(audio_path, language="hi", word_timestamps=True, verbose=False)
                logger.info('Transcription complete')

                logger.info('Full transcript:')
                logger.info(result.get('text', ''))

                logger.info('Words detected by Whisper:')
                for segment in result.get('segments', []):
                    for word_info in segment.get('words', []):
                        logger.info(repr(word_info['word']))

                # Load audio first
                logger.info('Loading audio with pydub...')
                audio = AudioSegment.from_wav(audio_path)
                duration_ms = len(audio)
                logger.info(f'Audio loaded, duration: {duration_ms} ms')

                # Improved matching: handle multi-word abusive phrases split across word boundaries
                segments = result.get('segments', [])
                words_with_times = []
                for segment in segments:
                    for word_info in segment.get('words', []):
                        word = word_info['word'].strip().lower()
                        # Remove punctuation but keep Hindi characters
                        word = ''.join(c for c in word if c.isalnum() or c.isspace())
                        if word:  # Only add non-empty words
                            words_with_times.append({
                                'word': word,
                                'start': word_info['start'],
                                'end': word_info['end']
                            })

                # Join all words to a string for phrase search
                joined_words = ' '.join([w['word'] for w in words_with_times])
                logger.info('Joined words:')
                logger.info(joined_words)

                censored_ranges = []
                def strict_match(a, b):
                    # For very short words (2-3 chars), require exact match
                    if len(a) <= 3 or len(b) <= 3:
                        return a == b
                    
                    # For medium length words (4-6 chars), allow 1 character difference
                    if len(a) <= 6 or len(b) <= 6:
                        return levenshtein(a, b) <= 1
                    
                    # For longer words, allow 2 character differences
                    return levenshtein(a, b) <= 2

                for abuse in ABUSIVE_WORDS:
                    abuse_clean = abuse.strip().lower()
                    abuse_clean = ''.join(c for c in abuse_clean if c.isalnum() or c.isspace())
                    abuse_tokens = abuse_clean.split()
                    max_window = len(abuse_tokens) + 1
                    logger.info(f'Checking for abusive word: {abuse_clean}')
                    for window_size in range(1, max_window+1):
                        for i in range(len(words_with_times) - window_size + 1):
                            window = words_with_times[i:i+window_size]
                            window_words = [w['word'] for w in window]
                            window_text = ' '.join(window_words)
                            joined_window = ''.join(window_words)
                            joined_abuse = ''.join(abuse_tokens)
                            if strict_match(joined_window, joined_abuse):
                                start_ms = int(window[0]['start'] * 1000)
                                end_ms = int(window[-1]['end'] * 1000)
                                start_ms = max(0, start_ms - 100)
                                end_ms = min(duration_ms, end_ms + 100)
                                censored_ranges.append((start_ms, end_ms))
                                logger.info(f'Match found! Beep for: {window_text} (matched: {abuse_clean})')

                # Sort and merge overlapping ranges
                if censored_ranges:
                    censored_ranges.sort(key=lambda x: x[0])
                    merged_ranges = []
                    current_start, current_end = censored_ranges[0]
                    
                    for start, end in censored_ranges[1:]:
                        if start <= current_end:
                            current_end = max(current_end, end)
                        else:
                            merged_ranges.append((current_start, current_end))
                            current_start, current_end = start, end
                    merged_ranges.append((current_start, current_end))
                    censored_ranges = merged_ranges

                logger.info('Censored ranges:')
                logger.info(censored_ranges)

                logger.info('Creating beep...')
                # Create a louder, higher-pitched beep (2000Hz, 1000ms duration, +12dB gain)
                beep = Sine(2000).to_audio_segment(duration=1000).apply_gain(+12)
                # Add fade in/out to make it less jarring
                beep = beep.fade_in(50).fade_out(50)
                logger.info('Beep type:')
                logger.info(type(beep))

                censored_audio = AudioSegment.empty()
                last_end = 0
                for start_ms, end_ms in censored_ranges:
                    if start_ms > last_end:
                        censored_audio += audio[last_end:start_ms]
                    # Ensure beep duration matches the censored segment
                    beep_duration = end_ms - start_ms
                    beep_segment = beep[:beep_duration] if beep_duration < len(beep) else beep * ((beep_duration//len(beep))+1)
                    beep_segment = beep_segment[:beep_duration]  # Trim to exact duration
                    # Add a small silence before and after beep
                    beep_segment = AudioSegment.silent(duration=50) + beep_segment + AudioSegment.silent(duration=50)
                    censored_audio += beep_segment
                    last_end = end_ms
                censored_audio += audio[last_end:]

                # Ensure censored audio matches original duration
                if len(censored_audio) > len(audio):
                    censored_audio = censored_audio[:len(audio)]
                elif len(censored_audio) < len(audio):
                    censored_audio = censored_audio + AudioSegment.silent(duration=len(audio) - len(censored_audio))

                logger.info('Censored audio type:')
                logger.info(type(censored_audio))
                logger.info('Original audio duration:')
                logger.info(len(audio))
                logger.info('Censored audio duration:')
                logger.info(len(censored_audio))

                censored_audio_path = os.path.join(temp_dir, 'censored_audio.wav')
                logger.info('Exporting censored audio...')
                censored_audio.export(censored_audio_path, format='wav')
                logger.info(f'Exported censored audio to {censored_audio_path}')

                # Merge censored audio back to video
                output_video_path = os.path.join(temp_dir, 'output.mp4')
                logger.info('Merging censored audio with video...')
                
                # Use FFmpeg command-line syntax
                cmd = [
                    'ffmpeg',
                    '-i', video_path,
                    '-i', censored_audio_path,
                    '-c:v', 'copy',
                    '-c:a', 'aac',
                    '-map', '0:v',
                    '-map', '1:a',
                    '-shortest',  # Ensure output duration matches shortest input
                    '-y',
                    output_video_path
                ]
                subprocess.run(cmd, check=True)
                logger.info(f'Merged video ready: {output_video_path}')

                return send_file(output_video_path, as_attachment=True)

            except Exception as e:
                logger.error(f"Error processing video: {str(e)}")
                logger.error(traceback.format_exc())
                return f'Error processing video: {str(e)}', 500

    except Exception as e:
        logger.error(f"Error in upload_video: {str(e)}")
        logger.error(traceback.format_exc())
        return f'Error: {str(e)}', 500

if __name__ == '__main__':
    try:
        logger.info("Starting Flask app...")
        app.run(debug=True, host='0.0.0.0', port=5001)
    except Exception as e:
        logger.error(f"Error starting Flask app: {str(e)}")
        logger.error(traceback.format_exc()) 