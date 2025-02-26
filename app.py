from flask import Flask, render_template, request
from flask_socketio import SocketIO

from twitchtok.clients import Client
from twitchtok.rooms import leave_room, join_twitch_room, join_tiktok_room, RoomType

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"
socketio = SocketIO(app)
clients: dict[str, Client] = {}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/listen")
def listen():
    return render_template("listen.html")


@socketio.on("connect")
def handle_connect():
    print("connected")


@socketio.on("disconnect")
def handle_disconnect():
    if request.sid in clients:
        client = clients[request.sid]
        if client.twitch_username:
            leave_room(str(client.twitch_username), RoomType.TWITCH)
        if client.tiktok_username:
            leave_room(str(client.tiktok_username), RoomType.TIKTOK)
        del clients[request.sid]

    print("disconnected")


@socketio.on("listen")
def handle_listen(data):
    tiktok_username = data["tiktok_user"]
    twitch_username = data["twitch_user"]

    twitch_joined = join_twitch_room(app, twitch_username)
    tiktok_joined = join_tiktok_room(app, tiktok_username)

    clients[request.sid] = Client(
        tiktok_username=tiktok_joined and tiktok_username,
        twitch_username=twitch_joined and twitch_username,
    )

    print("finished")


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8000, allow_unsafe_werkzeug=True)
