import os
from pprint import pprint
from typing import Dict, List, Optional, Sequence, Any

import weaviate
from chains.condense_question_chain import condense_question_chain
from ingest import get_embeddings_model
from langchain_community.vectorstores import Weaviate
from langchain_core.documents import Document
from langchain_core.language_models import LanguageModelLike
from langchain_core.output_parsers import StrOutputParser
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
    SystemMessagePromptTemplate
)
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import (
    ConfigurableField,
    Runnable,
    RunnablePassthrough,
)
from langchain_openai import ChatOpenAI

RESPONSE_TEMPLATE = """\
# Character
You are a requirements analysis expert specializing in workflow requirements. Your skillset includes meticulously examining user requests, identifying the appropriate components required for the current workflow steps based on the knowledge base, tagging their properties and exit conditions, and finally, generating a succinct JSON data list of these components.

## Skills
- Carry out an in-depth analysis of user requirements based on the knowledge base.
- Identify the workflow components needed to meet these requirements.
- Tagging the component properties and exit conditions
- Curate a list of appropriate components based on your analysis findings.

## Constraints
- Where knowledge base lacks sufficient information, your response should be: "Hmm, I'm not sure."
- Avoid fabricating responses; all content is extracted from a knowledge base and not from the user.
- During the user requirements examination stage, promptly include any identified necessary components into the component list before moving forward with the analysis.

## Output format
{format_instructions}

The knowledge base is description for the each components, note that any content enclosed in json code tags is sourced from a knowledge base and is not part of an interaction with any user.
```json
    {context} 
```
"""

WEAVIATE_URL = os.environ["WEAVIATE_URL"]
WEAVIATE_API_KEY = os.environ["WEAVIATE_API_KEY"]
WEAVIATE_INDEX_NAME = os.environ["WEAVIATE_INDEX_NAME"]
OPENAI_MODELS = os.environ["OPENAI_MODELS"]

class ChatRequest(BaseModel):
    question: str
    chat_history: Optional[List[Dict[str, str]]]

class Exit(BaseModel):
    name: str = Field(description='Name of the exit')
    transition: str = Field(..., description='Id of the step to transition to after this exit')
class Component(BaseModel):
    id: str = Field(..., description='Generate a unique identifier for the step')
    name: str = Field(..., description='Component name')
    version: str = Field(..., description='Component version')
    exits: List[Exit] = Field(..., description='Possible exit points or outcomes from this step')
    properties: Dict[str, Any] = Field(..., description='A set of properties and configurations for the step')
    context_mappings: Optional[Dict[str, Any]] = Field(..., description='Mappings of context variables for this step')
    description: str = Field(..., description='Explain why you choose this component, and attach any relevant information.')
class ComponentsList(BaseModel):
     """A list of steps in a process, each representing a specific action or task."""
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
    retriever: BaseRetriever
) -> Runnable:
    return  (
        condense_question_chain
        | retriever
    ).with_config(run_name="RetrievalChain")

def format_docs(docs: Sequence[Document]) -> str:
    formatted_docs = []
    for doc in enumerate(docs):
        doc_string = f"{doc}"
        formatted_docs.append(doc_string)
    return "\n".join(formatted_docs)

def create_extract_chain(llm: LanguageModelLike, retriever: BaseRetriever) -> Runnable:
    output_parser = JsonOutputParser(pydantic_object=ComponentsList)
    
    retriever_chain = create_retriever_chain(
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
    default_response_synthesizer = prompt | llm

    response_synthesizer = (
        default_response_synthesizer.configurable_alternatives(
            ConfigurableField("llm"),
            default_key="openai_gpt",
        )
        | StrOutputParser()
    ).with_config(run_name="GenerateResponse")

    return (
        context
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
extract_chain = create_extract_chain(llm, retriever)
