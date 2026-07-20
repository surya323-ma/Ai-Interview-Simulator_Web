"""
Voice Analysis Module - Records audio, converts speech to text, and analyzes responses
"""

import threading
import queue
import time
import numpy as np
import io

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    print("Warning: SpeechRecognition not available.")

try:
    import sounddevice as sd
    from scipy.io import wavfile
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    print("Warning: sounddevice not available. Audio recording disabled.")

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("Warning: pyttsx3 not available. Text-to-speech disabled.")

class TextToSpeech:
    """Handles text-to-speech functionality."""
    
    def __init__(self):
        """Initialize TTS engine."""
        self.engine = None
        self.is_speaking = False
        
        if TTS_AVAILABLE:
            try:
                self.engine = pyttsx3.init()
                self.engine.setProperty('rate', 150)  # Speed
                self.engine.setProperty('volume', 0.9)
            except Exception as e:
                print(f"TTS initialization failed: {e}")
    
    def speak(self, text):
        """Speak the given text."""
        if self.engine is None:
            print(f"[TTS] {text}")
            return
        
        try:
            self.is_speaking = True
            self.engine.say(text)
            self.engine.runAndWait()
            self.is_speaking = False
        except Exception as e:
            print(f"TTS error: {e}")
            self.is_speaking = False
    
    def speak_async(self, text):
        """Speak text in a separate thread."""
        thread = threading.Thread(target=self.speak, args=(text,), daemon=True)
        thread.start()
        return thread


class AudioRecorder:
    """Records audio from microphone."""
    
    def __init__(self, sample_rate=16000):
        """Initialize audio recorder."""
        self.sample_rate = sample_rate
        self.is_recording = False
        self.audio_data = []
        self.audio_queue = queue.Queue()
        self.record_thread = None
        
    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for audio stream."""
        if self.is_recording:
            self.audio_queue.put(indata.copy())
    
    def start_recording(self):
        """Start recording audio."""
        if not SOUNDDEVICE_AVAILABLE:
            print("Audio recording not available")
            return False
        
        self.audio_data = []
        self.is_recording = True
        
        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype='float32',
                callback=self._audio_callback
            )
            self.stream.start()
            
            # Thread to collect audio data
            def collect_audio():
                while self.is_recording:
                    try:
                        data = self.audio_queue.get(timeout=0.1)
                        self.audio_data.append(data)
                    except queue.Empty:
                        pass
            
            self.record_thread = threading.Thread(target=collect_audio, daemon=True)
            self.record_thread.start()
            return True
            
        except Exception as e:
            print(f"Failed to start recording: {e}")
            self.is_recording = False
            return False
    
    def stop_recording(self):
        """Stop recording and return audio data."""
        self.is_recording = False
        
        if hasattr(self, 'stream'):
            self.stream.stop()
            self.stream.close()
        
        if self.record_thread:
            self.record_thread.join(timeout=1.0)
        
        if self.audio_data:
            return np.concatenate(self.audio_data, axis=0)
        return None
    
    def get_audio_level(self):
        """Get current audio level (0-100)."""
        if not self.audio_data:
            return 0
        
        recent_data = self.audio_data[-5:] if len(self.audio_data) > 5 else self.audio_data
        if recent_data:
            combined = np.concatenate(recent_data)
            rms = np.sqrt(np.mean(combined ** 2))
            # Scale to 0-100
            level = min(100, rms * 500)
            return level
        return 0


class VoiceAnalyzer:
    """Analyzes voice responses for speech-to-text and metrics."""
    
    def __init__(self):
        """Initialize voice analyzer."""
        self.recorder = AudioRecorder()
        self.tts = TextToSpeech()
        self.recognizer = sr.Recognizer() if SPEECH_RECOGNITION_AVAILABLE else None
        
        # Analysis results
        self.transcript = ""
        self.word_count = 0
        self.speaking_duration = 0
        self.pause_count = 0
        self.words_per_minute = 0
        
        # Recording state
        self.recording_start_time = None
        self.is_recording = False
    
    def speak_question(self, question):
        """Speak a question using TTS."""
        self.tts.speak_async(question)
    
    def start_recording(self):
        """Start recording user's answer."""
        self.is_recording = self.recorder.start_recording()
        self.recording_start_time = time.time()
        return self.is_recording
    
    def stop_recording(self):
        """Stop recording and analyze the response."""
        audio_data = self.recorder.stop_recording()
        self.is_recording = False
        
        if self.recording_start_time:
            self.speaking_duration = time.time() - self.recording_start_time
        
        if audio_data is not None:
            self._analyze_audio(audio_data)
        
        return self.get_analysis_results()
    
    def _analyze_audio(self, audio_data):
        """Analyze recorded audio data."""
        # Convert to int16 for speech recognition
        audio_int16 = (audio_data * 32767).astype(np.int16)
        
        # Perform speech-to-text
        self.transcript = self._speech_to_text(audio_int16)
        
        # Analyze transcript
        if self.transcript:
            words = self.transcript.split()
            self.word_count = len(words)
            
            # Calculate words per minute
            if self.speaking_duration > 0:
                self.words_per_minute = (self.word_count / self.speaking_duration) * 60
        
        # Analyze pauses (silence detection)
        self.pause_count = self._detect_pauses(audio_data)
    
    def _speech_to_text(self, audio_int16):
        """Convert audio to text using speech recognition."""
        if not SPEECH_RECOGNITION_AVAILABLE or self.recognizer is None:
            return "[Speech recognition not available]"
        
        try:
            # Create WAV file in memory
            wav_buffer = io.BytesIO()
            wavfile.write(wav_buffer, self.recorder.sample_rate, audio_int16)
            wav_buffer.seek(0)
            
            # Use speech recognition
            with sr.AudioFile(wav_buffer) as source:
                audio = self.recognizer.record(source)
            
            # Try Google's free API first
            try:
                text = self.recognizer.recognize_google(audio)
                return text
            except sr.UnknownValueError:
                return "[Could not understand audio]"
            except sr.RequestError:
                # Try offline recognition if available
                try:
                    text = self.recognizer.recognize_sphinx(audio)
                    return text
                except:
                    return "[Speech recognition unavailable]"
                
        except Exception as e:
            print(f"Speech-to-text error: {e}")
            return "[Error processing audio]"
    
    def _detect_pauses(self, audio_data, threshold=0.01, min_pause_duration=0.5):
        """Detect pauses in audio."""
        if audio_data is None or len(audio_data) == 0:
            return 0
        
        # Calculate RMS in windows
        window_size = int(self.recorder.sample_rate * 0.1)  # 100ms windows
        pause_count = 0
        pause_frames = 0
        min_pause_frames = int(min_pause_duration / 0.1)  # Convert to windows
        
        for i in range(0, len(audio_data), window_size):
            window = audio_data[i:i + window_size]
            if len(window) > 0:
                rms = np.sqrt(np.mean(window.flatten() ** 2))
                
                if rms < threshold:
                    pause_frames += 1
                else:
                    if pause_frames >= min_pause_frames:
                        pause_count += 1
                    pause_frames = 0
        
        return pause_count
    
    def get_audio_level(self):
        """Get current recording audio level."""
        return self.recorder.get_audio_level()
    
    def get_analysis_results(self):
        """Get analysis results."""
        # Determine response length category
        if self.word_count < 20:
            length_category = "Too Short"
            length_score = 30
        elif self.word_count < 50:
            length_category = "Short"
            length_score = 60
        elif self.word_count < 150:
            length_category = "Good"
            length_score = 90
        elif self.word_count < 250:
            length_category = "Detailed"
            length_score = 85
        else:
            length_category = "Too Long"
            length_score = 60
        
        # Determine speaking pace
        if self.words_per_minute < 80:
            pace_category = "Too Slow"
            pace_score = 50
        elif self.words_per_minute < 120:
            pace_category = "Measured"
            pace_score = 80
        elif self.words_per_minute < 160:
            pace_category = "Good"
            pace_score = 95
        elif self.words_per_minute < 200:
            pace_category = "Quick"
            pace_score = 75
        else:
            pace_category = "Too Fast"
            pace_score = 50
        
        # Pause analysis
        if self.pause_count == 0:
            pause_category = "Fluent"
            pause_score = 95
        elif self.pause_count <= 2:
            pause_category = "Natural"
            pause_score = 85
        elif self.pause_count <= 5:
            pause_category = "Some Hesitation"
            pause_score = 65
        else:
            pause_category = "Frequent Pauses"
            pause_score = 40
        
        return {
            'transcript': self.transcript,
            'word_count': self.word_count,
            'speaking_duration': self.speaking_duration,
            'words_per_minute': self.words_per_minute,
            'pause_count': self.pause_count,
            'length_category': length_category,
            'length_score': length_score,
            'pace_category': pace_category,
            'pace_score': pace_score,
            'pause_category': pause_category,
            'pause_score': pause_score,
            'overall_voice_score': (length_score + pace_score + pause_score) / 3
        }
    
    def reset(self):
        """Reset analyzer state."""
        self.transcript = ""
        self.word_count = 0
        self.speaking_duration = 0
        self.pause_count = 0
        self.words_per_minute = 0
