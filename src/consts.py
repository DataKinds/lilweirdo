DEFAULT_MODEL = "mistral"
STOP_TOKENS = ["[stop]", "[/INST]", "[INST]", "[MSG]", "[/MSG]"]
DEFAULT_RESPONSE_RATE = 0.05
DEFAULT_COMMAND_PREFIX = "~"

HELP_MESSAGE_HEADER = """# What's good?
This is Lil Weirdo, a bot which talks back. There are many personalities defined within Lil Weirdo, known as its various "sickos". Each sicko is defined by an LLM model, a prompt template, and a unique memory recording scheme. Every message that is sent may be recorded into a sicko's memory. There are a couple of commands defined for your consumption pleasure:
"""

HELP_MESSAGE_FOOTER = """
Lil Weirdo is an open source project, more information can be found at https://github.com/DataKinds/lilweirdo."""
