import logging
import os

import discord
from dotenv import load_dotenv

from . import discordweirdo

L = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('discord').setLevel(logging.INFO)
    L.info("Loading env...")
    load_dotenv()

    L.info("Intializing Discord client...")
    intents = discord.Intents.default()
    intents.message_content = True
    client = discordweirdo.DiscordWeirdo(intents=intents)
    client.run(os.environ["DISCORD_TOKEN"], log_handler=None)

if __name__ == "__main__":
    main()

    # Instructions for generating URL is here: https://discordpy.readthedocs.io/en/stable/discord.html#inviting-your-bot
    # Invite me with https://discord.com/api/oauth2/authorize?client_id=1207216895586213889&permissions=380105120832&scope=bot