import asyncio
import threading
from abc import ABC, abstractmethod

from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent
from twitch_chat_irc.twitch_chat_irc import TwitchChatIRC


class Connection(ABC):
    def __init__(self, connection: TikTokLiveClient | TwitchChatIRC):
        self.connection = connection
        self._client_count = 0

    @abstractmethod
    def connect(self, app, username, room_name):
        pass

    @abstractmethod
    def disconnect(self):
        pass

    @property
    def client_count(self):
        return self._client_count

    def increment_client_count(self):
        self._client_count += 1
        print(f"incremented {self.client_count=} for {self.connection}")

    def decrement_client_count(self):
        self._client_count -= 1
        print(f"decremented {self.client_count=} for {self.connection}")


class TwitchConnection(Connection):
    def connect(self, app, username, room_name):
        socketio = app.extensions["socketio"]

        def on_message(message):
            print(f"sending TWITCH comment for {username}")
            socketio.emit(
                "listen",
                {"user": message["display-name"], "message": message["message"], "type": "twitch"},
                to=room_name,
            )

        def run_twitch():
            with app.test_request_context("/listen"):
                try:
                    self.connection.listen(username, on_message=on_message)
                except OSError:
                    print("Twitch connection closed -", username)

        t = threading.Thread(target=run_twitch)
        t.start()

    def disconnect(self):
        print(f"disconnecting {self.connection}")

        def _disconnect():
            self.connection.close_connection()
            del self.connection

        t = threading.Thread(target=_disconnect)
        t.start()


class TikTokConnection(Connection):
    def connect(self, app, username, room_name):
        socketio = app.extensions["socketio"]

        @self.connection.on(CommentEvent)
        async def on_message(event: CommentEvent) -> None:
            print(f"sending TIKTOK comment for {username}")
            socketio.emit(
                "listen",
                {"user": event.user.nickname, "message": event.comment, "type": "tiktok"},
                to=room_name,
            )

        def run_tiktok():
            with app.test_request_context("/listen"):
                self.connection.run()

        t = threading.Thread(target=run_tiktok)
        t.start()

    def disconnect(self):
        print(f"disconnecting {self.connection}")

        def _disconnect():
            asyncio.run(self.connection.disconnect())
            del self.connection

        t = threading.Thread(target=_disconnect)
        t.start()
