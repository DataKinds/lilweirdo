import logging
import os

import discord
import ollama  # type: ignore
from dotenv import load_dotenv

from . import discordweirdo

L = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('discord').setLevel(logging.INFO)
    L.info("Loading env...")
    load_dotenv()
    L.info(os.environ)

    L.info("Intializing Discord client...")
    intents = discord.Intents.default()
    intents.message_content = True
    ollamaclient = ollama.Client(host=os.environ.get("OLLAMA_HOST"),
                                 timeout=20.0) # seconds
    client = discordweirdo.DiscordWeirdo(ollamaclient=ollamaclient,
                                         intents=intents)
    client.run(os.environ["DISCORD_TOKEN"], log_handler=None)

if __name__ == "__main__":
    main()

    # Instructions for generating URL is here: https://discordpy.readthedocs.io/en/stable/discord.html#inviting-your-bot
    # Invite me with https://discord.com/api/oauth2/authorize?client_id=1207216895586213889&permissions=380105120832&scope=bot