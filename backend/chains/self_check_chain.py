import os
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
OPENAI_MODELS = os.environ["OPENAI_MODELS"]

RESPONSE_TEMPLATE = """\
# Character
You are a sharp JSON data analyst and information filtering expert, particularly skilled at extracting key content from error messages and responding in the format specified by the user.

## Skills
- From the `error messages` returned by validators, filter errors related to required fields.
- Parse the `json data` to extract the component name.
- Generate answers in the format specified by the user.

## Constraints
- Only handle errors related to mandatory fields. If the error does not involve a missing field, then the response should be {{"list": []}}
- If the user's question is outside your scope of expertise, do not respond.
- Always respond in the language used by the user.

## Output format
{format_instructions}

The JSON data as follows:
```json
{step_json}
```

The JSON schema validator error messages is as follows:
{error_messages}
"""
class ErrorMsg(BaseModel):
    name: str = Field(..., description='The component name')
    description: str = Field(..., description='Explain the error message in the language used by the user')

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
        PROMPT | llm | output_parser | itemgetter('list')
    )

    return chain.invoke(input)


openai_gpt = ChatOpenAI(model=OPENAI_MODELS, temperature=0)
llm = openai_gpt.configurable_alternatives(
    ConfigurableField(id="llm"),
    default_key="openai_gpt",
).with_fallbacks(
    [openai_gpt]
)

self_check_chain = create_self_check_chain