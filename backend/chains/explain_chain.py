import os
import json
from pathlib import Path
from operator import itemgetter
from typing import Dict, List, Optional, Sequence, Any
from langchain_core.language_models import LanguageModelLike
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
    SystemMessagePromptTemplate,
    FewShotChatMessagePromptTemplate
)
from langchain_core.output_parsers import StrOutputParser
from langchain.schema.retriever import BaseRetriever
from langchain_core.runnables import (
    ConfigurableField,
    Runnable,
    RunnablePassthrough,
    chain
)
from langchain_openai import ChatOpenAI
OPENAI_MODELS = os.environ["OPENAI_MODELS"]

RESPONSE_TEMPLATE = """\
# Character
You are a detail-oriented interpreter of JSON data. Your strengths lie in interpreting JSON workflow data using straightforward natural language.

## Skills
### Skill 1: Decode JSON data based on the JSON schema provided in Knowledge
To effectively illustrate JSON data, follow these steps:
Give a briefly summarize the goals and context of JSON data, such as its specific uses. This includes, but is not limited to, the overall direction of FLOW, important branch execution conditions, etc.
Then detailed step-by-step analysis:
- Step 1: Articulate the goals of the central component in the workflow.
- Step 2: Demonstrate how the part coordinates with the attribute configuration in the current step to perform its role in the workflow.
- Step 3: Scrutinize the step exits, detailing the transitions between steps, e.g., which step name to transition to.
- Step 4: Continue this step for each step mentioned in the given JSON data.
Summary: Provide a comprehensive assessment and overview of the entire dataset and associated workflows. Remember that your description should be concise but comprehensive and should emphasize the role and significance of each workflow step.

## Constraints
- Always follow the instructions given in the relevant JSON schema.
- Aim for a precise and detailed description, focusing on the role and function of each step in the workflow.
- Do not include field names defined in JSON in the entire response; instead, translate them into business information for natural language output.
- Interpret flows in the order in which they are executed, not in the order in which they are placed in the steps.
- If the user ask for explain some steps in detail, not show the component name or version, just explain the properties and exits of the step.

The knowledge base is description for the each components, note that any content enclosed in json code tags is sourced from a knowledge base and is not part of an interaction with any user.
```json
{context}
```
"""

def build_example() -> PromptTemplate:
    examples = [
        {
            "input": {'flow_json': {'id': 'b08303d39528446f810a5452b8b632bf', 'account_id': '64643fadae22dd58843ad1ab', 'user_id': '64649e2d5e3c241a03c651a7', 'name': 'Inbound call Robin', 'description': '', 'trigger_type': 'voice_inbound', 'status': 'draft', 'version': 1, 'created_at': '2024-04-23T09:38:11.410373Z', 'updated_at': '2024-05-02T13:40:32.389059Z', 'valid': False, 'validation_status': 'error', 'initial_step_id': '3fca0207-e300-4a07-bc7a-d1975c3ddf63', 'group_id': '9750b6abe8d5432e915e376144814734', 'pre_conditions': {}, 'steps': [{'id': '3fca0207-e300-4a07-bc7a-d1975c3ddf63', 'name': 'inbound_voice-ZjE1ZjM0MG', 'component': {'name': 'inbound_voice-ZjE1ZjM0MG', 'version': '1.3.x'}, 'properties': {}, 'exits': [{'name': 'ok', 'transition': '6633974ac53f5e8feec3de2f'}], 'context_mappings': {}, 'created_at': '2023-10-03T12:00:00.000000Z'}, {'id': '6633974ac53f5e8feec3de2f', 'name': 'assignment_and_dial-M2JhZTViYT', 'component': {'name': 'assignment_and_dial-M2JhZTViYT', 'version': '3.23.x'}, 'properties': {'priority': {'priorities_list': 5}, 'time_limit': {'time': 120}, 'assignment_parameters': {'ring_groups': {'ring_groups_list': ['test']}}}, 'exits': [{'name': 'call_finished', 'transition': '6633974ac53f5e8feec3de30'}, {'name': 'call_no_answer', 'transition': '6633974ac53f5e8feec3de31'}], 'context_mappings': {}, 'created_at': '2024-04-09T00:00:00.000000Z'}, {'id': '6633974ac53f5e8feec3de30', 'name': 'Terminate Call', 'component': {'name': 'hangup_call-OTE5ZmM0NW', 'version': '1.0.x'}, 'properties': {}, 'exits': [], 'context_mappings': {}, 'created_at': '2024-04-09T00:00:00.000000Z'}, {'id': '6633974ac53f5e8feec3de31', 'name': 'Voicemail Routing', 'component': {'name': 'voicemail-NGQ0ZDE5Nj', 'version': '2.4.x'}, 'properties': {'record_parameters': {'with_transcription_max_duration': 120}, 'assignment_parameters': {'ring_groups': {'ring_groups_list': ['test']}}}, 'exits': [], 'context_mappings': {}, 'created_at': '2024-04-09T00:00:00.000000Z'}]}},
            "output": "The JSON data outlines a workflow named \"Inbound call Robin\" designed for handling inbound voice calls. This workflow is currently in a draft status and has been flagged with a validation error, indicating issues that need to be resolved before it can be published and become operational.\n\n**Workflow Steps Overview:**\n\n**Initial Step (Inbound Voice Reception):**\n   - **Goal:** To receive an inbound voice call.\n   - **Execution:** This step does not have specific properties set, indicating it's primarily for call reception.\n   - **Transition:** Upon successful execution, the workflow transitions to the \"Assignment and Dial\" step.\n\n**Assignment and Dial:**\n   - **Goal:** To assign the call to a group and attempt to connect the call.\n   - **Execution:** This step involves setting a priority level (5 in this case) and a time limit of 120 seconds for the call assignment process. It specifies using a ring group named 'test' for the assignment.\n   - **Transitions:**\n     - If the call is successfully connected and finished, it transitions to the \"Terminate Call\" step.\n     - If the call is not answered, it transitions to the \"Voicemail Routing\" step.\n\n**Terminate Call:**\n   - **Goal:** To end the call.\n   - **Execution:** This step does not have specific properties, indicating its sole purpose is to hang up the call.\n   - **Transition:** There are no further transitions from this step, marking the end of the workflow if this path is taken.\n\n**Voicemail Routing:**\n   - **Goal:** To route the call to voicemail and enable message recording with transcription.\n   - **Execution:** This step is configured to record a voicemail with a maximum duration of 120 seconds and transcribe the message. It uses the same 'test' ring group for assignment parameters as the \"Assignment and Dial\" step.\n   - **Transition:** There are no further transitions from this step, indicating it's the end of the workflow for calls that reach voicemail.\n\n**Summary:**\nThe \"Inbound call Robin\" workflow is structured to manage inbound calls by initially attempting to connect the caller with available members of a specified ring group. If no one answers, the call is directed to voicemail, where a message can be left and transcribed. The workflow includes mechanisms for both successful call connections and unattended calls, ensuring that every call is processed efficiently. However, the presence of a validation error suggests that there are issues within the workflow configuration that need to be addressed before it can be fully implemented."
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

def get_schema_data(input) -> List:
    schema_list = []
    component_list = input['component_list']
    for data in component_list:
        file_path = Path(f"./schema/transformed_components_for_diff/{data}.json")
        source_file = json.loads(file_path.read_text())

        schema_list.append({
            json.dumps(source_file)
        })
    return schema_list

@chain
def _explain_chain(input) -> Runnable:
    few_shot_prompt = build_example()

    SystemPrompt = PromptTemplate(
        template = RESPONSE_TEMPLATE,
        input_variables=['context']
    )

    default_question="Explain the JSON data."
    question = input.get('question')
    if question is None or question == '':
        question = default_question

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate(prompt=SystemPrompt),
            few_shot_prompt,
           ("human", "flow_json: {flow_json}, question: {question}".format(flow_json="{flow_json}", question=question))
        ]
    )

    chain = (
        prompt
        |
        llm
        |
        StrOutputParser()
    )

    return chain

def create_explain_chain() -> Runnable:
    return (
        RunnablePassthrough.assign(context=get_schema_data)
        |
        _explain_chain
    )

openai_gpt = ChatOpenAI(model=OPENAI_MODELS, temperature=0)
llm = openai_gpt.configurable_alternatives(
    # This gives this field an id
    # When configuring the end runnable, we can then use this id to configure this field
    ConfigurableField(id="llm"),
    default_key="openai_gpt",
).with_fallbacks(
    [openai_gpt]
)

explain_chain = create_explain_chain()
