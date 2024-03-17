import logging
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from itertools import islice

import discord

L = logging.getLogger(__name__)

def user_nick(msg: discord.Message) -> str:
    return msg.author.global_name or msg.author.name

class Keeper(ABC):
    MESSAGE_HISTORY_LEN = 0

    @abstractmethod
    def process_message(self, message: discord.Message):
        """Ingest a user's message."""
        pass
    @abstractmethod
    def process_self_message(self, message: discord.Message):
        """Ingest our own message so we can remember what we said."""
        pass
    @abstractmethod
    def get_recent(self, message_count: int, member_id: int) -> list[discord.Message]: 
        """Gets a user's last N known messages."""
        pass
    @abstractmethod
    def get_count(self, member_id: int) -> int: 
        """Gets a user's known message count."""
        pass
    @abstractmethod
    def get_ai_ingestible(self, member_id: int, start_token: str = "", stop_token: str = "") -> list[str]:
        """
        Produces a user's message history in a format that the AI can
        understand. The newest message will always be last.
        """
        pass


class ConvoKeeper(Keeper):
    """
    Implements an AI memory which just stores the last N messages and ignores members
    """
    MESSAGE_HISTORY_LEN = 1000

    def __init__(self):
        """
        Attributes:
            history -- the last MESSAGE_HISTORY_LEN messages
        """
        self.history: deque[discord.Message] = deque(maxlen=self.MESSAGE_HISTORY_LEN)

    def process_message(self, message: discord.Message):
        """Ingest a user's message."""
        self.history.append(message)

    def process_self_message(self, message: discord.Message):
        """Ingest our own message so we can remember what we said."""
        self.history.append(message)

    def get_recent(self, message_count: int, member_id: int) -> list[discord.Message]: 
        """Gets the last N known messages."""
        return list(islice(reversed(self.history), message_count))
    
    def get_count(self, member_id: int = 0) -> int: 
        """Gets a known message count."""
        return len(self.history)

    def get_ai_ingestible(self, member_id: int, start_token: str = "", stop_token: str = "") -> list[str]:
        """
        Produces a user's message history in a format that the AI can
        understand. The newest message will always be last.
        """
        return [f"{start_token} {user_nick(msg)}: {msg.clean_content} {stop_token}" for msg in self.history]


class PeopleKeeper(Keeper):
    """
    Implements an AI memory which distinguishes between different people's conversation threads.
    """
    MESSAGE_HISTORY_LEN = 100

    def __init__(self):
        """
        Attributes:
            history -- maps user IDs to a history of messages
        """
        self.history: dict[int, deque[discord.Message]] = \
            defaultdict(lambda: deque(maxlen=self.MESSAGE_HISTORY_LEN))

    def process_message(self, message: discord.Message):
        """Ingest a user's message."""
        self.history[message.author.id].append(message)
        
    def process_self_message(self, message: discord.Message):
        """Ingest our own message so we can remember what we said."""
        if message.reference:
            if isinstance(message.reference.resolved, discord.Message):
                who_we_replied_to = message.reference.resolved.author.id 
                self.history[who_we_replied_to].append(message)

    def get_recent(self, message_count: int, member_id: int) -> list[discord.Message]: 
        """Gets a user's last N known messages."""
        return list(islice(reversed(self.history[member_id]), message_count))
    
    def get_count(self, member_id: int) -> int: 
        """Gets a user's known message count."""
        return len(self.history[member_id])

    def get_ai_ingestible(self, member_id: int, start_token: str = "", stop_token: str = "") -> list[str]:
        """
        Produces a user's message history in a format that the AI can
        understand. The newest message will always be last.
        """
        return [f"{start_token} {user_nick(msg)}: {msg.clean_content} {stop_token}" for msg in self.history[member_id]]
