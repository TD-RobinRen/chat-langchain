import os
from pprint import pprint
import json
from typing import List
from pathlib import Path
from parser import parse_json_markdown
from operator import itemgetter

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import (
    PromptTemplate,
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
    SystemMessagePromptTemplate,
    FewShotChatMessagePromptTemplate
)
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

    for data in extracted_data:
        file_path = Path(f"./schema/transformed_components/{data['source']}.json")
        source_file = json.loads(file_path.read_text())

        batch_input.append({
            "source": json.dumps(extracted_data),
            "raw": json.dumps(data),
            "component_schema": json.dumps(source_file)
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
