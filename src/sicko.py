import logging
from typing import Type

import discord
import ollama as ol  # type: ignore

from .keeper import ConvoKeeper, Keeper
from .templater import LIL_WEIRDO, Templater

L = logging.getLogger(__name__)

class Sicko:
    """Implements a really mean AI.
    
    Args:
        ollama_client: An Ollama.Client, else the default is used.
        keeper: A Keeper class to initialize, serving as the memory of the AI.
        templater: A Templater, which controls the prompt template, stop 
            tokens, choice of model, and other options.
    """
    def __init__(self,
                 ollamaclient: ol.Client = None,
                 keeper: Type[Keeper] = ConvoKeeper, 
                 templater: Templater = LIL_WEIRDO):
        L.info("Initializing LC chain...")
        L.info(f"Memory keeper: {keeper}")
        L.info(f"Templater: {templater}")
        self.llm: ol.Client = ol.Client() if ollamaclient is None else ollamaclient
        self.templater: Templater = templater
        self.keeper: Keeper = keeper()
        self.starttok = "[MSG]"
        self.stoptok = "[/MSG]"
        L.info("LC chain initialized! Asking it how it feels to be alive...")
        L.info(self.__generate(f"{self.starttok} God: How does it feel to be alive? {self.stoptok}\n{self.starttok} Lil Weirdo:"))

    def __prompt(self, user: discord.Member | discord.User) -> str:
        messages = '\n'.join(self.keeper.get_ai_ingestible(user.id, self.starttok, self.stoptok))
        prompt = f"{messages}\n{self.starttok} Lil Weirdo:"
        L.info(f"Generated prompt: {prompt}")
        return prompt

    def __generate(self, prompt: str) -> str:
        with self.templater.with_model(self.llm) as modelname:
            response: str = self.llm.generate(
                model=modelname,
                prompt=prompt
            )['response']
            L.info(f"Generated response: {response}")
            return response

    async def respond_to(self, user: discord.Member | discord.User) -> str: 
        """Generates a mean message. Expects the most recent message to be last
        in the passed-in list. Expects a nonempty message list. Will crop the
        message such that it doesn't generate any extra users in the
        conversation (so the message ends before something like "Human:").
        
        Args:
            user is the person that invoked the AI"""
        return self.__generate(self.__prompt(user))
