from TikTokLive import TikTokLiveClient
from TikTokLive.client.errors import UserOfflineError
from flask import Flask
from flask_socketio import join_room, emit, leave_room as leave_room_sio
from twitch_chat_irc import twitch_chat_irc

from twitchtok.connection import Connection, TwitchConnection, TikTokConnection

twitch_connections: dict[str, Connection] = {}
tiktok_connections: dict[str, Connection] = {}


class RoomType:
    TIKTOK = "tiktok"
    TWITCH = "twitch"


def join_twitch_room(app: Flask, username: str):
    room_name = f"twitch:{username}"
    join_room(room_name)
    if username in twitch_connections:
        twitch_connections[username].increment_client_count()
        return True

    connection = TwitchConnection(connection=twitch_chat_irc.TwitchChatIRC())
    connection.increment_client_count()
    twitch_connections[username] = connection

    connection.connect(app, username, room_name)
    return True


def join_tiktok_room(app: Flask, username: str):
    room_name = f"tiktok:{username}"
    join_room(room_name)
    if username in tiktok_connections:
        tiktok_connections[username].increment_client_count()
        return True

    connection = TikTokConnection(connection=TikTokLiveClient(unique_id=username))
    connection.increment_client_count()
    tiktok_connections[username] = connection

    try:
        connection.connect(app, username, room_name)
    except UserOfflineError:
        leave_room_sio(room_name)
        emit("live-error", {"message": "The tiktok user is offline."})
        return False

    return True


def leave_room(username: str, room_type: RoomType):
    connections = twitch_connections if room_type == RoomType.TWITCH else tiktok_connections

    if username not in connections:
        return
    room_name = f"{room_type}:{username}"
    leave_room_sio(room_name)
    connection = connections[username]
    connection.decrement_client_count()
    print(f"left {room_type} room for {username}")
    if connection.client_count == 0:
        try:
            connection.disconnect()
        finally:
            print(f"closed {room_type} connection for {username}")
            del connections[username]
