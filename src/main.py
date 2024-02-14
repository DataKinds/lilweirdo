import discord
from langchain_core.messages import HumanMessage

from .chain import mean_chain


def main():
    print(mean_chain().invoke({
        "chat_history": [
            HumanMessage(content="whats up guys"),
            HumanMessage(content="im gonna play some league"),
        ],
        "input": "does anyone else wanna else wanna play",
        "username": "at"
    }))

if __name__ == "__main__":
    main()