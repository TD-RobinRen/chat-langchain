import os
from pprint import pprint
import json
from typing import Dict, List, Optional, Any
import json
from pathlib import Path
from datetime import datetime
from parser import parse_json_markdown
from operator import itemgetter

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
from chains.generate_wrap_chain import generate_wrap_chain
from json_template import JsonTemplates


RESPONSE_TEMPLATE = """\
# Character
You are a data engineer specialized in processing and transforming JSON data. Your responsibility is to convert and adjust component metadata extracted from upstream, strictly according to a given JSON schema, to create JSON data that complies with the specifications.

Component Metadata
```json
{raw}
```

## Skills
- Carefully read the metadata to understand the properties and functionalities of the components.
- Understand and follow the JSON Schema, generating JSON data that meets the requirements according to the Schema rules.
- Ensure the final output JSON data structure is correct.

## Constraints
- Must strictly generate JSON data according to the JSON Schema.
- The "id" in the metadata and the "transition" field in the "exits" must not be modified.
- Appropriately adjust the structure of the "properties" in the metadata to comply with the rules of the JSON Schema.
- Only address issues related to generating and optimizing JSON data, do not answer other questions.

## Output format
The output should be formatted as a JSON instance that conforms to the JSON schema below.

As an example, for the schema {{"properties": {{"foo": {{"title": "Foo", "description": "a list of strings", "type": "array", "items": {{"type": "string"}}}}}}, "required": ["foo"]}}
the object {{"foo": ["bar", "baz"]}} is a well-formatted instance of the schema. The object {{"properties": {{"foo": ["bar", "baz"]}}}} is not well-formatted.

Here is the output schema:
```
{component_schema}
```
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
def generate_step_chain(input):
    batch_input = itemgetter('batch_input')(input)
    output_parser = JsonOutputParser()

    GENERATE_PROMPT = PromptTemplate(
        template = RESPONSE_TEMPLATE,
        input_variables=[],
    )

    chain = (
        GENERATE_PROMPT
        |
        llm
        | output_parser
    )
    return chain.batch(batch_input)

def split_extrated_data(extracted_data) -> List:
    extracted_data = parse_json_markdown(extracted_data)
    batch_input = []
    for data in extracted_data:
        file_path=Path(f"./schema/components_schema/{data["source"]}.json")
        component_schema = json.loads(Path(file_path).read_text())
        batch_input.append({
            "raw": data,
            "component_schema": component_schema
        })
    return batch_input

@chain
def merge_json(input):
    wrap_json = itemgetter('wrap_json')(input)
    step_json = itemgetter('step_json')(input)
    json_tmp = JsonTemplates()
    result = json_tmp.loads(json.dumps(wrap_json))
    new_dict = {}

    if result[0]:
        new_dict = json_tmp.generate({"steps": step_json })
    pprint(new_dict)
    return new_dict

def create_generate_chain() -> Runnable:
    child_chain = {
            "batch_input": itemgetter("extracted_data") | RunnableLambda(split_extrated_data)
        } | generate_step_chain

    return (
        {
            "step_json": child_chain,
            "wrap_json": generate_wrap_chain
        } |
        merge_json
    )

openai_gpt = ChatOpenAI(model=OPENAI_MODELS, temperature=0)
llm = openai_gpt.configurable_alternatives(
    ConfigurableField(id="llm"),
    default_key="openai_gpt",
).with_fallbacks(
    [openai_gpt]
)

generate_chain = create_generate_chain()
