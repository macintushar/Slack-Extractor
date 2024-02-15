from flask import Flask, request, jsonify, g
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import sqlite3
import os
from load_dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

slack_client = WebClient(token=os.environ['SLACK_BOT_TOKEN'])

def get_db():
    db = sqlite3.connect('subot.db')
    return db

def create_table():
    db = get_db()
    db.execute('''
    CREATE TABLE IF NOT EXISTS subot_quotes (
        REACTION_ID INTEGER PRIMARY KEY,
        USERNAME TEXT NOT NULL,
        QUOTE TEXT NOT NULL,
        EMOJI TEXT NOT NULL UNIQUE,
        TIMESTAMP DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
''')

def load_quotes():
    db = get_db()
    create_table()
    cursor = db.execute('SELECT * FROM subot_quotes;')
    reactions = []

    for row in cursor:
        reactions.append({
            'reaction_id': row[0],
            'username': row[1],
            'quote': row[2],
            'emoji': row[3],
            'timestamp': row[4]
        })
        print('here',row)
    cursor.close()
    return reactions

@app.route('/slack/events', methods=['POST'])
def slack_events():
    json_payload = request.json

    if 'challenge' in json_payload:
        return jsonify({'challenge': json_payload['challenge']})

    if json_payload['token'] != os.environ['SLACK_VERIFICATION_TOKEN']:
        return jsonify({'error': 'Invalid request token'}), 403

    event = json_payload['event']
    
    if event['type'] == 'reaction_added':
        reactions = load_quotes()
        print(reactions)
        
        for reaction in reactions: 
            
            if event['reaction'] == reaction['emoji']:
                try:
                    channel_id = event['item']['channel']
                    message_ts = event['item']['ts']
                    
                    response = slack_client.conversations_replies(
                        channel=channel_id,
                        ts=message_ts
                    )

                    if not response['messages'][0].get('thread_ts'):
                        slack_client.chat_postMessage(
                            channel=channel_id,
                            thread_ts=message_ts,
                            text='_' + reaction['quote'] + '_',
                            username=reaction['username'],
                            type='plain_text',
                            icon_emoji=':' + reaction['emoji'] + ':'
                        )
                    else:
                        thread_ts = response['messages'][0].get('thread_ts')
                        slack_client.chat_postMessage(
                            channel=channel_id,
                            thread_ts=thread_ts,
                            text='_' + reaction['quote'] + '_',
                            username=reaction['username'],
                            type='plain_text',
                            icon_emoji=':' + reaction['emoji'] + ':'
                        )

                except SlackApiError as e:
                    print(f"Error posting message: {e}")

    return jsonify({'status': 'ok'}), 200

@app.route('/slack/wisdom', methods=['POST'])
def wisdom():
    reactions = load_quotes()
    print(reactions)
    json_payload = request.json
    print(json_payload)
    return jsonify({'status':''})

@app.route('/')
def index():
    return 'Subot is running!'

@app.route('/quotes/new', methods=['POST'])
def add_quote():
    data = request.json
    print(data)
    db = get_db()
    db.execute('INSERT INTO subot_quotes (USERNAME, QUOTE, EMOJI, TIMESTAMP) VALUES (?, ?, ?, CURRENT_TIMESTAMP);', (data['username'], data['quote'], data['emoji']))
    db.commit()
    return jsonify({'status': 'ok'}), 200

@app.route('/quotes', methods=['GET'])
def get_quotes():
    reactions = load_quotes()
    return jsonify(reactions)

@app.route('/quotes/<int:reaction_id>', methods=['GET'])
def get_quote(reaction_id):
    db = get_db()
    cursor = db.execute('SELECT * FROM subot_quotes WHERE REACTION_ID = ?;', (reaction_id,))
    reaction = cursor.fetchone()
    cursor.close()
    return jsonify({
        'reaction_id': reaction[0],
        'username': reaction[1],
        'quote': reaction[2],
        'emoji': reaction[3],
        'timestamp': reaction[4]
    })
    
@app.route('/quotes/<int:reaction_id>', methods=['DELETE'])
def delete_quote(reaction_id):
    db = get_db()
    db.execute('DELETE FROM subot_quotes WHERE REACTION_ID = ?;', (reaction_id,))
    db.commit()
    return jsonify({'status': 'ok'}), 200
    
if __name__ == '__main__':
    app.run(port=3000)
