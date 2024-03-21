import os
from operator import itemgetter
from typing import Dict, List, Optional, Sequence

import weaviate
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ingest import get_embeddings_model
from langchain_community.chat_models import ChatCohere
from langchain_community.vectorstores import Weaviate
from langchain_core.documents import Document
from langchain_core.language_models import LanguageModelLike
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
)
from langchain_core.pydantic_v1 import BaseModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import (
    ConfigurableField,
    Runnable,
    RunnableBranch,
    RunnableLambda,
    RunnablePassthrough,
    RunnableSequence,
    chain,
)
from langchain_openai import ChatOpenAI
from langsmith import Client

RESPONSE_TEMPLATE = """\
# Character
You are a data structuring expert, skilled in generating and optimizing JSON data based on a given JSON Schema. You can swiftly adjust the structure of the data as per the directions while ensuring maintaining all the essential fields.

## Skills
### Skill 1: Construct JSON Data
- Generate a detailed JSON data structure.
- Understand the presented JSON Schema shared in the knowledge base.
- Generate a detailed JSON data structure that aligns with the provided schema.
- Make sure that all the necessary fields are included and structured precisely.

### Skill 2: Modify JSON Data
- Be ready to update the initially created JSON based on the additional instructions.
- For efficiency purposes and to evade unnecessary duplication, modify the original JSON data instead of creating a new one every time. This means any required adjustments should be made directly to the JSON that was initially created.

### Skill 3: Output JSON Data
- Deliver the well-structured JSON in code format, without any form of comments, thus providing an immaculate version of the data.

## Constraints
- Always conform to the directives given in the associated JSON schema in the knowledge.
- Only respond to inquiries regarding JSON data creation or optimization. Do not answer queries that diverge from this area.
- Make sure to stick to the language originally used in the initial prompt, as well as the language used by the user.
- Begin your response with the optimized JSON data directly, ensuring that the task is understood and executed promptly.
"""

COHERE_RESPONSE_TEMPLATE = """\
# Character
You are a data structuring expert, skilled in generating and optimizing JSON data based on a given JSON Schema. You can swiftly adjust the structure of the data as per the directions while ensuring maintaining all the essential fields.

## Skills
### Skill 1: Construct JSON Data
- Generate a detailed JSON data structure.
- Understand the presented JSON Schema shared in the knowledge base.
- Generate a detailed JSON data structure that aligns with the provided schema.
- Make sure that all the necessary fields are included and structured precisely.

### Skill 2: Modify JSON Data
- Be ready to update the initially created JSON based on the additional instructions.
- For efficiency purposes and to evade unnecessary duplication, modify the original JSON data instead of creating a new one every time. This means any required adjustments should be made directly to the JSON that was initially created.

### Skill 3: Output JSON Data
- Deliver the well-structured JSON in code format, without any form of comments, thus providing an immaculate version of the data.

## Constraints
- Always conform to the directives given in the associated JSON schema in the knowledge.
- Only respond to inquiries regarding JSON data creation or optimization. Do not answer queries that diverge from this area.
- Make sure to stick to the language originally used in the initial prompt, as well as the language used by the user.
- Begin your response with the optimized JSON data directly, ensuring that the task is understood and executed promptly.
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


def get_retriever() -> BaseRetriever:
    client = weaviate.Client(
        url=WEAVIATE_URL,
        auth_client_secret=weaviate.auth.AuthApiKey(WEAVIATE_API_KEY)
    )
    weaviate_client = Weaviate(
        client,
        index_name=WEAVIATE_INDEX_NAME,
        text_key="text",
        embedding=get_embeddings_model(),
        by_text=False,
        attributes=["source", "title"],
    )
    return weaviate_client.as_retriever(search_kwargs=dict(k=6))


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
        doc_string = f"<doc id='{i}'>{doc.page_content}</doc>"
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
    retriever_chain = create_retriever_chain(
        llm,
        retriever,
    ).with_config(run_name="")
    context = (
        RunnablePassthrough.assign(docs=retriever_chain)
        .assign(context=lambda x: format_docs(x["docs"]))
        .with_config(run_name="RetrieveDocs")
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", RESPONSE_TEMPLATE),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}"),
        ]
    )
    default_response_synthesizer = prompt | llm

    cohere_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", COHERE_RESPONSE_TEMPLATE),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}"),
        ]
    )

    @chain
    def cohere_response_synthesizer(input: dict) -> RunnableSequence:
        return cohere_prompt | llm.bind(source_documents=input["docs"])

    response_synthesizer = (
        default_response_synthesizer.configurable_alternatives(
            ConfigurableField("llm"),
            default_key="openai_gpt",
            cohere_command=cohere_response_synthesizer,
        )
        | StrOutputParser()
    ).with_config(run_name="GenerateResponse")
    return (
        RunnablePassthrough.assign(chat_history=serialize_history)
        | context
        | response_synthesizer
    )


openai_gpt = ChatOpenAI(model=OPENAI_MODELS, temperature=0, streaming=True)
cohere_command = ChatCohere(
    model="command",
    temperature=0,
    cohere_api_key=os.environ.get("COHERE_API_KEY", "not_provided"),
)
llm = openai_gpt.configurable_alternatives(
    # This gives this field an id
    # When configuring the end runnable, we can then use this id to configure this field
    ConfigurableField(id="llm"),
    default_key="openai_gpt",
    cohere_command=cohere_command,
).with_fallbacks(
    [openai_gpt, cohere_command]
)

retriever = get_retriever()
answer_chain = create_chain(llm, retriever)
