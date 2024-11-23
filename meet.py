import json
from google.cloud import pubsub_v1
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Constants
PROJECT_ID = ""
TOPIC_NAME = ""
SUBSCRIPTION_NAME = ""
SCOPES = ['https://www.googleapis.com/auth/pubsub']

# Authenticate with Google Pub/Sub API
def authenticate_google_pubsub():
    creds = None
    try:
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('creds1.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
    except Exception as e:
        print(f"Authentication error: {e}")
        return None
    return creds

# Fetch messages from Pub/Sub topic
def subscribe_to_topic(project_id, subscription_name):
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_name)

    def callback(message):
        print(f"Received message: {message}")
        message.ack()

        # Process message data (assuming JSON payload)
        try:
            data = json.loads(message.data)
            print(f"Message data: {data}")
            
            # Placeholder: Process meeting data (e.g., extract meeting ID, date, and other relevant info)
            meeting_id = data.get('meetingId', None)
            if meeting_id:
                print(f"Meeting ID: {meeting_id}")
                # Add logic to fetch other relevant meeting details if necessary

        except Exception as e:
            print(f"Error processing message: {e}")

    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    print(f"Listening for messages on {subscription_path}")

    try:
        streaming_pull_future.result()
    except Exception as e:
        print(f"Stream error: {e}")
        streaming_pull_future.cancel()
        subscriber.close()

# Main entry point to authenticate and start listening to Pub/Sub
def authenticate_and_subscribe():
    creds = authenticate_google_pubsub()
    if creds:
        subscribe_to_topic(PROJECT_ID, SUBSCRIPTION_NAME)

if __name__ == "__main__":
    authenticate_and_subscribe()
