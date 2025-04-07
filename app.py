from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import speech_recognition as sr
import pyttsx3
import pywhatkit
import datetime
import wikipedia
import pyjokes
import threading
import time
import re
import webbrowser
import logging
from queue import Queue
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, async_mode='threading', logger=True, engineio_logger=True)

# Speech recognition setup
recognizer = sr.Recognizer()
recognizer.pause_threshold = 1.5
recognizer.energy_threshold = 3000
recognizer.dynamic_energy_threshold = True

# Smart home state
home_state = {
    'kitchen_light': False,
    'dining_light': False,
    'living_room_light': False,
    'current_song': None,
    'background_color': {
        'kitchen': '#ffffff',
        'dining': '#ffffff',
        'living_room': '#ffffff'
    }
}

# Thread-safe TTS queue
tts_queue = Queue()

def tts_worker():
    """Background worker for text-to-speech"""
    engine = None
    while True:
        text = tts_queue.get()
        if text is None:  # Exit signal
            break
            
        try:
            if engine is None:
                engine = pyttsx3.init()
                voices = engine.getProperty('voices')
                engine.setProperty('voice', voices[1].id if len(voices) > 1 else voices[0].id)
                engine.setProperty('rate', 150)
                engine.setProperty('volume', 0.9)
            
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            logger.error(f"TTS error: {e}")
            if engine:
                try:
                    engine.stop()
                except:
                    pass
                engine = None
        finally:
            tts_queue.task_done()

# Start TTS thread
tts_thread = threading.Thread(target=tts_worker, daemon=True)
tts_thread.start()

def talk(text):
    """Convert text to speech and emit to client"""
    tts_queue.put(text)
    socketio.emit('assistant_response', {'text': text})

def take_command():
    """Listen for voice commands with improved error handling"""
    try:
        with sr.Microphone() as source:
            logger.info("Listening...")
            socketio.emit('listening_status', {'status': 'listening'})
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
            command = recognizer.recognize_google(audio).lower()
            logger.info(f"Command: {command}")
            socketio.emit('listening_status', {'status': 'processing'})
            return command
    except sr.WaitTimeoutError:
        talk("Listening timed out. Please try again.")
    except sr.UnknownValueError:
        talk("Sorry, I couldn't understand what you said.")
    except sr.RequestError as e:
        talk(f"Speech recognition service error: {str(e)}")
    except Exception as e:
        logger.error(f"Voice recognition error: {e}")
        talk("An error occurred while listening.")
    socketio.emit('listening_status', {'status': 'idle'})
    return ""

def process_command(command):
    """Process commands with enhanced functionality"""
    if not command:
        return
    
    logger.info(f"Processing command: {command}")
    
    # Light control with advanced pattern matching
    light_commands = {
        'kitchen': 'kitchen_light',
        'dining': 'dining_light',
        'living room': 'living_room_light',
        'livingroom': 'living_room_light'
    }
    
    # All lights control
    if 'all lights' in command:
        new_state = 'on' in command
        response = f"Turning {'on' if new_state else 'off'} all lights"
        for light_key in ['kitchen_light', 'dining_light', 'living_room_light']:
            home_state[light_key] = new_state
        talk(response)
        socketio.emit('update_lights', home_state)
        return
    
    # Individual light control
    for light_name, light_key in light_commands.items():
        if light_name in command:
            if 'on' in command:
                if not home_state[light_key]:
                    home_state[light_key] = True
                    talk(f"Turning on {light_name} light")
                    socketio.emit('update_lights', home_state)
                else:
                    talk(f"The {light_name} light is already on")
            elif 'off' in command:
                if home_state[light_key]:
                    home_state[light_key] = False
                    talk(f"Turning off {light_name} light")
                    socketio.emit('update_lights', home_state)
                else:
                    talk(f"The {light_name} light is already off")
            return
    
    # Additional features
    if 'play' in command:
        song = command.replace('play', '').strip()
        if song:
            home_state['current_song'] = song
            talk(f"Playing {song} on YouTube")
            socketio.emit('play_youtube', {'song': song})
            try:
                pywhatkit.playonyt(song)
            except Exception as e:
                logger.error(f"YouTube error: {e}")
                talk("Sorry, I couldn't play that song")
    
    elif 'time' in command:
        current_time = datetime.datetime.now().strftime('%I:%M %p')
        talk(f"The current time is {current_time}")
    
    elif 'joke' in command:
        joke = pyjokes.get_joke()
        talk(f"Here's a joke: {joke}")
    
    else:
        talk("I'm not sure how to handle that command. Try 'turn on kitchen light' or 'play music'")

def voice_command_loop():
    """Background thread for voice commands"""
    while True:
        command = take_command()
        if command:
            process_command(command)
        time.sleep(0.5)

@app.route('/')
def index():
    return render_template('index.html', initial_state=home_state)

@app.route('/command', methods=['POST'])
def handle_command():
    command = request.json.get('command', '').lower()
    process_command(command)
    return jsonify({'status': 'success'})

@socketio.on('connect')
def handle_connect():
    emit('update_lights', home_state)
    emit('update_all_backgrounds', home_state['background_color'])

def open_browser():
    """Open the default browser to the app URL"""
    time.sleep(1)
    webbrowser.open('http://localhost:5000')

if __name__ == '__main__':
    # Start voice command thread
    voice_thread = threading.Thread(target=voice_command_loop, daemon=True)
    voice_thread.start()
    
    # Start browser thread
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    try:
        socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False)
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        tts_queue.put(None)
        tts_thread.join()