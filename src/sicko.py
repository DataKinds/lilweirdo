import logging
import re
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from itertools import islice
from typing import Type

import discord
import ollama as ol  # type: ignore
from langchain.chains import create_history_aware_retriever
from langchain_community.llms import Ollama
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from .consts import DEFAULT_MODEL
from .keeper import ConvoKeeper, Keeper
from .templater import LIL_OWO_FREAK, LIL_WEIRDO, Templater

L = logging.getLogger(__name__)

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
                 keeper: Type[Keeper] = ConvoKeeper, 
                 templater: Templater = LIL_WEIRDO):
        L.info("Initializing LC chain...")
        L.info(f"Memory keeper: {keeper}")
        L.info(f"Templater: {templater}")
        self.llm: ol.Client = ol.Client()
        self.templater: Templater = templater
        self.keeper: Keeper = keeper()
        L.info("LC chain initialized! Asking it how it feels to be alive...")

    def __prompt(self, user: discord.Member | discord.User) -> str:
        messages = '[stop]\n'.join(self.keeper.get_ai_ingestible(user.id))
        return f"{messages}\nLil Weirdo:"

    async def respond_to(self, user: discord.Member | discord.User) -> str: 
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
