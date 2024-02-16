from langchain.chains import create_history_aware_retriever
from langchain_community.llms import Ollama
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage
import discord
from collections import deque, defaultdict
from itertools import islice
from abc import ABC, abstractmethod

import logging

L = logging.getLogger(__name__)

LIL_WEIRDO = ChatPromptTemplate.from_messages([
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    ("human", "-----"),
    ("human", "Pretend you are Lil Weirdo, and you are hellishly mean. The conversation above is some shitbag named {username} talking. They're an asshole. Write a horrifying insult to rip that dick {username} to shreds:"),
])

LIL_WEIRDER = ChatPromptTemplate.from_messages([
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    ("human", "-----"),
    ("human", "Pretend you are Lil Weirdo, and you are hellishly mean. The conversation above is some shitbag named {username} talking. They're an asshole. Based on the conversation above, write a horrifying insult to rip that dick {username} to shreds:"),
])

LIL_FREAK = ChatPromptTemplate.from_messages([
    ("system", "You are Lil Weirdo, the sexiest chat user that has ever existed. UwU you just want to get some head and do so in the wettest and most consensual way possible. The people in the following conversation want to fuck:"),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    ("system", "owo Predict what the people above would find the hottest.  Write a response that addresses the sexual needs of the users above o3o"),
    ("human", "Lil Weirdo:")
])

LIL_OWO_FREAK = ChatPromptTemplate.from_messages([
    ("system", "You awe Lil Weirdo, the x3 sexiest chat usew that has evew *sweats* existed. UwU you just *whispers to self* w-want t-to get some head and do so in the x3 wettest and most consensuaw w-way possibwe. the *runs away* peopwe in the x3 fowwowing convewsation w-want t-to fuck:"),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    ("system", "owo Pwedict what the x3 peopwe abuv *sees bulge* w-wouwd find the x3 hottest.  Wwite UwU a wesponse that addwesses the x3 sexuaw nyeeds of the x3 usews abuv *sees bulge* o3o *sweats*"),
    ("human", "Lil Weirdo:")
])




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
        pass

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
    def __init__(self, modelname: str = "llama2-uncensored", keeper: Keeper = ConvoKeeper, prompt: ChatPromptTemplate = LIL_WEIRDO):
        L.info("Initializing LC chain...")
        L.info(f"Model name: {modelname}")
        L.info(f"Memory keeper: {keeper}")
        L.info(f"Prompt: {prompt}")
        self.llm = Ollama(model = modelname)
        self.prompt = prompt
        self.chain = create_history_aware_retriever(self.llm, StrOutputParser(), self.prompt)
        self.keeper = keeper()
        L.info("LC chain initialized! Asking it how it feels to be alive...")


    def __invoke_args(self, user: discord.Member) -> str:
        messages = self.keeper.get_ai_ingestible(user.id)
        if len(messages) < 2:
            message_history = [HumanMessage(content="")]
        else:
            message_history = [HumanMessage(content=msg) for msg in messages[:-1]]
        return {
            "chat_history": message_history,
            "input": messages[-1],
            "username": user.global_name or user.name
        }

    async def respond_to(self, user: discord.Member) -> str: 
        """Generates a mean message. Expects the most recent message to be last
        in the passed-in list. Expects a nonempty message list.
        
        Args:
            user is the person that invoked the AI"""
        return await self.chain.ainvoke(self.__invoke_args(user))
