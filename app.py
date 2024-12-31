import asyncio
import datetime
import threading

from TikTokLive import TikTokLiveClient
from TikTokLive.client.errors import UserOfflineError
from TikTokLive.events import CommentEvent
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from twitch_chat_irc import twitch_chat_irc

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)
clients = {}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/listen')
def listen():
    return render_template('listen.html')


@socketio.on('connect')
def handle_connect():
    print('connected')


@socketio.on('disconnect')
def handle_disconnect():
    if data := clients.get(request.sid):
        tiktok_client, twitch_connection = data
        twitch_connection.close_connection()
        if tiktok_client:
            print('disconnecting TIKTOK')
            start = datetime.datetime.now()
            asyncio.run(tiktok_client.disconnect())
            finish = datetime.datetime.now()
            print(f'disconnected TIKTOK in {finish - start}')
        del clients[request.sid]
    print('disconnected')


@socketio.on('listen')
def handle_listen(data):
    tiktok_username = data['tiktok_user']
    twitch_username = data['twitch_user']
    tiktok_client: TikTokLiveClient = TikTokLiveClient(unique_id=tiktok_username)
    twitch_connection = twitch_chat_irc.TwitchChatIRC()
    clients[request.sid] = (tiktok_client, twitch_connection)

    @tiktok_client.on(CommentEvent)
    async def on_tiktok_comment(event: CommentEvent) -> None:
        print(f'sending TIKTOK comment for {tiktok_username}')
        emit('listen', {"user": event.user.nickname, "message": event.comment, "type": "tiktok"})

    def on_twitch_message(message):
        print(f'sending TWITCH comment for {twitch_username}')
        socketio.emit('listen', {"user": message['display-name'], "message": message['message'], "type": "twitch"})

    def run_twitch():
        with app.test_request_context('/listen'):
            try:
                twitch_connection.listen(twitch_username, on_message=on_twitch_message)
            except OSError:
                print('Twitch connection closed -', twitch_username)

    t = threading.Thread(target=run_twitch)
    t.start()
    try:
        tiktok_client.run()
    except UserOfflineError:
        clients[request.sid] = (None, twitch_connection)
        emit('live-error', {"message": "The tiktok user is offline."})

    print('finished')


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8000, allow_unsafe_werkzeug=True)
