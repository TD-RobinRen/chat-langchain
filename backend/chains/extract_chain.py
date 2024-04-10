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
    SystemMessagePromptTemplate,
    FewShotChatMessagePromptTemplate
)
from langchain_core.pydantic_v1 import BaseModel, Field, constr
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
    transition: constr(regex=r'^[0-9a-f]{32}$') = Field(..., description='Id of the step to transition to after this exit')
    description: str = Field(..., description='Summarize the conditions for this exit points, and attach any relevant information.')
class Component(BaseModel):
    id: constr(regex=r'^[0-9a-f]{32}$') = Field(..., description='Generate a unique identifier for the step')
    name: str = Field(..., description='Component name')
    version: str = Field(..., description='Component version')
    exits: List[Exit] = Field(..., description='Possible exit points or outcomes from this step')
    properties: Dict[str, Any] = Field(..., description='A set of properties and configurations for the step')
    context_mappings: Optional[Dict[str, Any]] = Field(description='Mappings of context variables for this step')
    description: str = Field(..., description='Summarize why you choose this component, and attach any relevant information.')
    source: str = Field(..., description='Component source')
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
        attributes=["source", "name", "version"],
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

def build_example() -> PromptTemplate:
    examples = [
        {
            "input": "Create a initialize flow with inbound voice call, the name is chatter box demo. Afterward I want to create a workflow using the following steps: after the voice call incoming, it should be Request an assignment and dial the agents return for this interaction and assign to a ring group, the ring groups name is test.",
            "output": '[ { "id": "994aaf1e94a54043878add8502d518a4", "name": "inbound_voice-ZjE1ZjM0MG", "version": "1.3.0", "exits": [ { "name": "ok", "transition": "c819e33e451b4ca99e53c959a5c8322c", "description": "If the component succeeds" } ], "properties": {}, "context_mappings": {}, "description": "Initial component for incoming call flow definitions for the `chatter box demo`.", "source": "incoming_call.component" }, { "id": "c819e33e451b4ca99e53c959a5c8322c", "name": "assignment_and_dial-M2JhZTViYT", "version": "3.23.1", "exits": [ { "name": "call_finished", "transition": "f8994967f57440bea18b095a14879172", "description": "There was a successful match and a conversation with an agent has finished." }, { "name": "call_no_answer", "transition": "69e6a43f0d50484f8c4fd6ece395a64f", "description": "There was at least one successful dial attempt but no agent was available." } ], "properties": { "ring_group": "test" }, "context_mappings": {}, "description": "Request an assignment and dial the agents return for this interaction and assign to a ring group named `test`.", "source": "assignment_and_dial.component" } ]'
        }
    ]
    example_prompt = ChatPromptTemplate.from_messages(
        [
            ("human", "{input}"),
            ("ai", "{output}"),
        ]
    )
    return FewShotChatMessagePromptTemplate(
        example_prompt=example_prompt,
        examples=examples,
    )

def create_extract_chain(llm: LanguageModelLike, retriever: BaseRetriever) -> Runnable:
    output_parser = JsonOutputParser(pydantic_object=ComponentsList)
    few_shot_prompt = build_example()
    
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
            few_shot_prompt,
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


openai_gpt = ChatOpenAI(model=OPENAI_MODELS, temperature=0)
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
