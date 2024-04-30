from operator import itemgetter
from langchain_openai import ChatOpenAI
from langchain_core.language_models import LanguageModelLike
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import (
    ConfigurableField,
    Runnable,
    RunnableBranch,
    RunnableLambda
)

RESPONSE_TEMPLATE = """\
Given the following conversation and a follow up question, rephrase the follow up \
question to be a standalone question.

```json
{flow_json}
```
Follow Up Input: {question}
Standalone Question:"""

def create_general_chain (llm: LanguageModelLike) -> Runnable:
    prompt = PromptTemplate.from_template(RESPONSE_TEMPLATE)
    chain = (
        prompt | llm | StrOutputParser()
    )
    return chain


openai_gpt = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
llm = openai_gpt.configurable_alternatives(
    ConfigurableField(id="llm"),
    default_key="openai_gpt",
).with_fallbacks(
    [openai_gpt]
)

general_chain = create_general_chain(llm)