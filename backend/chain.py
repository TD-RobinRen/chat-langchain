from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.pydantic_v1 import BaseModel
from langchain_core.runnables import (
    Runnable,
    RunnablePassthrough,
    RunnableBranch,
    RunnableLambda,
    chain,
)
from langsmith import Client

from typing import Dict, List, Optional

from chains.extract_chain import extract_chain
from chains.generate_chain import generate_chain
from chains.output_chain import output_chain

from chains.generate_diff_chain import generate_diff_chain

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

class ChatRequest(BaseModel):
    question: str
    chat_history: Optional[List[Dict[str, str]]]
    diff_json: Optional[object]
    chat_type: Optional[str]
    component_list: Optional[List[str]]

def serialize_history(request: ChatRequest):
    chat_history = request["chat_history"] or []
    converted_chat_history = []
    for message in chat_history:
        if message.get("human") is not None:
            converted_chat_history.append(HumanMessage(content=message["human"]))
        if message.get("ai") is not None:
            converted_chat_history.append(AIMessage(content=message["ai"]))
    return converted_chat_history

def route_chain(input) -> Runnable:
    print(f"---------------------->>>>{input['chat_type']}")
    if input["chat_type"] == "diff":
        return generate_diff_chain
    elif input["chat_type"] == "generate":
        return generate_flow_chain()
        

def create_main_chain() -> Runnable:
    return RunnableLambda(route_chain)

def generate_flow_chain() -> Runnable:
    result = (
        RunnablePassthrough.assign(chat_history=serialize_history)
        |
        {
            "extracted_data": extract_chain
        }
        |
        generate_chain
        |
        output_chain
    )
    return result

main_chain = create_main_chain()
