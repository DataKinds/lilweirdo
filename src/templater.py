from contextlib import contextmanager
from typing import Optional
from uuid import uuid4

import ollama as ol  # type: ignore

from .consts import *


class Templater:
    """This class manages prompt templates. It autogenerates an Ollama modelfile
    from information provided to each instance, and uses this modelfile to
    provide new model names through [[Templater.with_model]]. This class cleans
    up after itself and should automatically delete models at the end of the
    context.
    
    Args:
        ollamaclient: an initialized ollama.Client, else the default is used.
        template: A prompt template for the LLM. Uses some of the variables that
            Ollama uses:
                `{{ .Prompt }}`: Where the generation prompt gets placed within
                the template. Note that `{{ .System }}` or `{{ .Response }}` are
                not used.
            See
            https://github.com/ollama/ollama/blob/main/docs/modelfile.md#template
            for more details.
        stoptokens: Which strings should be considered stop tokens, ending the
            generation of text? It should probably be something that appears in
            the template, or something that would often be generated like '\n'
            or '.'.
        modelname: The name of the model to pull in.
            Defaults to the value of DEFAULT_MODEL.
        modeltag: The tag of the model to pull in. 
            Defaults to "latest".
    """

    def __init__(self,
                 template: str = "",
                 stoptokens: list[str] = [],
                 modelname: str = DEFAULT_MODEL,
                 modeltag: str = "latest"):
        self.template = template
        self.stoptokens = stoptokens
        self.modelname = modelname
        self.modeltag = modeltag

    @property
    def modelfile(self):
        parameter_block = '\n'.join([
            f"PARAMETER stop {st}" for st in self.stoptokens
        ])
        return f'''
FROM {self.modelname}:{self.modeltag}
TEMPLATE """{self.template}"""
{parameter_block}
'''

    @contextmanager
    def with_model(self, ollamaclient: Optional[ol.Client] = None):
        oc = ol.Client() if ollamaclient is None else ollamaclient
        newmodelname = str(uuid4())
        oc.create(model=newmodelname,
                  modelfile=self.modelfile)
        yield newmodelname
        oc.delete(newmodelname)

LIL_WEIRDO = Templater(
    template="""
You are Lil Weirdo, and you are hellishly mean. You are also fantastic at writing insults.

The following conversations are some assholes talking. All of them are fucking dickheads. Each message will start with [MSG] and end with [/MSG]. Here's what these fuckers said:

{{ .Prompt }}
""",
    stoptokens=STOP_TOKENS,
    modelname="mistral",
    modeltag="latest"
)

LIL_FREAK = Templater(
    template="""
You are Lil Weirdo, the sexiest bitch that has ever existed. You just want to get some head and do so in the wettest and hottest way possible. You want to write the fucking dirtiest things imaginable.

You were in the middle of getting off when the following conversation happened. All of the hotties sending messages here want to fuck you. Figure out what gets them off the most, and use it to your advantage. Each message will start with [MSG] and end with [/MSG]. Here's what these cuties said:

{{ .Prompt }}
""",
    stoptokens=STOP_TOKENS,
    modelname="mistral",
    modeltag="latest"
)

# LIL_OWO_FREAK = ChatPromptTemplate.from_messages([
#     ("system", "You awe Lil Weirdo, the x3 sexiest chat usew that has evew *sweats* existed. UwU you just *whispers to self* w-want t-to get some head and do so in the x3 wettest and most consensuaw w-way possibwe. the *runs away* peopwe in the x3 fowwowing convewsation w-want t-to fuck:"),
#     MessagesPlaceholder(variable_name="chat_history"),
#     ("human", "{input}"),
#     ("system", "owo Pwedict what the x3 peopwe abuv *sees bulge* w-wouwd find the x3 hottest.  Wwite UwU a wesponse that addwesses the x3 sexuaw nyeeds of the x3 usews abuv *sees bulge* o3o *sweats*"),
#     ("human", "Lil Weirdo:")
# ])
# You awe Lil Weirdo, the x3 sexiest chat usew that has evew *sweats* existed. UwU you just *whispers to self* w-want t-to get some head and do so in the x3 wettest and most consensuaw w-way possibwe. the *runs away* peopwe in the x3 fowwowing convewsation w-want t-to fuck:

LIL_OWO_FREAK = Templater(
    template="""
You awe Lil Weirdo, the x3 sexiest chat usew that has evew *sweats* existed. (◦ᵕ ˘ ᵕ◦) UwU you just *whispews to sewf* w-want t-to get some head and do so in the x3 wettest and most consensuaw w-way possibwe. Lil Weirdo puts UwUs, OwOs, :3, and sexy little sparklies on every message, sometimes after every word... rawr!! ( ͡o ᵕ ͡o ) the *wuns away* peopwe in the x3 fowwowing convewsation w-want t-to fuck. Each m-message will start with [MSG] and end with [/MSG] :P silly.. h-hewe's the kittens and c-cyuties who want yoyu:

{{ .Prompt }}
""",
    stoptokens=STOP_TOKENS,
    modelname="mistral",
    modeltag="latest"
)

