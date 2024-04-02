from typing import Dict, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from chains.extract_chain import extract_chain
from chains.generate_chain import generate_chain
from chains.generate_wrap_chain import generate_wrap_chain
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.pydantic_v1 import BaseModel
from langchain_core.runnables import (
    Runnable,
    RunnablePassthrough,
)
from langsmith import Client

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

class ChatRequest(BaseModel):
    question: str
    chat_history: Optional[List[Dict[str, str]]]

def serialize_history(request: ChatRequest):
    chat_history = request["chat_history"] or []
    converted_chat_history = []
    for message in chat_history:
        if message.get("human") is not None:
            converted_chat_history.append(HumanMessage(content=message["human"]))
        if message.get("ai") is not None:
            converted_chat_history.append(AIMessage(content=message["ai"]))
    return converted_chat_history

def create_chain() -> Runnable:
    result = (
        RunnablePassthrough.assign(chat_history=serialize_history)
        | 
        {
            "extracted_data": extract_chain
        }
        |
        generate_chain
    )
    return result

answer_chain = create_chain()
