import json
from operator import itemgetter
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import (
    Runnable,
    chain
)

RESPONSE_TEMPLATE = """\
Below is the generated json data, 
```json
{merged_json}
```
\n
But I realized that some fields may be missing, you can choose to click on the `Apply button` and the missing fields may go into the studio system on your own to be added.
\n
**Here is the missing field list:**
{error_messages_list}
"""

def serialize_error_messages(error_messages_list):
    converted_error_message = []
    for msg in error_messages_list:
        converted_error_message.append(f"- {msg}")
    return "\n".join(str(x) for x in converted_error_message)

@chain
def create_output_chain(input) -> Runnable:
    merged_json = json.dumps(itemgetter('merged_json')(input))
    error_messages_list = itemgetter('error_messages_list')(input)
    PROMPT = PromptTemplate.from_template(RESPONSE_TEMPLATE)
    return PROMPT.format(merged_json=merged_json, error_messages_list=serialize_error_messages(error_messages_list))

output_chain = create_output_chain