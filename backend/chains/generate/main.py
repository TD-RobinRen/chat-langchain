from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnablePassthrough
from chains.generate.extract_chain import extract_chain
from chains.generate.generate_func_chain import generate_func_chain
from chains.generate.output_chain import output_chain

def serialize_history(request):
    chat_history = request["chat_history"] or []
    converted_chat_history = []
    for message in chat_history:
        if message.get("human") is not None:
            converted_chat_history.append(HumanMessage(content=message["human"]))
        if message.get("ai") is not None:
            converted_chat_history.append(AIMessage(content=message["ai"]))
    return converted_chat_history

generate_chain = (
        RunnablePassthrough.assign(chat_history=serialize_history)
        |
        {
            "extracted_data": extract_chain
        }
        |
        generate_func_chain
        |
        output_chain
    )
