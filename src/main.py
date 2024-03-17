import logging
import os
import random
import re

import discord
from dotenv import load_dotenv

from . import consts, keeper, sicko, templater

L = logging.getLogger(__name__)

class DiscordWeirdo(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sickos: dict[str, sicko.Sicko] = {
            "weirdo": sicko.Sicko(keeper.PeopleKeeper, templater.LIL_WEIRDO),
            "freak": sicko.Sicko(keeper.ConvoKeeper, templater.LIL_FREAK),
            "uwu": sicko.Sicko(keeper.ConvoKeeper, templater.LIL_OWO_FREAK),
        }
        self.response_rate: float = consts.DEFAULT_RESPONSE_RATE
        self.current_sicko: str | None = None
        # self.tree = discord.app_commands.CommandTree(self)
        self.command_prefix: str = consts.DEFAULT_COMMAND_PREFIX

    async def respond_to_message(self, message: discord.Message): 
        """Sends a random sicko's response to a user, and record that sent
        message in that sicko's memory."""
        responder: sicko.Sicko
        if self.current_sicko is None:
            responder = random.choice(list(self.sickos.values()))
        else:
            responder = self.sickos[self.current_sicko]
        L.info(f"Responding! Current sicko is {self.current_sicko}, responding with {responder}...")
        async with message.channel.typing():
            response = await responder.respond_to(message.author)
            L.info(f"Generated response: {response}")
            try:
                # uwu_response = uwuify.uwu(response, flags=uwuify.SMILEY | uwuify.YU | uwuify.STUTTER)
                # TODO: the non-uwuified version has to be the one that we feed into its memory
                uwu_response = response
            except IndexError:
                # sometimes the uwu library fails lol
                uwu_response = response
            sent_message = await message.reply(uwu_response)
            L.info("Ingesting message event from ourselves...")
            responder.keeper.process_self_message(sent_message)

    async def on_ready(self):
        L.info(f"Loaded that mean ass bot named {self.user}")

    async def command_message(self, message: discord.Message) -> None:
        """Handles internal bot commands which start with `self.command_prefix`"""
        command, *rest = re.split(r"\s+", message.content)
        match command:
            case "/help":
                await message.reply(consts.HELP_MESSAGE)
            case "/amnesia":
                L.info("Clearing memory...")
                for sicko in self.sickos.values():
                    sicko.keeper = sicko.keeper.__class__()
                await message.reply("Uhhh I forgor >:3")
            case "/responserate":
                try:
                    rate = float(rest[0])
                    assert 0 <= rate <= 1
                    self.response_rate = rate
                    await message.reply(f"Set response rate to {rate}")
                except (IndexError, ValueError, AssertionError):
                    await message.reply(consts.RESPONSE_RATE_HELP_MESSAGE)
            case "/sicko":
                def sicko_list():
                    return ", ".join([f"`{sicko}`" for sicko in self.sickos.keys()]) 
                try:
                    subcommand, *rest = rest
                    match subcommand:
                        case "current":
                            if self.current_sicko is None:
                                await message.reply("Currently set to shuffle all sickos each reply.")
                            else:
                                await message.reply(f"The sicko that's replying to you is `{self.current_sicko}`.")
                        case "shuffle":
                            self.current_sicko = None
                            await message.reply("Shuffling sickos.")
                        case "list":
                            await message.reply(f"Currently available sickos: {sicko_list()}")
                        case "set":
                            newsicko = rest[0]
                            if newsicko not in self.sickos.keys():
                                await message.reply(f"Sicko `{newsicko}` not available.\nCurrently available sickos: {sicko_list()}")
                                return
                            self.current_sicko = newsicko
                            await message.reply(f"Switched to `{newsicko}`.")
                        case _:
                            await message.reply(consts.SICKO_HELP_MESSAGE)
                except (ValueError, IndexError) as e:
                    L.debug("Failed slash command", e)
                    await message.reply(consts.SICKO_HELP_MESSAGE)
            case "/~cheevosfrom":
                if len(rest) == 0:
                    await message.reply(consts.HELP_MESSAGE)
                    return
                game_title = message.content.removeprefix("/~cheevosfrom ")
                response = templater.CHEEVOS_FROM.generate(game_title)
                await message.reply(f"""Achievements from {game_title}: 
{response}""")
            case _:
                await message.reply(consts.HELP_MESSAGE)

    async def on_message(self, message: discord.Message):
        if message.author.id == self.user.id: # type: ignore
            L.info("Skipping our own message in on_message...")
            return
        if message.content.startswith("/"):
            L.info("Got slash command, forwarding to command processor...")
            await self.command_message(message)
            return
        L.info(f"Got message from {message.author.id}/{message.author}, sending to {len(self.sickos)} sickos")
        for s in self.sickos.values():
            s.keeper.process_message(message)
            preview = ' / '.join([msg.content for msg in s.keeper.get_recent(3, message.author.id)])
            L.info(f"Last 3/{s.keeper.get_count(message.author.id)}/{s.keeper.MESSAGE_HISTORY_LEN} messages: {preview}")
        if message.reference:
            # the message might be a reply!
            if isinstance(message.reference.resolved, discord.Message):
                # the message _is_ a reply that we can access
                if message.reference.resolved.author.id == self.user.id: # type: ignore
                    # it's a reply to us, we definitely respond
                    await self.respond_to_message(message)
                    return
        if any([mentioned.id == self.user.id for mentioned in message.mentions]): # type: ignore
            # the message pinged us
            await self.respond_to_message(message)
            return
        # only reply to some percentage of messages normally
        if random.random() < self.response_rate:
            await self.respond_to_message(message)
            return

def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('discord').setLevel(logging.INFO)
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