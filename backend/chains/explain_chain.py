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
        {"input":{"flow_json": {"id": "2cbcece4779b4fda8734e093350f0ae0","account_id": "64643fadae22dd58843ad1ab","user_id": "64649df4667594238abb5f9b","name": "Base Test","description": "","trigger_type": "voice_inbound","status": "published","version": 1,"next_version": "f4eb91db69e84885b2547e343efa4ca3","created_at": "2024-04-24T05:57:27.201840Z","updated_at": "2024-04-24T06:00:47.876655Z","valid": "true","validation_status": "valid","initial_step_id": "3c589727-9f42-4600-84ff-bc34422b0a45","group_id": "8a9b44665b964de4aa14c63de89c6b17","pre_conditions": {},"steps": [{"id": "3c589727-9f42-4600-84ff-bc34422b0a45","name": "Initial step","component": { "name": "inbound_voice-ZjE1ZjM0MG", "version": "1.3.x" },"properties": {},"exits": [{"_key": "e30d6986-308a-4451-adbd-cabd4780758c","name": "ok","transition": "5617214b-a9c7-4099-9d35-a056c74d4b97"}],"context_mappings": {},"created_at": "2024-04-24T05:58:15.319000Z"},{"id": "5617214b-a9c7-4099-9d35-a056c74d4b97","name": "Recording","component": { "name": "record-ZGE1ZDUyOD", "version": "1.4.x" },"properties": { "record_call": "true"},"exits": [{"_key": "ab326e40-e519-43da-97ab-db5dc16b80e5","name": "ok","transition": "248ef0e2-5e21-4b99-89d3-d4499e5fa9ba"}],"context_mappings": {},"created_at": "2024-04-24T05:58:43.751000Z"},{"id": "248ef0e2-5e21-4b99-89d3-d4499e5fa9ba","name": "Assignment","component": {"name": "assignment_and_dial-M2JhZTViYT","version": "3.23.x"},"properties": {"priority": { "priorities_list": 10 },"time_limit": { "time": 200, "waiting_music": {} },"users_to_ring": {"exhaust": "true","forced_queueing": "false","number_of_users": 1},"waiting_message": {},"assignment_parameters": {"ring_groups": { "ring_groups_list": ["qa-test"] }}},"exits": [{"_key": "400c274d-7c0e-4af6-8bc6-8fab286238fb","name": "call_finished"},{"_key": "043cada0-9e08-408a-a481-ce608625f4a0","name": "call_no_answer","transition": "22f208c3-d54b-4de6-a823-e87122f0ecc0"},{"_key": "a9f85f44-7c19-43ee-8851-d77c5d630fb6","name": "time_limit_reached","transition": "22f208c3-d54b-4de6-a823-e87122f0ecc0"},{"_key": "c3edb00d-329a-491a-ba68-5707814ea9d3","name": "no_match","transition": "5680e1af-5654-42b2-b718-13b1e264f501"}],"context_mappings": {},"created_at": "2024-04-24T05:59:07.651000Z"},{"id": "22f208c3-d54b-4de6-a823-e87122f0ecc0","name": "End","component": { "name": "hangup_call-OTE5ZmM0NW", "version": "1.0.x" },"properties": {},"exits": [],"context_mappings": {},"created_at": "2024-04-24T05:59:29.239000Z"},{"id": "5680e1af-5654-42b2-b718-13b1e264f501","name": "Voicemail","component": { "name": "voicemail-NGQ0ZDE5Nj", "version": "2.4.x" },"properties": {"record_parameters": { "without_transcription_max_duration": 300 },"assignment_parameters": {"ring_groups": { "ring_groups_list": ["agents"] }}},"exits": [],"context_mappings": {},"created_at": "2024-04-24T05:59:43.443000Z"}],"model": {}},"compared_flow_json": {"id": "f4eb91db69e84885b2547e343efa4ca3","account_id": "64643fadae22dd58843ad1ab","user_id": "64649df4667594238abb5f9b","name": "Base Test","description": "","trigger_type": "voice_inbound","status": "draft","version": 2,"previous_version": "2cbcece4779b4fda8734e093350f0ae0","created_at": "2024-04-24T06:00:52.823168Z","updated_at": "2024-04-24T06:04:40.913139Z","valid": "true","validation_status": "valid","initial_step_id": "a1260b451ad54e4ba6f16cdae4f28c7e","group_id": "8a9b44665b964de4aa14c63de89c6b17","pre_conditions": {},"supported_trigger_types": [],"steps": [{"id": "a1260b451ad54e4ba6f16cdae4f28c7e","name": "Initial step","component": { "name": "inbound_voice-ZjE1ZjM0MG", "version": "1.3.x" },"properties": {},"context_mappings": {},"created_at": "2024-04-24T05:58:15.319000Z","exits": [{"_key": "fed41ea7-c20b-45bd-9893-5d54a31b124b","name": "ok","transition": "a415aa75b98340f2975ff66d7f58b0e1"}]},{"id": "a415aa75b98340f2975ff66d7f58b0e1","name": "Assignment","component": {"name": "assignment_and_dial-M2JhZTViYT","version": "3.23.x"},"properties": {"priority": { "priorities_list": 10 },"time_limit": { "time": 360, "waiting_music": {} },"users_to_ring": {"exhaust": "true","forced_queueing": "false","number_of_users": 1},"waiting_message": {},"assignment_parameters": {"agents": { "agents_list": ["64649df4667594238abb5f9b"] }}},"context_mappings": {},"created_at": "2024-04-24T05:59:07.651000Z","exits": [{"_key": "9f1b2e52-b682-4a61-bd85-b488b88ce8cd","name": "call_finished"},{"_key": "0ba9c830-05d5-4d80-b772-296b3d0371ad","name": "call_no_answer","transition": "34016a8ced504681b0cd815d52765660"},{"_key": "bf024232-b126-474b-9dd0-89fe45f9d7a2","name": "time_limit_reached","transition": "34016a8ced504681b0cd815d52765660"},{"_key": "0719c4a8-679e-47e3-9bca-13bc2f57d531","name": "no_match","transition": "9c1b05cf-72e8-44df-aab8-d2e7a8589b35"}]},{"id": "34016a8ced504681b0cd815d52765660","name": "End","component": { "name": "hangup_call-OTE5ZmM0NW", "version": "1.0.x" },"properties": {},"exits": [],"context_mappings": {},"created_at": "2024-04-24T05:59:29.239000Z"},{"id": "fefa855092a14f63a0c0722508565bc3","name": "Voicemail","component": { "name": "voicemail-NGQ0ZDE5Nj", "version": "2.4.x" },"properties": {"record_parameters": { "without_transcription_max_duration": 300 },"assignment_parameters": {"ring_groups": { "ring_groups_list": ["agents"] }}},"exits": [],"context_mappings": {},"created_at": "2024-04-24T05:59:43.443000Z"},{"name": "Play audio","id": "9c1b05cf-72e8-44df-aab8-d2e7a8589b35","component": { "name": "play_audio-NjFkZDU2MG", "version": "2.16.x" },"properties": {"audio_message": {"text": "Sorry, please leave your message, we'll call you back.","language": "en-US"}},"context_mappings": {},"created_at": "2024-04-24T06:01:47.075Z","exits": [{"_key": "f6259674-ae52-42b3-85c7-69d7eb98abd2","name": "ok","transition": "fefa855092a14f63a0c0722508565bc3"}]}],"model": {}}},
        "output": "The flow 'Base Test' is primarily configured to handle inbound voice triggers.As a voice-based workflow, it is activated when there is an inbound voice call.\n**Initial Step**\nThe workflow initiates its process with the step named 'Initial Step'. Here the inbound call is received and managed. Upon successfully receiving a call, the workflow proceeds to the step named 'Assignment'.\n**Assignment Step**\nThe 'Assignment' step is crucial in determining the handling of the incoming call. Various factors are taken into consideration such as priority, time limit (initially set to 360), waiting message and the agents to be rung. The system is configured to reach out to one user at a time, and it exhaustively tries to reach all the users specified. Also, if the call is not picked up or if the maximum time limit has been reached, the workflow redirects to the 'End' step.\n**End step**\nThe 'End' step is simply a termination point where the call would be hang up. Alternatively, if the assignment step cannot find a match, the workflow proceeds to the 'Play Audio' step. An apology message is then played for the user indicating that their call couldn't be attended and asks them to leave a message.\n**Voicemail Step**\nThe workflow then transitions to the 'Voicemail' step where the caller's message is recorded. The maximum length of the recorded message without transcription is 300 units of measurement.\nOverall, the workflow is smartly designed to handle inbound voice signals, assigning calls to different users if a human presence is detected on the line, and efficiently transitions to recording a voicemail if no response is found. The effectiveness of the system lies in its ability to navigate various steps, clearly defined transitions, and its adaptability to different situations encountered during a voice call."}
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
