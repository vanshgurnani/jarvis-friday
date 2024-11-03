import os
from dotenv import load_dotenv
import speech_recognition as sr
import pyttsx3
import time
import re
import json
import webbrowser
import requests
from datetime import datetime, timedelta
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

load_dotenv()

WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
CUSTOM_SEARCH_API_KEY = os.getenv('CUSTOM_SEARCH_API_KEY')
SEARCH_ENGINE_ID = os.getenv('SEARCH_ENGINE_ID')

# Initialize recognizer and TTS engine
recognizer = sr.Recognizer()
engine = pyttsx3.init()

# Initialize reminders list
REMINDER_FILE = "reminders.json"

# Google Calendar API scope
SCOPES = ['https://www.googleapis.com/auth/calendar']

voice_gender = 'male'  # Default voice gender
available_voices = engine.getProperty('voices')

def set_voice(gender):
    """Set the TTS engine voice based on gender."""
    global voice_gender
    voice_gender = gender.lower()
    for voice in available_voices:
        if (voice_gender == 'male' and 'male' in voice.name.lower()) or \
           (voice_gender == 'female' and 'female' in voice.name.lower()):
            engine.setProperty('voice', voice.id)
            speak(f"Voice set to {voice.name}.")
            return
    speak("Sorry, the selected voice is not available. Default voice will be used.")
    
# Authenticate and build the Google Calendar service
def authenticate_google_calendar():
    """Authenticate the user and return the Google Calendar service."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Log the refreshed access and refresh tokens
            print("Refreshed Credentials:")
            print(f"Access Token: {creds.token}")
            print(f"Refresh Token: {creds.refresh_token}")

            # Save the refreshed credentials back to token.json
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        else:
            # Create the flow with access_type='offline' to get a refresh token
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            flow.run_local_server(port=52760, access_type='offline', prompt='consent')  # Request offline access
            creds = flow.credentials  # Get the credentials from the flow

            # Log the initial access and refresh tokens
            print("Initial Credentials:")
            print(f"Access Token: {creds.token}")
            print(f"Refresh Token: {creds.refresh_token}")

            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)


calendar_service = authenticate_google_calendar()

def speak(text):
    """Convert text to speech."""
    engine.say(text)
    engine.runAndWait()

def listen():
    """Capture voice input and return the recognized text."""
    with sr.Microphone() as source:
        print("Listening...")
        audio = recognizer.listen(source)
        try:
            command = recognizer.recognize_google(audio)
            print(f"You said: {command}")
            return command.lower()
        except sr.UnknownValueError:
            speak("Sorry, I didn't catch that.")
        except sr.RequestError:
            speak("Sorry, my speech service is down.")
    return ""

def parse_time(time_str):
    """Parse time in either 12-hour or 24-hour format and return in 24-hour format."""
    try:
        parsed_time = datetime.strptime(time_str, "%H:%M")
    except ValueError:
        try:
            parsed_time = datetime.strptime(time_str, "%I:%M %p")
        except ValueError:
            speak("Please specify the time in a valid format, like '15:30' or '12:30 pm'.")
            return None
    return parsed_time.strftime("%H:%M")

def load_reminders():
    """Load reminders from a JSON file."""
    try:
        with open(REMINDER_FILE, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_reminders():
    """Save reminders to a JSON file."""
    with open(REMINDER_FILE, "w") as file:
        json.dump(reminders, file)

reminders = load_reminders()

def add_google_calendar_event(reminder_text, reminder_time):
    """Add an event to Google Calendar for the authenticated user."""
    event_time = datetime.strptime(reminder_time, "%H:%M")
    event_start = datetime.now().replace(hour=event_time.hour, minute=event_time.minute, second=0, microsecond=0)
    event_end = event_start + timedelta(minutes=30)

    event = {
        'summary': reminder_text,
        'start': {'dateTime': event_start.isoformat(), 'timeZone': 'America/Los_Angeles'},
        'end': {'dateTime': event_end.isoformat(), 'timeZone': 'America/Los_Angeles'},
    }

    event = calendar_service.events().insert(calendarId='primary', body=event).execute()
    print(f"Event created: {event.get('htmlLink')}")
    speak(f"Google Calendar event created for {reminder_text} at {reminder_time}")

def add_reminder(reminder_text, reminder_time):
    """Schedule a reminder and add it to persistent storage and Google Calendar."""
    reminder_24_hour = parse_time(reminder_time)
    if reminder_24_hour:
        reminder = {"text": reminder_text, "time": reminder_24_hour}
        reminders.append(reminder)
        save_reminders()
        add_google_calendar_event(reminder_text, reminder_24_hour)
        speak(f"Reminder set for {reminder_24_hour} to {reminder_text}")

def trigger_reminder(reminder_text):
    """Notify the user when a reminder is due."""
    speak(f"Reminder: {reminder_text}")
    print(f"Reminder: {reminder_text}")

def check_reminders():
    """Check the system time to trigger reminders."""
    current_time = datetime.now().strftime("%H:%M")
    for reminder in reminders:
        if reminder["time"] == current_time:
            trigger_reminder(reminder["text"])
            reminders.remove(reminder)
            save_reminders()
    time.sleep(60)

def play_music(song_name):
    """Play music on YouTube by searching for the song name."""
    search_url = f"https://www.youtube.com/results?search_query={song_name.replace(' ', '+')}"
    webbrowser.open(search_url)
    speak(f"Playing {song_name} on YouTube.")

def get_weather(city_name):
    """Fetch weather data for a given city using OpenWeatherMap API."""
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={WEATHER_API_KEY}&units=metric"
    try:
        response = requests.get(url)
        response.raise_for_status()
        weather_data = response.json()
        main_weather = weather_data['weather'][0]['description']
        temp = weather_data['main']['temp']
        city = weather_data['name']
        weather_report = f"The weather in {city} is {main_weather} with a temperature of {temp}°C."
        print(weather_report)
        speak(weather_report)
    except requests.exceptions.RequestException as e:
        print("Error fetching weather data:", e)
        speak("Sorry, I couldn't fetch the weather data right now.")

def google_custom_search(search_query):
    url = f"https://www.googleapis.com/customsearch/v1?q={search_query}&key={CUSTOM_SEARCH_API_KEY}&cx={SEARCH_ENGINE_ID}"
    response = requests.get(url)
    results = response.json()
    
    # Print the full response for debugging
    print(json.dumps(results, indent=4))

    # Check if 'items' key exists in the response
    if 'items' in results and results['items']:
        for result in results['items']:
            snippet = result.get('snippet', 'No snippet available')
            print(f"Snippet: {snippet}")
            speak(snippet)  # Add this line to speak the snippet
    else:
        no_results_message = "No results found or 'items' key is missing."
        print(no_results_message)
        speak(no_results_message)  # Speak the no results message

                
def process_command(command):
    """Process the voice command and trigger appropriate actions."""
    match = re.search(r"(?:set|schedule|remind me to|create a reminder for|add a reminder to) (.+?) at (\d{1,2}:\d{2}(?:\s?[ap]m)?)", command)

    if match:
        reminder_text = match.group(1)
        reminder_time = match.group(2)
        add_reminder(reminder_text, reminder_time)
    elif "set voice" in command:
        if "male" in command:
            set_voice('male')
        elif "female" in command:
            set_voice('female')
        else:
            speak("Please specify if you want a male or female voice.")
    elif "weather" in command:
        # Extract city name from command if possible; otherwise, use a default city
        city_match = re.search(r"weather in (\w+)", command)
        city_name = city_match.group(1) if city_match else "your location"  # Default city if none specified
        get_weather(city_name)
    elif "search" in command or "find" in command:
        search_query = command.replace("search", "").replace("find", "").strip()
        if search_query:
            google_custom_search(search_query)
        else:
            speak("Please specify what you would like to search for.")
    elif "play" in command and "music" in command:
        song_name = command.replace("play music", "").strip()
        play_music(song_name)
    else:
        speak("Please specify the reminder and time, or ask me to play music on YouTube.")

if __name__ == "__main__":
    speak("Hello, I am your assistant. How can I help you today?")
    while True:
        command = listen()
        if "exit" in command or "stop" in command:
            speak("Goodbye!")
            break
        process_command(command)
        check_reminders()
