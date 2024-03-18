import logging
import random
import re
from dataclasses import dataclass
from typing import Awaitable, Callable, TypeAlias, Union, cast

import discord

from . import consts, keeper, sicko, templater

L = logging.getLogger(__name__)

_Type_CommandTreeCallback: TypeAlias = Callable[[str, discord.Message], Awaitable[bool]]

@dataclass
class Command:
    """Stores a command inside a command tree.
    
    Arguments:
        func: The command's stored function. Should expect two arguments: the
        first being just the arguments to the command, the second being the
        original message that invoked the command.
        
        name: The command's fully qualified name as passed to """

    func: _Type_CommandTreeCallback
    name: str
    help: str | Callable[[], str]
    metavars: list[str]

    def get_help(self) -> str:
        """Generates the help if it's passed as a factory."""
        if isinstance(self.help, str):
            return self.help
        else:
            return self.help()

_Type_CommandTree: TypeAlias = dict[str, Union[Command, "_Type_CommandTree"] ]

class CommandTree:
    """Manages the command tree of a discord bot, including generating
    documentation, managing a command prefix, and routing commands."""
    def __init__(self, prefix: str = "/"):
        self.prefix: str = prefix
        self.cmds: _Type_CommandTree = {}

    def add(self, name: str, metavars: list[str], description: Callable[[], str] | str, command_func: _Type_CommandTreeCallback) -> _Type_CommandTreeCallback:
        """Register a new command in the tree. 
        
        Arguments:
            name: The name of the command to register. Multiple subcommands can
            be registered in one command group by separating command segments by
            spaces.
            
            metavars: The names of the variables passed into the command, for
            generating documentation.
            
            description: The help descripton for the command
            
            command_func: The function to execute if the command matches. This
            function should return True if it was successful."""
        L.info(f"Registering command '{name}' with variables {metavars} to function {command_func}")
        *name_components, name_last = re.split(r"\s+", name)
        # register command in self.cmds
        cur: _Type_CommandTree = self.cmds
        for component in name_components:
            if component not in cur:
                cur[component] = {}
            cur = cast(_Type_CommandTree, cur[component])
            assert isinstance(cur, dict), f"Failed to register a command '{name}' as an improper subgroup of already-registered command '{component}'."
        cur[name_last] = Command(command_func, name, description, metavars)
        return command_func
    
    def deprefixed(self, s: str) -> str | None:
        """Returns the string with the command prefix removed if it existed,
        else returns None."""
        if s.startswith(self.prefix):
            return s.removeprefix(self.prefix)
        else:
            return None
    
    def help(self, cmd_node: _Type_CommandTree | Command | None = None) -> str:
        """Returns the help message associated with a given node from [[cmds]].
        
        Arguments:
            cmd_node: This is an element that exists in [[cmds]]. It may be a
            dict, in which case the help is aggregated from all the children of
            the node. It may be a [[Command]], in which case only this commands'
            help is generated. Or, it may be ``None``, in which case the full
            help is generated."""
        def single_help(cmd: Command) -> str:
            mvars = "".join((f" <{v}>" for v in cmd.metavars))
            return f"* {self.prefix}**{cmd.name}**{mvars}: {cmd.get_help()}"
        if isinstance(cmd_node, Command):
            return single_help(cmd_node)
        elif isinstance(cmd_node, dict):
            helps = [self.help(child) for child in cmd_node.values()]
            return "\n".join(helps)
        else:
            bn = "\n"
            helps = [self.help(child) for child in self.cmds.values()]
            return f"""{consts.HELP_MESSAGE_HEADER}
{bn.join(helps)}
{consts.HELP_MESSAGE_FOOTER}"""

    async def invoke(self, message: discord.Message) -> bool:
        """Tries to process a message as a command. If the message should be
        ingested by the command processor, we return True. If the message should
        otherwise be handled normally we return False.
        
        If we should be ingesting a message but the command is malformed
        somehow, reply with the relevant help message and return True."""
        content = self.deprefixed(message.content)
        if content is None:
            return False
        # we don't split by regex class to be able to recreate message exactly
        L.info(f"Invoking command with content '{content}'")
        L.info(f"Current command tree: {self.cmds}")
        msg_arglist = content.split(" ") 
        drill: _Type_CommandTree | Command = self.cmds
        for idx, arg in enumerate(msg_arglist): 
            if isinstance(drill, dict):
                L.info(f"Drilling to '{arg}' with drill={drill}")
                if arg not in drill:
                    # We've reached a branch node where we cannot follow the command any longer.
                    L.info(f"Drilled down and couldn't find specified subcommand {arg} from command {msg_arglist}, replying with help for command tree {drill}.")
                    await message.reply(self.help(drill))
                    return True 
                drill = drill[arg]
                continue
            elif isinstance(drill, Command):
                # The tree returned a command's leaf node. We've found the command successfully.
                break
            else:
                # The tree's malformed!
                L.critical(f"""The command tree has been malformed: {self.cmds}""")
                return False
        # at this point, drill is either:
        #   * a Command, in which case we've successfully drilled down to a single command
        #   * or it's a branch of self.cmds, in which case a partial command was supplied
        if isinstance(drill, dict):
            L.info(f"Incomplete command '{content}' provided, replying with help for command tree {drill}")
            await message.reply(self.help(drill))
        elif isinstance(drill, Command):
            args_rest = " ".join(msg_arglist[idx:])
            L.info(f"Found command {msg_arglist}, passing it string argument '{args_rest}'")
            # Send the help message if the command fails.
            if not await drill.func(args_rest, message):
                await message.reply(self.help(drill))
        return True
        

class DiscordWeirdo(discord.Client):
    def __init__(self, *args, **kwargs) -> None: # type: ignore
        super().__init__(*args, **kwargs)
        self.sickos: dict[str, sicko.Sicko] = {
            "weirdo": sicko.Sicko(keeper.PeopleKeeper, templater.LIL_WEIRDO),
            "freak": sicko.Sicko(keeper.ConvoKeeper, templater.LIL_FREAK),
            "uwu": sicko.Sicko(keeper.ConvoKeeper, templater.LIL_OWO_FREAK),
        }
        self.response_rate: float = consts.DEFAULT_RESPONSE_RATE
        self.current_sicko: str | None = None
        # self.tree = discord.app_commands.CommandTree(self)
        self.ctree = CommandTree(consts.DEFAULT_COMMAND_PREFIX)
        self._register_commands()

    async def respond_to_message(self, message: discord.Message) -> None: 
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

    async def on_ready(self) -> None:
        L.info(f"Loaded that mean ass bot named {self.user}")

    async def cmd_help(self, args: str, message: discord.Message) -> bool:
        await message.reply(self.ctree.help())
        return True
    async def cmd_amnesia(self, args: str, message: discord.Message) -> bool:
        L.info("Clearing memory...")
        for s in self.sickos.values():
            s.keeper = s.keeper.__class__()
        await message.reply("Uhhh I forgor >:3")
        return True
    async def cmd_responserate(self, args: str, message: discord.Message) -> bool:
        try:
            rate = float(re.split(r"\s+", args)[0])
            assert 0 <= rate <= 1
            self.response_rate = rate
            await message.reply(f"Set response rate to {rate}")
        except (IndexError, ValueError, AssertionError):
            return False
        return True
    def __sicko_list(self) -> str:
        return ", ".join([f"`{sicko}`" for sicko in self.sickos.keys()]) 
    async def cmd_sicko_list(self, args: str, message: discord.Message) -> bool:
        await message.reply(f"Currently available sickos: {self.__sicko_list()}")
        return True
    async def cmd_sicko_current(self, args: str, message: discord.Message) -> bool:
        if self.current_sicko is None:
            await message.reply("Currently set to shuffle all sickos each reply.")
        else:
            await message.reply(f"The sicko that's replying to you is `{self.current_sicko}`.")
        return True
    async def cmd_sicko_shuffle(self, args: str, message: discord.Message) -> bool:
        self.current_sicko = None
        await message.reply("Shuffling sickos.")
        return True
    async def cmd_sicko_set(self, args: str, message: discord.Message) -> bool:
        newsicko = re.split(r"\s+", args)[0]
        if newsicko not in self.sickos.keys():
            await message.reply(f"Sicko `{newsicko}` not available.\nCurrently available sickos: {self.__sicko_list()}")
            return True
        self.current_sicko = newsicko
        await message.reply(f"Switched to `{newsicko}`.")
        return True
    async def cmd_cheevosfrom(self, args: str, message: discord.Message) -> bool:
        sargs = args.strip()
        if len(sargs) == 0:
            return False
        response = templater.CHEEVOS_FROM.generate(sargs)
        await message.reply(f"""Achievements from {sargs}: 
{response}""")
        return True
    def _register_commands(self) -> None:
        """Registers all command functions with our [[self.ctree]]."""
        self.ctree.add("help", [], "Show this help message.", self.cmd_help)
        self.ctree.add("amnesia", [], "Deletes all of the sickos' memories.", self.cmd_amnesia)
        self.ctree.add("responserate", ["rate"], 
                       lambda: f"Sets the percent of messages the sickos respond to, from 0 to 1. Currently set to {self.response_rate}, defaults to {consts.DEFAULT_RESPONSE_RATE}", 
                       self.cmd_responserate)
        self.ctree.add("sicko list", [], "Lists the available sickos", self.cmd_sicko_list) 
        self.ctree.add("sicko current", [], 
                       lambda: f"Lists the currently replying sicko. It is currently `{self.current_sicko}`", self.cmd_sicko_current) 
        self.ctree.add("sicko shuffle", [], "Sets the sickos to shuffle which one responds to a given message", self.cmd_sicko_shuffle) 
        self.ctree.add("sicko set", ["name"], "Sets the currently responding sicko to the given named sicko", self.cmd_sicko_set) 
        self.ctree.add("cheevosfrom", ["game title"], "What's the list of achievements from your favorite game?", self.cmd_sicko_set) 

    async def on_message(self, message: discord.Message) -> None:
        if message.author.id == self.user.id: # type: ignore
            L.info("Skipping our own message in on_message...")
            return
        L.debug(f'Checking prefix {self.ctree.prefix} against message {message.content}')
        if message.content.startswith(self.ctree.prefix):
            L.info("Got command message, forwarding to command processor...")
            await self.ctree.invoke(message)
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
