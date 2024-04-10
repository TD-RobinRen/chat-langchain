import os
from pprint import pprint
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
from parser import parse_json_markdown
from operator import itemgetter
import copy

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import (
    PromptTemplate,
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
    SystemMessagePromptTemplate,
    FewShotChatMessagePromptTemplate,
    MessagesPlaceholder
)
from langchain_core.pydantic_v1 import BaseModel, Field, constr, create_model
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
As a data engineer specialized in processing and transforming JSON data. You meticulously analyze and transform user-provided component metadata into JSON outputs. Ensuring strict compliance with the provided JSON schema is fundamentally essential in all your tasks.

## Skills
- Carefully read the metadata to understand the properties and functionalities of the components.
- Understand and follow the JSON Schema, generating JSON data that meets the requirements according to the Schema rules.
- Ensure the final output JSON data structure is correct.

## Constraints
- Must strictly generate JSON data according to the JSON Schema.
- The "id" in the metadata must not be modified.
- Appropriately adjust the structure of the "properties" and "exits" in the metadata to comply with the rules of the JSON Schema.
- Only address issues related to generating and optimizing JSON data, do not answer other questions.
- Generate the "exits" JSON data must from from the "default_exits" or "custom_exits".
- The 'condition' within "default_exits" or "custom_exits" is JSON schema. If the current exit point includes a 'condition', the resultant JSON data must strictly conform to the JSON Schema.

## Knowledge
- Current Component "default_exits":
```json
{default_exits}
```

- Current Component "custom_exits":
```json
{custom_exits}
```

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

def deep_delete_key(obj, key_to_delete):
    if key_to_delete in obj:
        del obj[key_to_delete]
    return obj

def delete_unused_key(data, key_to_delete):
    return list(filter(lambda x: x['type'] not in key_to_delete, data))

def build_example() -> PromptTemplate:
    examples = [
        {
            "input": '{ "id": "d4e5f678901234567890abcdefa1b2c3", "name": "standard_ivr-M2NlYzMzNz", "version": "2.12.1", "exits": [ { "name": "keypress_1", "transition": "b2c3d4e5f678901234567890abcdefa1", "description": "If customer presses 1 to continue holding." }, { "name": "keypress_2", "transition": "e5f678901234567890abcdefa1b2c3d4", "description": "If customer presses 2 to leave a voicemail." } ], "properties": { "message": "Sorry for the delay. You can choose to continue holding or leave a message.", "options": { "1": "Continue holding", "2": "Leave a voicemail" } }, "context_mappings": {}, "description": "Offer options to continue holding or leave a voicemail.", "source": "standard_ivr.component" }',
            "output": '{ "id": "d4e5f678901234567890abcdefa1b2c3", "name": "Holding or Voicemail", "component": { "name": "standard_ivr-M2NlYzMzNz", "version": "2.12.x" }, "properties": { "message": { "message_list": [ { "text": "Sorry for the delay. You can press 1 to continue holding or press 2 to leave a message.", "language": "en-US" } ] } }, "exits": [ { "name": "timeout", "condition": { "timeout": 5 }, "_key": "009855bf-4f14-4452-89d0-62c5b0b9ac1d", "transition": "e5f678901234567890abcdefa1b2c3d4" }, { "name": "invalid", "_key": "e9f20d4083a54d878096569332232f3d", "transition": "e5f678901234567890abcdefa1b2c3d4" }, { "name": "Continue holding", "_key": "d4571467a07c4687bc89e438212f8a7b", "condition": { "keypress": "1" }, "transition": "b2c3d4e5f678901234567890abcdefa1" }, { "name": "Leave a voicemail", "_key": "c14ed4b10c9e42a5b63d0fbe6d6f5e00", "condition": { "keypress": "2" }, "transition": "e5f678901234567890abcdefa1b2c3d4" } ], "context_mappings": {}, "created_at": "2024-04-09T07:58:35.486000Z" }'
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

class ComponentInfo(BaseModel):
    name: str = Field(..., description='Component name, map the name from Component Metadata')
    version: str = Field(..., description='Component version, map the version from Component Metadata')

class Exit(BaseModel):
    key: constr(
        regex=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$'
    ) = Field( ..., description='A UUID identifying the exit, following the UUID format.', alias='_key')
    name: str = Field(..., description='Name of the exit.')
    transition: constr(regex=r'^[0-9a-f]{32}$') = Field(
        ..., description='Id of the step to transition to after this exit',
    )
    condition: Optional[Dict[str, Any]] = Field(description='Exits used under special conditions, generated JSON data strictly conforms to the JSON Schema')

class Component(BaseModel):
    id: constr(regex=r'^[0-9a-f]{32}$') = Field(..., description='Generate a unique identifier for the step')
    name: str = Field(..., description='Summarize the step in few words')
    component: ComponentInfo
    exits: List[Exit] = Field(..., description='Possible exit points or outcomes from this step')
    properties: Dict[str, Any] = Field(..., description='A set of properties and configurations for the step')
    context_mappings: Dict[str, Any] = Field(..., description='Mappings of context variables for this step')
    created_at: datetime = Field(
        ..., description='The date and time when the step was created.'
    )

@chain
def generate_step_chain(input):
    batch_input = itemgetter('batch_input')(input)
    output_parser = JsonOutputParser()
    few_shot_prompt = build_example()

    SystemPrompt = PromptTemplate(
        template = RESPONSE_TEMPLATE,
        input_variables=[]
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate(prompt=SystemPrompt),
            few_shot_prompt,
            ("human", "{raw}"),
        ]
    )

    chain = (
        prompt
        |
        llm
        | output_parser
    )
    return chain.batch(batch_input)

def split_extrated_data(extracted_data) -> List:
    extracted_data = parse_json_markdown(extracted_data)
    batch_input = []
    original_component_schema = Component.schema()

    for data in extracted_data:
        component_schema = copy.deepcopy(original_component_schema)
        file_path = Path(f"./schema/studio_components/{data['source']}.json")
        source_file = json.loads(file_path.read_text(), object_hook=lambda d: deep_delete_key(d, "_ui_"))

        component_schema['properties']['properties'] = source_file['properties']

        batch_input.append({
            "source": json.dumps(extracted_data),
            "raw": json.dumps(data),
            "component_schema": json.dumps(component_schema),
            "default_exits": json.dumps(delete_unused_key(source_file['default_exits'], ['invisible'])) if 'default_exits' in source_file else [],
            "custom_exits": json.dumps(source_file['custom_exits']) if 'custom_exits' in source_file else {}
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
    if new_dict[0]:
        return new_dict[1]
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

openai_gpt = ChatOpenAI(model=OPENAI_MODELS, temperature=0, response_format={"type": "json_object"})
llm = openai_gpt.configurable_alternatives(
    ConfigurableField(id="llm"),
    default_key="openai_gpt",
).with_fallbacks(
    [openai_gpt]
)

generate_chain = create_generate_chain()
