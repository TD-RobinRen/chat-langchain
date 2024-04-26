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
You're a meticulous flowchart analyst. Your skill set is specially aligned towards recognizing and optimizing the inherent contrasts between flowcharts.

## Skills
### Skill 1: Appraising flowchart deviations
- Evaluate the diff_json of the flowchart to track all versions and amendments. Scrutinize how these changes impact on the entire sequence. 
- Upon encountering a shift in attributes, highlight the modification comprehensively and investigate its consequential effects on the process.
- In case ids in the steps are modified, treat them as negligible.

### Skill 2: Deciphering Transition Changes
- In situations where the transition undergoes alterations, meticulously identify the end-points in each stage. Provide an in-depth account of each transition shift, including its intended direction.

### Skill 3: Persistent Scrutiny
- Conduct the afore-mentioned evaluations for all changes persistently, maintaining an unbroken focus on the evolution.

## Constraints
- All comparisons and analyses must be based on the knowledge base
- To refer to the flow, use its name and version.
- Restrict discussion to topics related to flowchart analysis.
- Extract content from the knowledge base. For unidentified flowcharts, employ search and browsing.
- When citing sources, adopt the ^^^ Markdown format.
- For identifying specific components, prefer step names over component names.

The knowledge base is description for the each components, note that any content enclosed in json code tags is sourced from a knowledge base and is not part of an interaction with any user.
```json
{context}
```
"""

def build_example() -> PromptTemplate:
    examples = [
        {
            "input": '{"next_version__deleted":"f4eb91db69e84885b2547e343efa4ca3","previous_version__added":"2cbcece4779b4fda8734e093350f0ae0","supported_trigger_types__added":[],"id":{"__old":"2cbcece4779b4fda8734e093350f0ae0","__new":"f4eb91db69e84885b2547e343efa4ca3"},"account_id":"64643fadae22dd58843ad1ab","user_id":"64649df4667594238abb5f9b","name":"Base Test","description":"","trigger_type":"voice_inbound","status":{"__old":"published","__new":"draft"},"version":{"__old":1,"__new":2},"created_at":{"__old":"2024-04-24T05:57:27.201840Z","__new":"2024-04-24T06:00:52.823168Z"},"updated_at":{"__old":"2024-04-24T06:00:47.876655Z","__new":"2024-04-24T06:04:40.913139Z"},"valid":true,"validation_status":"valid","initial_step_id":{"__old":"3c589727-9f42-4600-84ff-bc34422b0a45","__new":"a1260b451ad54e4ba6f16cdae4f28c7e"},"group_id":"8a9b44665b964de4aa14c63de89c6b17","pre_conditions":{},"steps":[["~",{"id":{"__old":"3c589727-9f42-4600-84ff-bc34422b0a45","__new":"a1260b451ad54e4ba6f16cdae4f28c7e"},"name":"Initial step","component":{"name":"inbound_voice-ZjE1ZjM0MG","version":"1.3.x"},"properties":{},"exits":[["~",{"_key":{"__old":"e30d6986-308a-4451-adbd-cabd4780758c","__new":"fed41ea7-c20b-45bd-9893-5d54a31b124b"},"name":"ok","transition":{"__old":"5617214b-a9c7-4099-9d35-a056c74d4b97","__new":"a415aa75b98340f2975ff66d7f58b0e1"}}]],"context_mappings":{},"created_at":"2024-04-24T05:58:15.319000Z"}],["-",{"id":"5617214b-a9c7-4099-9d35-a056c74d4b97","name":"Recording","component":{"name":"record-ZGE1ZDUyOD","version":"1.4.x"},"properties":{"record_call":true},"exits":[{"_key":"ab326e40-e519-43da-97ab-db5dc16b80e5","name":"ok","transition":"248ef0e2-5e21-4b99-89d3-d4499e5fa9ba"}],"context_mappings":{},"created_at":"2024-04-24T05:58:43.751000Z"}],["~",{"id":{"__old":"248ef0e2-5e21-4b99-89d3-d4499e5fa9ba","__new":"a415aa75b98340f2975ff66d7f58b0e1"},"name":"Assignment","component":{"name":"assignment_and_dial-M2JhZTViYT","version":"3.23.x"},"properties":{"priority":{"priorities_list":10},"time_limit":{"time":{"__old":200,"__new":360},"waiting_music":{}},"users_to_ring":{"exhaust":true,"forced_queueing":false,"number_of_users":1},"waiting_message":{},"assignment_parameters":{"ring_groups__deleted":{"ring_groups_list":["qa-test"]},"agents__added":{"agents_list":["64649df4667594238abb5f9b"]}}},"exits":[["~",{"_key":{"__old":"400c274d-7c0e-4af6-8bc6-8fab286238fb","__new":"9f1b2e52-b682-4a61-bd85-b488b88ce8cd"},"name":"call_finished"}],["~",{"_key":{"__old":"043cada0-9e08-408a-a481-ce608625f4a0","__new":"0ba9c830-05d5-4d80-b772-296b3d0371ad"},"name":"call_no_answer","transition":{"__old":"22f208c3-d54b-4de6-a823-e87122f0ecc0","__new":"34016a8ced504681b0cd815d52765660"}}],["~",{"_key":{"__old":"a9f85f44-7c19-43ee-8851-d77c5d630fb6","__new":"bf024232-b126-474b-9dd0-89fe45f9d7a2"},"name":"time_limit_reached","transition":{"__old":"22f208c3-d54b-4de6-a823-e87122f0ecc0","__new":"34016a8ced504681b0cd815d52765660"}}],["~",{"_key":{"__old":"c3edb00d-329a-491a-ba68-5707814ea9d3","__new":"0719c4a8-679e-47e3-9bca-13bc2f57d531"},"name":"no_match","transition":{"__old":"5680e1af-5654-42b2-b718-13b1e264f501","__new":"9c1b05cf-72e8-44df-aab8-d2e7a8589b35"}}]],"context_mappings":{},"created_at":"2024-04-24T05:59:07.651000Z"}],["~",{"id":{"__old":"22f208c3-d54b-4de6-a823-e87122f0ecc0","__new":"34016a8ced504681b0cd815d52765660"},"name":"End","component":{"name":"hangup_call-OTE5ZmM0NW","version":"1.0.x"},"properties":{},"exits":[],"context_mappings":{},"created_at":"2024-04-24T05:59:29.239000Z"}],["~",{"id":{"__old":"5680e1af-5654-42b2-b718-13b1e264f501","__new":"fefa855092a14f63a0c0722508565bc3"},"name":"Voicemail","component":{"name":"voicemail-NGQ0ZDE5Nj","version":"2.4.x"},"properties":{"record_parameters":{"without_transcription_max_duration":300},"assignment_parameters":{"ring_groups":{"ring_groups_list":["agents"]}}},"exits":[],"context_mappings":{},"created_at":"2024-04-24T05:59:43.443000Z"}],["+",{"name":"Play audio","id":"9c1b05cf-72e8-44df-aab8-d2e7a8589b35","component":{"name":"play_audio-NjFkZDU2MG","version":"2.16.x"},"properties":{"audio_message":{"text":"Sorry, please leave your message, we\'ll call you back.","language":"en-US"}},"context_mappings":{},"created_at":"2024-04-24T06:01:47.075Z","exits":[{"_key":"f6259674-ae52-42b3-85c7-69d7eb98abd2","name":"ok","transition":"fefa855092a14f63a0c0722508565bc3"}]}]]}',
            "output": 'The changes from version 1 to version 2 of the \'Base Test\' flowchart on April 24, 2024:\n**Step-Level Changes:**\n- Recording Step: This step has been eliminated in version 2 of the flowchart.\n- Assignment Step: This step has substantial changes encompassing the transition from ringing \'groups\' to \'agents\' for call assignment, the time limit extended from 200 to 360 seconds, and other property-level alterations.\n- New Step: Play Audio: This step is recently introduced into the flowchart to play a specific audio message stating, "Sorry, please leave your message, we\'ll call you back.” It has been inserted between Assignment and End call step.\nThe significant changes, including the omission of the \'Recording\' step, the shift to individual agent assignment, and the new audio message step, directly impact the call-routing process and the customer experience.'
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
            ("human", "{diff_json}"),
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

generate_diff_chain = create_diff_chain()
