import logging
import os
import random

import discord
import uwuify
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

from . import sicko

L = logging.getLogger(__name__)


class DiscordWeirdo(discord.Client):
    L = logging.getLogger("discord.weirdo")
    MESSAGE_RESPONSE_RATE = 0.05

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sickos = [
            sicko.Sicko(sicko.PeopleKeeper, sicko.LIL_WEIRDO),
            # sicko.Sicko("llama2-uncensored", sicko.PeopleKeeper, sicko.LIL_WEIRDER),
            # sicko.Sicko("llama2-uncensored", sicko.ConvoKeeper, sicko.LIL_FREAK)
        ]

    async def respond_to_message(self, message: discord.Message): 
        """Sends a random sicko's response to a user, and record that sent
        message in that sicko's memory."""
        self.L.info("Responding!")
        async with message.channel.typing():
            sicko = random.choice(self.sickos)
            response = await sicko.respond_to(message.author)
            self.L.info(f"Generated mean response: {response}")
            try:
                # uwu_response = uwuify.uwu(response, flags=uwuify.SMILEY | uwuify.YU | uwuify.STUTTER)
                # TODO: the non-uwuified version has to be the one that we feed into its memory
                uwu_response = response
            except IndexError:
                # sometimes the uwu library fails lol
                uwu_response = response
            sent_message = await message.reply(uwu_response)
            self.L.info(f"Ingesting message event from ourselves...")
            sicko.keeper.process_self_message(sent_message)

    async def on_ready(self):
        self.L.info(f"Loaded that mean ass bot named {self.user}")

    async def on_message(self, message: discord.Message):
        if message.author.id == self.user.id:
            self.L.info(f"Skipping our own message in on_message...")
            return
        self.L.info(f"Got message from {message.author.id}/{message.author}, sending to {len(self.sickos)} sickos")
        for sicko in self.sickos:
            sicko.keeper.process_message(message)
            preview = ' / '.join([msg.content for msg in sicko.keeper.get_recent(3, message.author.id)])
            self.L.info(f"Last 3/{sicko.keeper.get_count(message.author.id)}/{sicko.keeper.MESSAGE_HISTORY_LEN} messages: {preview}")
        if message.reference:
            # the message might be a reply!
            if isinstance(message.reference.resolved, discord.Message):
                # the message _is_ a reply that we can access
                if message.reference.resolved.author.id == self.user.id:
                    # it's a reply to us, we definitely respond
                    await self.respond_to_message(message)
                    return
        if any([mentioned.id == self.user.id for mentioned in message.mentions]):
            # the message pinged us
            await self.respond_to_message(message)
            return
        # only reply to 15% of messages normally
        if random.random() < self.MESSAGE_RESPONSE_RATE:
            await self.respond_to_message(message)
            return

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