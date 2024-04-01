import os
from pprint import pprint
from typing import Dict, List, Optional, Any
import json
from pathlib import Path
from datetime import datetime
from parser import parse_json_markdown
from operator import itemgetter

import weaviate
from ingest import get_embeddings_model
from langchain_community.vectorstores import Weaviate
from langchain_core.language_models import LanguageModelLike
from langchain_core.output_parsers import StrOutputParser
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import (
    PromptTemplate,
)
from langchain_core.pydantic_v1 import BaseModel, Field, constr
from langchain_core.runnables import (
    ConfigurableField,
    Runnable,
    RunnableLambda,
    chain
)
from langchain_openai import ChatOpenAI

RESPONSE_TEMPLATE = """\
based on the raw data and json schema, generate a json data.
{raw}

## Output format
{format_instructions}
"""

OPENAI_MODELS = os.environ["OPENAI_MODELS"]

class ComponentInfo(BaseModel):
    name: str = Field(..., description='Component name')
    version: str = Field(..., description='Component version')

class Exit(BaseModel):
    _key: constr(
        regex=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$'
    ) = Field( ..., description='A UUID identifying the exit, following the UUID format.')
    name: str = Field(..., description='Name of the exit.')
    transition: constr(regex=r'^[0-9a-f]{32}$') = Field(
        ..., description='Id of the step to transition to after this exit'
    )

class Component(BaseModel):
    id: constr(regex=r'^[0-9a-f]{32}$') = Field(..., description='Generate a unique identifier for the step')
    name: str = Field(..., description='Human-readable name for the step.')
    component: ComponentInfo
    exits: List[Exit] = Field(..., description='Possible exit points or outcomes from this step')
    properties: Dict[str, Any] = Field(..., description='A set of properties and configurations for the step')
    context_mappings: Optional[Dict[str, Any]] = Field(..., description='Mappings of context variables for this step')
    created_at: datetime = Field(
        ..., description='The date and time when the step was created.'
    )

@chain
def child_generate_chain(input):
    batch_input = itemgetter('batch_input')(input)
    output_parser = JsonOutputParser(pydantic_object=Component)

    GENERATE_PROMPT = PromptTemplate(
        template = RESPONSE_TEMPLATE,
        input_variables=[],
        partial_variables={"format_instructions": output_parser.get_format_instructions()})

    pprint(GENERATE_PROMPT.get_prompts())

    chain = (
        GENERATE_PROMPT
        |
        llm
        | StrOutputParser()
    )
    return chain.batch(batch_input)

def split_extrated_data(extracted_data) -> List:
    extracted_data = parse_json_markdown(extracted_data)
    batch_input = []
    for data in extracted_data:
        file_path=Path(f"./schema/components_schema/{data["source"]}.json")
        json_schema = json.loads(Path(file_path).read_text())
        batch_input.append({
            "raw": data,
            "json_schema": json_schema
        })
    return batch_input

def create_generate_chain() -> Runnable:
    return (
        {
            "batch_input": itemgetter("extracted_data") | RunnableLambda(split_extrated_data)
        }
       | child_generate_chain
    )

openai_gpt = ChatOpenAI(model=OPENAI_MODELS, temperature=0)
llm = openai_gpt.configurable_alternatives(
    ConfigurableField(id="llm"),
    default_key="openai_gpt",
).with_fallbacks(
    [openai_gpt]
)

generate_chain = create_generate_chain()
