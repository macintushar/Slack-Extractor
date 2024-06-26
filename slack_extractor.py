from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import os

app = Flask(__name__)
slack_client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))

def load_reactions():
    return [{"emoji": "thumbsup"}, {"emoji": "thumbsdown"}]

@app.route('/slack/events', methods=['POST'])
def slack_events():
    json_payload = request.json

    if 'challenge' in json_payload:
        return jsonify({'challenge': json_payload['challenge']})

    if json_payload['token'] != os.environ['SLACK_VERIFICATION_TOKEN']:
        return jsonify({'error': 'Invalid request token'}), 403

    event = json_payload['event']
    
    if event['type'] == 'reaction_added':
        if event['reaction'] == "+1":
            try:
                channel_id = event['item']['channel']
                message_ts = event['item']['ts']
                
                response = slack_client.conversations_replies(
                    channel=channel_id,
                    ts=message_ts
                )
                print(response)

            except SlackApiError as e:
                print(f"Error posting message: {e}")

    return jsonify({'status': 'ok'}), 200

@app.route('/slack/users')
def slack_users():
    users = slack_client.users_list()
    print(users)
    return jsonify({"users":users.data}), 200

if __name__ == "__main__":
    app.run(port=3000, debug=True)
