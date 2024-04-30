from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from langchain_core.pydantic_v1 import BaseModel
from langchain_core.runnables import Runnable, RunnableLambda
from langsmith import Client

from typing import Dict, List, Optional

from chains.generate.main import generate_chain
from chains.general_chain import general_chain
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
    flow_json: Optional[object]

def route_chain(input) -> Runnable:
    print(f"---------------------->>>>{input['chat_type']}")
    if input["chat_type"] == "diff":
        return generate_diff_chain
    elif input["chat_type"] == "generate":
        return generate_chain
    else:
        return general_chain

def create_main_chain() -> Runnable:
    return RunnableLambda(route_chain)

main_chain = create_main_chain()
