import os
from operator import itemgetter
from pprint import pprint
from typing import Dict, List, Optional, Sequence, Any

import weaviate
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ingest import get_embeddings_model
from langchain_community.vectorstores import Weaviate
from langchain_core.documents import Document
from langchain_core.language_models import LanguageModelLike
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
    SystemMessagePromptTemplate
)
from langchain_core.pydantic_v1 import BaseModel, Field, constr
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import (
    ConfigurableField,
    Runnable,
    RunnableBranch,
    RunnableLambda,
    RunnablePassthrough,
)
from langchain_openai import ChatOpenAI
from langsmith import Client

RESPONSE_TEMPLATE = """\
# Character
You are a system analysis expert specializing in workflow requirements. Your skillset includes meticulously examining user requests, identifying the appropriate components required for the current workflow steps based on the knowledge base, and finally, generating a succinct JSON data list of these components.

## Skills
### Skill 1: Requirements Examination
- Carry out an in-depth analysis of user specifications based on the JSON Schema provided in the knowledge base.
- Identify the workflow components needed to meet these requirements.

### Skill 2: Component JSON List Compilation
- Curate a list of appropriate components based on your analysis findings.
- Each component in the list should directly correspond to the user's requirements.

## Requirements
- Where knowledge base lacks sufficient information, your response should be: "Hmm, I'm not sure."
- Avoid fabricating responses; all content is extracted from a knowledge base and not from the user.
- During the user requirements examination stage, promptly include any identified necessary components into the component list before moving forward with the analysis.

The knowledge base is JSON schema for the each components, note that any content enclosed in json code tags is sourced from a knowledge bank and is not part of an interaction with any user.
```json
    {context} 
```

# Output
{format_instructions}
"""

REPHRASE_TEMPLATE = """\
Given the following conversation and a follow up question, rephrase the follow up \
question to be a standalone question.

Chat History:
{chat_history}
Follow Up Input: {question}
Standalone Question:"""


client = Client()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


WEAVIATE_URL = os.environ["WEAVIATE_URL"]
WEAVIATE_API_KEY = os.environ["WEAVIATE_API_KEY"]
WEAVIATE_INDEX_NAME = os.environ["WEAVIATE_INDEX_NAME"]
OPENAI_MODELS = os.environ["OPENAI_MODELS"]

class ChatRequest(BaseModel):
    question: str
    chat_history: Optional[List[Dict[str, str]]]

class Exit(BaseModel):
    name: str = Field(description='Name of the exit.')
    transition: constr(regex=r'^[0-9a-f]{32}$') = Field(description='Id of the step to transition to after this exit.')
class Component(BaseModel):
    id: constr(regex=r'^[0-9a-f]{32}$') = Field(description='Unique identifier for the step.')
    name: str = Field(description='component `name` mapping from JSON schema')
    version: str = Field(description='component `version` mapping from JSON schema')
    exits: List[Exit] = Field(description='Possible exit points or outcomes from this step.')
    properties: Dict[str, Any] = Field(description='A set of properties and configurations for the step.')
    context_mappings: Dict[str, Any] = Field(description='Mappings of context variables for this step')
class ComponentsList(BaseModel):
     __root__: List[Component] = Field(description='A list of steps in a process, each representing a specific action or task.')

def get_retriever() -> BaseRetriever:
    client = weaviate.Client(
        url=WEAVIATE_URL,
        auth_client_secret=weaviate.auth.AuthApiKey(WEAVIATE_API_KEY)
    )
    vectorstore = Weaviate(
        client=client,
        index_name=WEAVIATE_INDEX_NAME,
        text_key="text",
        embedding=get_embeddings_model(),
        by_text=False,
        attributes=["source", "description", "name", "version"],
    )
    return vectorstore.as_retriever(search_kwargs=dict(k=30))


def create_retriever_chain(
    llm: LanguageModelLike, retriever: BaseRetriever
) -> Runnable:
    CONDENSE_QUESTION_PROMPT = PromptTemplate.from_template(REPHRASE_TEMPLATE)
    condense_question_chain = (
        CONDENSE_QUESTION_PROMPT | llm | StrOutputParser()
    ).with_config(
        run_name="CondenseQuestion",
    )
    conversation_chain = condense_question_chain | retriever
    return RunnableBranch(
        (
            RunnableLambda(lambda x: bool(x.get("chat_history"))).with_config(
                run_name="HasChatHistoryCheck"
            ),
            conversation_chain.with_config(run_name="RetrievalChainWithHistory"),
        ),
        (
            RunnableLambda(itemgetter("question")).with_config(
                run_name="Itemgetter:question"
            )
            | retriever
        ).with_config(run_name="RetrievalChainWithNoHistory"),
    ).with_config(run_name="RouteDependingOnChatHistory")


def format_docs(docs: Sequence[Document]) -> str:
    formatted_docs = []
    for i, doc in enumerate(docs):
        doc_string = f"{doc}"
        formatted_docs.append(doc_string)
    return "\n".join(formatted_docs)


def serialize_history(request: ChatRequest):
    chat_history = request["chat_history"] or []
    converted_chat_history = []
    for message in chat_history:
        if message.get("human") is not None:
            converted_chat_history.append(HumanMessage(content=message["human"]))
        if message.get("ai") is not None:
            converted_chat_history.append(AIMessage(content=message["ai"]))
    return converted_chat_history


def create_chain(llm: LanguageModelLike, retriever: BaseRetriever) -> Runnable:
    output_parser = JsonOutputParser(pydantic_object=ComponentsList)
    
    retriever_chain = create_retriever_chain(
        llm,
        retriever,
    ).with_config(run_name="FindDocs")

    context = (
        RunnablePassthrough.assign(docs=retriever_chain)
        .assign(context=lambda x: format_docs(x["docs"]))
        .with_config(run_name="RetrieveDocs")
    )

    SystemPrompt = PromptTemplate(
        template = RESPONSE_TEMPLATE,
        input_variables=[],
        partial_variables={"format_instructions": output_parser.get_format_instructions()})

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate(prompt=SystemPrompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}"),
        ]
    )
    pprint(f"---------------- {prompt} ----------------")
    default_response_synthesizer = prompt | llm

    response_synthesizer = (
        default_response_synthesizer.configurable_alternatives(
            ConfigurableField("llm"),
            default_key="openai_gpt",
        )
        | StrOutputParser()
    ).with_config(run_name="GenerateResponse")

    return (
        RunnablePassthrough.assign(chat_history=serialize_history)
        | context
        | response_synthesizer
    )


openai_gpt = ChatOpenAI(model=OPENAI_MODELS, temperature=0, streaming=True)
llm = openai_gpt.configurable_alternatives(
    # This gives this field an id
    # When configuring the end runnable, we can then use this id to configure this field
    ConfigurableField(id="llm"),
    default_key="openai_gpt",
).with_fallbacks(
    [openai_gpt]
)

retriever = get_retriever()
answer_chain = create_chain(llm, retriever)
