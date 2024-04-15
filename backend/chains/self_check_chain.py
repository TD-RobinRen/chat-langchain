from operator import itemgetter
from langchain_openai import ChatOpenAI
import json
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import (
    ConfigurableField,
    RunnablePassthrough,
    chain
)
from jsonschema import Draft7Validator
from typing import List
from langchain_core.pydantic_v1 import BaseModel, Field

RESPONSE_TEMPLATE = """\
# Character
You are an outstanding JSON data expert, skilled at extracting key information from JSON schema validator error messages, with a focus on identifying errors related to missing fields. You accurately inform users about the missing information needed to fill.

## Skills
- Detailed parsing of JSON schema validator error messages, focusing on identifying missing required fields.
- Accurately and concisely listing the missing required fields based on the error messages.

## Constraints
- Discussion is limited to topics related to JSON data and JSON schema validator error messages.
- Maintain focus on error messages, avoiding other discussions.
- Always maintain accurate and clear communication.
- Please focusing on the errors related to field omission.

## Output format
{format_instructions}

The JSON data as follows:
```json
{step_json}
```

The JSON schema validator error message is as follows:
{error_messages}
"""
class ErrorMsg(BaseModel):
    name: str = Field(..., description='The name of from JSON data')
    description: str = Field(..., description='Summarize the error message')

class ErrorMsgList(BaseModel):
     list: List[ErrorMsg]

def validateStep(component_schema, step_json):
    validator = Draft7Validator(component_schema)
    errors = list(validator.iter_errors(step_json))
    error_messages = []
    if errors:
        for error in errors:
            error_messages.append(error.message)
    return error_messages

@chain
def create_self_check_chain(input):
    component_schema = json.loads(itemgetter('component_schema')(input))
    step_json = itemgetter('step_json')(input)

    output_parser = JsonOutputParser(pydantic_object=ErrorMsgList)

    error_messages = validateStep(component_schema, step_json)

    PROMPT = PromptTemplate(
        template = RESPONSE_TEMPLATE,
        input_variables=[],
        partial_variables={"format_instructions": output_parser.get_format_instructions()})

    if len(error_messages) == 0:
        return []

    chain = (
        RunnablePassthrough.assign(error_messages= lambda x: error_messages)
        |
        PROMPT | llm | output_parser
    )

    return chain.invoke(input)


openai_gpt = ChatOpenAI(model="gpt-4-0125-preview", streaming=False)
llm = openai_gpt.configurable_alternatives(
    ConfigurableField(id="llm"),
    default_key="openai_gpt",
).with_fallbacks(
    [openai_gpt]
)

self_check_chain = create_self_check_chain