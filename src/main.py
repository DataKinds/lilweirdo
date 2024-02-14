import logging
import os

import discord
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from collections import deque, defaultdict
from itertools import islice
import random
from .chain import Sicko

L = logging.getLogger(__name__)


class PeopleKeeper:
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

    def get_preview(self, member_id: int, message_count: int) -> list[discord.Message]: 
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
        return [msg.content for msg in self.history[member_id]]

class DiscordWeirdo(discord.Client):
    L = logging.getLogger("discord.weirdo")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pk = PeopleKeeper()
        self.sicko = Sicko()

    async def respond_to_message(self, message: discord.Message): 
        """Sends a mean responds to a user."""
        self.L.info("Responding!")
        async with message.channel.typing():
            response = self.sicko.respond_to(message.author.name, self.pk.get_ai_ingestible(message.author.id))
            self.L.info(f"Generated mean response: {response}")
            await message.reply(response)


    async def on_ready(self):
        self.L.info(f"Loaded that mean ass bot named {self.user}")

    async def on_message(self, message: discord.Message):
        if message.author.id == self.user.id:
            self.L.info(f"Ignoring message event from ourselves...")
            return
        self.L.info(f"Got message from {message.author.id}/{message.author}")
        self.pk.process_message(message)
        preview = ' / '.join([msg.content for msg in self.pk.get_preview(message.author.id, 3)])
        self.L.info(f"Last 3/{self.pk.get_count(message.author.id)}/{self.pk.MESSAGE_HISTORY_LEN} messages: {preview}")
        # only reply to 15% of messages
        if random.random() < 0.15:
            self.respond_to_message(message)

def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('discord').setLevel(logging.INFO)
    L.setLevel(logging.INFO)
    L.info("Loading env...")
    load_dotenv()

    L.info("Intializing Discord client...")
    intents = discord.Intents.default()
    intents.message_content = True
    client = DiscordWeirdo(intents=intents)
    client.run(os.environ["DISCORD_TOKEN"], log_handler=None)

if __name__ == "__main__":
    main()

    # Instructions for generating URL is here: https://discordpy.readthedocs.io/en/stable/discord.html#inviting-your-bot
    # Invite me with https://discord.com/api/oauth2/authorize?client_id=1207216895586213889&permissions=380105120832&scope=bot