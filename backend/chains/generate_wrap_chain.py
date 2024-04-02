import os
from typing import Dict, Optional, Any
from langchain_core.language_models import LanguageModelLike
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import (
    PromptTemplate,
)

from datetime import datetime
from enum import Enum

from pydantic.v1 import BaseModel, Field, constr
from langchain_core.runnables import (
    ConfigurableField,
)
from langchain_openai import ChatOpenAI

OPENAI_MODELS = os.environ["OPENAI_MODELS"]

WRAP_TEMPLATE = """\
```
{format_instructions}
```
"""

class TriggerType(Enum):
    voice_inbound = 'voice_inbound'
    voice_outbound = 'voice_outbound'
    livechat_inbound = 'livechat_inbound'
    message_inbound = 'message_inbound'
    api = 'api'
    module = 'module'


class Status(Enum):
    draft = 'draft'
    published = 'published'
    archived = 'archived'
    deleted = 'deleted'

class ValidationStatus(Enum):
    valid = 'valid'
    error = 'error'
    warning = 'warning'
    validating = 'validating'
    not_validated = 'not_validated'


class Format(BaseModel):
    type: Optional[str] = Field(None, description='The type of the variable')
    field_schema: Optional[str] = Field(
        'http://json-schema.org/draft-04/schema#',
        alias='$schema',
        description='The schema of the variable',
    )

class Model(BaseModel):
    displayName: Optional[str] = Field(None, description='The name of this variable')
    exposed: Optional[bool] = Field(None, description='Exposed the values')
    format: Optional[Format] = Field(None, description='The format of the variable')


class StudioWorkFlowMetaSchema(BaseModel):
    id: constr(regex=r'^[0-9a-f]{32}$') = Field(..., description='A unique identifier')
    account_id: Optional[constr(regex=r'^[0-9a-fA-F]{24}$')] = Field(
        None,
        description='Account identifier, the identifier of the account to which this record belongs.',
    )
    user_id: Optional[constr(regex=r'^[0-9a-fA-F]{24}$')] = Field(
        None,
        description='User identifier, the identifier of the user who created this record.',
    )
    name: str = Field(
        ...,
        description='Name, usually representing a human-readable title or name for this record.',
    )
    description: str = Field(
        ...,
        description='Detailed description or additional information about this record.',
    )
    trigger_type: TriggerType = Field(
        ...,
        description='Trigger type, indicating the manner or condition under which this record is triggered.',
    )
    status: Status = Field(
        ...,
        description="Status, indicating the current status of this record, such as 'published'.",
    )
    version: int = Field(
        ..., description='Version number, the version identifier of this record.'
    )
    previous_version: Optional[str] = Field(
        None,
        description='Identifier of the previous version, pointing to the prior version of this record.',
    )
    created_at: datetime = Field(
        ..., description='Creation time, the date and time when the record was created.'
    )
    updated_at: datetime = Field(
        ...,
        description='Update time, the date and time when the record was last updated.',
    )
    valid: bool = Field(
        ..., description='Validity flag, indicating whether this record is valid.'
    )
    validation_status: ValidationStatus = Field(
        ...,
        description="Validation status, showing the validation status of this record, such as 'valid'.",
    )
    initial_step_id: constr(regex=r'^[0-9a-f]{32}$') = Field(
        ...,
        description='Initial step identifier, pointing to the initial step in the process.',
    )
    group_id: Optional[str] = Field(
        None,
        description='Group identifier, the identifier of the group or category to which this record belongs.',
    )
    pre_conditions: Optional[Dict[str, Any]] = Field(
        None,
        description='Pre-conditions, defining conditions that must be met for this record to be valid.',
    )
    steps: str = Field('{% steps %}', const=True)
    model: Optional[Model] = Field(
        None, description='The context variables for this flow'
    )


def create_generate_wrap_chain(llm: LanguageModelLike):
    output_parser = JsonOutputParser(pydantic_object=StudioWorkFlowMetaSchema)

    PROMPT = PromptTemplate(
        template = WRAP_TEMPLATE,
        input_variables=[],
        partial_variables={"format_instructions": output_parser.get_format_instructions()})

    return (
        PROMPT
        |
        llm
        | output_parser
    )


openai_gpt = ChatOpenAI(model=OPENAI_MODELS, temperature=0)
llm = openai_gpt.configurable_alternatives(
    ConfigurableField(id="llm"),
    default_key="openai_gpt",
).with_fallbacks(
    [openai_gpt]
)

generate_wrap_chain = create_generate_wrap_chain(llm)
