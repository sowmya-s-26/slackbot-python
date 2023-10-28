import os
from pathlib import Path
from dotenv import load_dotenv
from slackeventsapi import SlackEventAdapter
from slack_sdk import WebClient
import ssl

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

from flask import Flask, request, jsonify, Response
app = Flask(__name__)

slack_event_adapter = SlackEventAdapter(os.environ['SIGNING_SECRET'], '/slack/events', app)

ssl._create_default_https_context = ssl._create_unverified_context

client = WebClient(token=os.environ['SLACK_TOKEN'])
api_response = client.api_test()
BOT_ID = client.api_call("auth.test")['user_id']

message_counts = {}
welcome_messages = {}

class WelcomeMessage:
  START_TEXT = {
    'type': 'section',
    'text': {
      'type': 'mrkdwn',
      'text': (
        'Welcome to this awesome channel! \n\n'
        '*Get started by completing the tasks!*'
      )
    }
  }

  DIVIDER = {'type': 'divider'}

  def __init__(self, channel, user):
    print(self)
    self.channel = channel
    self.user = user
    self.timestamp = ''
    self.completed = False
    self.icon_emoji = ':robot_face:'

  def get_message(self):
    return {
      'ts': self.timestamp,
      'channel': self.channel,
      'username': 'Welcome Robot!',
      'icon_emoji': self.icon_emoji,
      'blocks': [
        self.START_TEXT,
        self.DIVIDER,
        *self._get_reaction_task()
      ]
    }
  
  def _get_reaction_task(self):
    checkmark = ':white_check_mark:'
    if not self.completed:
      checkmark = ':white_large_square:'
    
    text = f'{checkmark} *React to this message!*'

    return [{'type': 'section', 'text': {'type': 'mrkdwn', 'text': text}}]
  
@slack_event_adapter.on('reaction_added')
def reaction(payload):
  print('hereeeee')
  event = payload.get('event', {})
  print(event)
  channel_id = event.get('channel')
  user_id = event.get('user')


  if f'@{user_id}' not in welcome_messages:
    return
  
  print(welcome_messages[channel_id][user_id])

  welcome = welcome_messages[channel_id][user_id]
  welcome.completed = True
  welcome.channel = channel_id
  message = welcome.get_message()
  updated_message = client.chat_update(**message)
  welcome.timestamp = updated_message['ts']
  
def send_welcome_message(channel, user):
  welcome = WelcomeMessage(channel, user)
  message = welcome.get_message()
  response = client.chat_postMessage(**message)
  welcome.timestamp = response['ts']

  if channel not in welcome_messages:
    welcome_messages[channel] = {}
  welcome_messages[channel][user] = welcome

@app.route('/slack/events', methods=['POST'])
def slack_events():
    data = request.json  

    if 'challenge' in data:
        return jsonify({"challenge": data['challenge']})
    return jsonify({"status": "OK"})

@slack_event_adapter.on('message')
def message(payload):
  event = payload.get('event', {})
  channel_id = event.get('channel')
  user_id = event.get('user')
  text = event.get('text')

  if(user_id != None and user_id != BOT_ID):
    if(user_id in message_counts):
      message_counts[user_id] += 1
    else:
      message_counts[user_id] = 1

    if text.lower() == 'start':
      send_welcome_message(f'@{user_id}', user_id)
    # client.chat_postMessage(channel=channel_id, text=text)

@app.route('/message-count', methods=['GET', 'POST'])
def message_count():
  data = request.form
  channel_id = data.get('channel_id')
  user_id = data.get('user_id')
  message_count = message_counts.get(user_id, 0)
  client.chat_postMessage(channel=channel_id, text=f"Message: {message_count}")
  return Response(), 200

if(__name__ == '__main__'):
  app.run(debug=True)