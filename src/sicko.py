import logging
import re
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from itertools import islice
from .consts import DEFAULT_MODEL


import discord
from langchain.chains import create_history_aware_retriever
from langchain_community.llms import Ollama
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import ollama as ol
from .templater import Templater, LIL_WEIRDO, LIL_OWO_FREAK

L = logging.getLogger(__name__)

class Keeper(ABC):
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
    def get_ai_ingestible(self, member_id: int) -> list[str]:
        """
        Produces a user's message history in a format that LangChain can
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

    def get_ai_ingestible(self, member_id: int) -> list[str]:
        """
        Produces a user's message history in a format that LangChain can
        understand. The newest message will always be last.
        """
        return [f"{msg.author.global_name or msg.author.name}: {msg.content}" for msg in self.history]


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

    def get_ai_ingestible(self, member_id: int) -> list[str]:
        """
        Produces a user's message history in a format that LangChain can
        understand. The newest message will always be last.
        """
        return [f"{msg.author.global_name or msg.author.name}: {msg.content}" for msg in self.history[member_id]]



class Sicko:
    """Implements a really mean AI.
    
    Args:
        modelname: What Ollama model should we load?
        prompt: LangChain prompt fed into the Sicko AI. Expects to have 3
            variables:
                (MessagesPlaceholder(variable_name="chat_history")) where the memory of the bot is fed into
                {input} the previous message that triggered the bot
                {username} the user that triggered the bot
    """
    def __init__(self, 
                 keeper: Keeper = ConvoKeeper, 
                 templater: Templater = LIL_WEIRDO):
        L.info("Initializing LC chain...")
        L.info(f"Memory keeper: {keeper}")
        L.info(f"Templater: {templater}")
        self.llm: ol.Client = ol.Client()
        self.templater: Templater = templater
        self.keeper: Keeper = keeper()
        L.info("LC chain initialized! Asking it how it feels to be alive...")

    def __prompt(self, user: discord.Member) -> str:
        messages = '[stop]\n'.join(self.keeper.get_ai_ingestible(user.id))
        return f"{messages}\nLil Weirdo:"

    async def respond_to(self, user: discord.Member) -> str: 
        """Generates a mean message. Expects the most recent message to be last
        in the passed-in list. Expects a nonempty message list. Will crop the
        message such that it doesn't generate any extra users in the
        conversation (so the message ends before something like "Human:").
        
        Args:
            user is the person that invoked the AI"""
        with self.templater.with_model(self.llm) as modelname:
            response = self.llm.generate(
                model=modelname,
                prompt=self.__prompt(user)
            )['response']
        return response
