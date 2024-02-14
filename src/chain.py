from langchain.chains import create_history_aware_retriever
from langchain_community.llms import Ollama
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage

import logging

L = logging.getLogger(__name__)


class Sicko:
    """Implements a really mean AI."""
    def __init__(self):
        L.info("Initializing LC chain...")
        self.llm = Ollama(model = "mistral")
        self.mean_prompt = ChatPromptTemplate.from_messages([
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            ("human", "-----"),
            ("human", "Pretend you are hellishly mean. The conversation above is some shitbag named \"{username}\" talking. You are an asshole, but they're a bigger one. You write a horribly mean insult. Rip that dick \"{username}\" to shreds.")
        ])
        self.chain = create_history_aware_retriever(self.llm, StrOutputParser(), self.mean_prompt)
        L.info("LC chain initialized! Asking it how it feels to be alive...")
        L.info(self.chain.invoke(self.__invoke_args("The Creator", ["How does it feel to be alive?"])))


    def __invoke_args(self, username: str, messages: list[str]) -> str:
        if len(messages) < 2:
            message_history = [HumanMessage(content="")]
        else:
            message_history = [HumanMessage(content=msg) for msg in messages[:-1]]
        return {
            "chat_history": message_history,
            "input": messages[-1],
            "username": username
        }

    async def respond_to(self, username: str, messages: list[str]) -> str: 
        """Generates a mean message. Expects the most recent message to be last
        in the passed-in list. Expects a nonempty message list."""
        return await self.chain.ainvoke(self.__invoke_args(username, messages))
