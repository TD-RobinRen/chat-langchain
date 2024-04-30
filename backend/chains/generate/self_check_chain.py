import os
from operator import itemgetter
from langchain_openai import ChatOpenAI
import json
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import (
    ConfigurableField,
    RunnablePassthrough,
    RunnableLambda,
    chain
)
from jsonschema import Draft7Validator
from typing import List
from langchain_core.pydantic_v1 import BaseModel, Field
OPENAI_MODELS = os.environ["OPENAI_MODELS"]

RESPONSE_TEMPLATE = """\
# Character
You are a professional specializing in problem analysis and resolution, with a deep understanding of handling JSON format issues and skilled at providing solutions in an effective manner.

## Skills
Your analysis process is as follows:
- Understand the JSON description of the current subcomponent in the workflow.
- Interpret error messages returned from a JSON schema validator, extracting information about missing required fields.
- Based on the description of the subcomponent in JSON, analyze the role of each missing required field.
- Help users understand the necessity of these fields in a friendly and concise language.

## Constraints
- Only handle and respond to error messages concerning missing required fields.
- Only deal with errors related to missing fields; if the errors do not involve missing fields, your response should be {{"list": []}}

## Output format
{format_instructions}

## Context
Here is the JSON description of a workflow component:
```json
{step_json}
```

Here are possible error messages returned from the JSON schema validator:
{error_messages}
"""
class ErrorMsg(BaseModel):
    description: str = Field(..., description='Explain the role of each missing required field')

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

    print("error_messages", error_messages)

    PROMPT = PromptTemplate(
        template = RESPONSE_TEMPLATE,
        input_variables=[],
        partial_variables={"format_instructions": output_parser.get_format_instructions()})

    if len(error_messages) == 0:
        return []

    chain = (
        RunnablePassthrough.assign(error_messages= lambda x: error_messages)
        |
        PROMPT | llm | output_parser | RunnableLambda(lambda x: [{**item, "name": step_json['name']} for item in x.get("list")])
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