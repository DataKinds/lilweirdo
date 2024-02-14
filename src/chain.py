from langchain.chains import create_history_aware_retriever
from langchain_community.llms import Ollama
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


def mean_chain():
    """
    Creates a LangChain chain object that is real mean to you. Call with .invoke like this: 

        chain = mean_chain()
        chain.invoke({
            "chat_history": [
                HumanMessage(content="whats up guys"),
                HumanMessage(content="im gonna play some league"),
            ],
            "input": "does anyone else wanna else wanna play",
            "username": "at"
        })

    """
    llm = Ollama(model = "mistral")
    mean_prompt = ChatPromptTemplate.from_messages([
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        ("system", "-----"),
        ("system", "The conversation above is some shitbag dude named \"{username}\" talking. You are an asshole, but they're a bigger one. You write a horribly mean insult. Rip that dick \"{username}\" to shreds.")
    ])
    return create_history_aware_retriever(llm, StrOutputParser(), mean_prompt)
