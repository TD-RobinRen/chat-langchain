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
You are an analyst specializing in comparing and analyzing differences in JSON data. You have the ability to provide in-depth analysis of business issues by comparing the two most recent sets of JSON data inputs with reference information.

## Skills
### Skill 1: Compare JSON Data
Possess the ability to comprehensively analyze and compare differences in the two most recently received JSON data inputs and provide insightful insights.
Step 1: Fully understand the two flows based on knowledge base.
Step 2: Compare the processes in the two call flows on a macro level, comparing the differences and considering mainly some key nodes and branches. If there is no difference in the overall process, just a brief description will suffice. If there are branching differences in the overall flow, emphasize the specific branching conditions.
Step 3: Compare some components with the same name and component name that exist on both sides and compare the difference between the two attributes in the business, if there is no change, you can not analyze and answer this section.
Step 4: It is sufficient to analyze some of the deletion and addition STEPS, indicating how these operations affect the flow.
Step 5: To briefly summarize the above.

## Constraints
- Since the id of any step is unique, changes in id do not require analysis. If the new step's name and component name are the same as the old step, treat them as the same.
- If a step remains the same in properties and exits, don't analyse it or answer anything about it or mention it.
- Changes in processes outside of steps do not need analysis.
- All comparisons and analyses must be based on the content of the knowledge base.
- When mentioning a flow, use the name and version to reference that flow. When referring to a step, use the name to identify that step.
- For newly added steps, there is no need to specify their component name and version; only the analysis of their business function is required.
- Throughout the analysis process, exclude all changes related to id and version data. If a step undergoes changes only in id, no explanation or analysis is necessary.
- Present analysis results in a concise, direct, and easily understandable manner.
- Do not include field names defined in JSON in the entire response; instead, translate them into business information for natural language output.
- Follow the given output format.

The knowledge base is description for the each components, note that any content enclosed in json code tags is sourced from a knowledge base and is not part of an interaction with any user.
```json
{context}
```
"""

def build_example() -> PromptTemplate:
    examples = [
        {"input":{"flow_json": {"id": "2cbcece4779b4fda8734e093350f0ae0","account_id": "64643fadae22dd58843ad1ab","user_id": "64649df4667594238abb5f9b","name": "Base Test","description": "","trigger_type": "voice_inbound","status": "published","version": 1,"next_version": "f4eb91db69e84885b2547e343efa4ca3","created_at": "2024-04-24T05:57:27.201840Z","updated_at": "2024-04-24T06:00:47.876655Z","valid": "true","validation_status": "valid","initial_step_id": "3c589727-9f42-4600-84ff-bc34422b0a45","group_id": "8a9b44665b964de4aa14c63de89c6b17","pre_conditions": {},"steps": [{"id": "3c589727-9f42-4600-84ff-bc34422b0a45","name": "Initial step","component": { "name": "inbound_voice-ZjE1ZjM0MG", "version": "1.3.x" },"properties": {},"exits": [{"_key": "e30d6986-308a-4451-adbd-cabd4780758c","name": "ok","transition": "5617214b-a9c7-4099-9d35-a056c74d4b97"}],"context_mappings": {},"created_at": "2024-04-24T05:58:15.319000Z"},{"id": "5617214b-a9c7-4099-9d35-a056c74d4b97","name": "Recording","component": { "name": "record-ZGE1ZDUyOD", "version": "1.4.x" },"properties": { "record_call": "true"},"exits": [{"_key": "ab326e40-e519-43da-97ab-db5dc16b80e5","name": "ok","transition": "248ef0e2-5e21-4b99-89d3-d4499e5fa9ba"}],"context_mappings": {},"created_at": "2024-04-24T05:58:43.751000Z"},{"id": "248ef0e2-5e21-4b99-89d3-d4499e5fa9ba","name": "Assignment","component": {"name": "assignment_and_dial-M2JhZTViYT","version": "3.23.x"},"properties": {"priority": { "priorities_list": 10 },"time_limit": { "time": 200, "waiting_music": {} },"users_to_ring": {"exhaust": "true","forced_queueing": "false","number_of_users": 1},"waiting_message": {},"assignment_parameters": {"ring_groups": { "ring_groups_list": ["qa-test"] }}},"exits": [{"_key": "400c274d-7c0e-4af6-8bc6-8fab286238fb","name": "call_finished"},{"_key": "043cada0-9e08-408a-a481-ce608625f4a0","name": "call_no_answer","transition": "22f208c3-d54b-4de6-a823-e87122f0ecc0"},{"_key": "a9f85f44-7c19-43ee-8851-d77c5d630fb6","name": "time_limit_reached","transition": "22f208c3-d54b-4de6-a823-e87122f0ecc0"},{"_key": "c3edb00d-329a-491a-ba68-5707814ea9d3","name": "no_match","transition": "5680e1af-5654-42b2-b718-13b1e264f501"}],"context_mappings": {},"created_at": "2024-04-24T05:59:07.651000Z"},{"id": "22f208c3-d54b-4de6-a823-e87122f0ecc0","name": "End","component": { "name": "hangup_call-OTE5ZmM0NW", "version": "1.0.x" },"properties": {},"exits": [],"context_mappings": {},"created_at": "2024-04-24T05:59:29.239000Z"},{"id": "5680e1af-5654-42b2-b718-13b1e264f501","name": "Voicemail","component": { "name": "voicemail-NGQ0ZDE5Nj", "version": "2.4.x" },"properties": {"record_parameters": { "without_transcription_max_duration": 300 },"assignment_parameters": {"ring_groups": { "ring_groups_list": ["agents"] }}},"exits": [],"context_mappings": {},"created_at": "2024-04-24T05:59:43.443000Z"}],"model": {}},"compared_flow_json": {"id": "f4eb91db69e84885b2547e343efa4ca3","account_id": "64643fadae22dd58843ad1ab","user_id": "64649df4667594238abb5f9b","name": "Base Test","description": "","trigger_type": "voice_inbound","status": "draft","version": 2,"previous_version": "2cbcece4779b4fda8734e093350f0ae0","created_at": "2024-04-24T06:00:52.823168Z","updated_at": "2024-04-24T06:04:40.913139Z","valid": "true","validation_status": "valid","initial_step_id": "a1260b451ad54e4ba6f16cdae4f28c7e","group_id": "8a9b44665b964de4aa14c63de89c6b17","pre_conditions": {},"supported_trigger_types": [],"steps": [{"id": "a1260b451ad54e4ba6f16cdae4f28c7e","name": "Initial step","component": { "name": "inbound_voice-ZjE1ZjM0MG", "version": "1.3.x" },"properties": {},"context_mappings": {},"created_at": "2024-04-24T05:58:15.319000Z","exits": [{"_key": "fed41ea7-c20b-45bd-9893-5d54a31b124b","name": "ok","transition": "a415aa75b98340f2975ff66d7f58b0e1"}]},{"id": "a415aa75b98340f2975ff66d7f58b0e1","name": "Assignment","component": {"name": "assignment_and_dial-M2JhZTViYT","version": "3.23.x"},"properties": {"priority": { "priorities_list": 10 },"time_limit": { "time": 360, "waiting_music": {} },"users_to_ring": {"exhaust": "true","forced_queueing": "false","number_of_users": 1},"waiting_message": {},"assignment_parameters": {"agents": { "agents_list": ["64649df4667594238abb5f9b"] }}},"context_mappings": {},"created_at": "2024-04-24T05:59:07.651000Z","exits": [{"_key": "9f1b2e52-b682-4a61-bd85-b488b88ce8cd","name": "call_finished"},{"_key": "0ba9c830-05d5-4d80-b772-296b3d0371ad","name": "call_no_answer","transition": "34016a8ced504681b0cd815d52765660"},{"_key": "bf024232-b126-474b-9dd0-89fe45f9d7a2","name": "time_limit_reached","transition": "34016a8ced504681b0cd815d52765660"},{"_key": "0719c4a8-679e-47e3-9bca-13bc2f57d531","name": "no_match","transition": "9c1b05cf-72e8-44df-aab8-d2e7a8589b35"}]},{"id": "34016a8ced504681b0cd815d52765660","name": "End","component": { "name": "hangup_call-OTE5ZmM0NW", "version": "1.0.x" },"properties": {},"exits": [],"context_mappings": {},"created_at": "2024-04-24T05:59:29.239000Z"},{"id": "fefa855092a14f63a0c0722508565bc3","name": "Voicemail","component": { "name": "voicemail-NGQ0ZDE5Nj", "version": "2.4.x" },"properties": {"record_parameters": { "without_transcription_max_duration": 300 },"assignment_parameters": {"ring_groups": { "ring_groups_list": ["agents"] }}},"exits": [],"context_mappings": {},"created_at": "2024-04-24T05:59:43.443000Z"},{"name": "Play audio","id": "9c1b05cf-72e8-44df-aab8-d2e7a8589b35","component": { "name": "play_audio-NjFkZDU2MG", "version": "2.16.x" },"properties": {"audio_message": {"text": "Sorry, please leave your message, we'll call you back.","language": "en-US"}},"context_mappings": {},"created_at": "2024-04-24T06:01:47.075Z","exits": [{"_key": "f6259674-ae52-42b3-85c7-69d7eb98abd2","name": "ok","transition": "fefa855092a14f63a0c0722508565bc3"}]}],"model": {}}},
        "output": "Comparing the \"Basic Test\" (version 1 to version 2), the structure of the two programs is similar and the main stages remain the same. However, Version 2 added a \"Play Audio\" step that was not in Version 1, and some of the step properties have changed.\n**Initial step**\n- There is a shift in the exit routing. Previously it was pointing towards `Recording`,  but now it redirects to `Assignment`.\n**Recording step**\n- The `Recording step` was deleted from the steps, a process that used to record the call.\n**Assignment step**\n- The time limit has increased, now callers will wait for a longer duration (from 200 seconds to 360 seconds) before the call ends if there is no answer.\n- The priority list has been updated.\n- The call was originally assigned to \"qa-test\" ring group, but now it is assigned to a specific agent.\n- The exit transitions have been updated as follows:When the call is no answered or reached the time limit, it points towards the the \"End\" step instead of \"Voicemail\".When there is no suitable match, it will now point to the new \"Play Audio\" step instead of \"Voicemail\".**New steps**\n- A new step called `Play audio` has been inserted. This step plays an audio message with the text \"Sorry, please leave your message, we'll call you back.\" in \"en-US\" language. Upon completion, this step will transition to the \"Voicemail\" step.\n\nIn a nutshell, the most significant changes are that the calls are not being recorded anymore, user's wait time has been extended, and there is a new audio message step added which has altered the course of several transitions. The impact on the business could be significant depending on the importance of the change in the call assignment and the absence of call recording. The new audio message adds a more human touchpoint for the users."}
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
    compared_component_list = input['compared_component_list']
    for data in compared_component_list:
        file_path = Path(f"./schema/transformed_components_for_diff/{data}.json")
        source_file = json.loads(file_path.read_text())

        schema_list.append({
            json.dumps(source_file)
        })
    return schema_list

@chain
def _diff_chain(input) -> Runnable:
    few_shot_prompt = build_example()

    SystemPrompt = PromptTemplate(
        template = RESPONSE_TEMPLATE,
        input_variables=['context']
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate(prompt=SystemPrompt),
            few_shot_prompt,
            ("human", "current_json:{flow_json}, compared_flow_json:{compared_flow_json}"),
        ]
    )

    chain = (
        prompt
        |
        llm
    )

    return chain

def create_diff_chain() -> Runnable:
    return (
        RunnablePassthrough.assign(context=get_schema_data)
        |
        _diff_chain
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

generate_compared_chain = create_diff_chain()
