from dataclasses import dataclass
from typing import Literal


@dataclass
class Client:
    tiktok_username: Literal[False] | str
    twitch_username: Literal[False] | str
