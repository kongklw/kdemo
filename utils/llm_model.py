from kdemo import settings
from langchain_openai import ChatOpenAI, OpenAI
import logging
# from langchain.chat_models import init_chat_model
# from langchain.agents import create_agent

logger = logging.getLogger(__name__)

# agent = create_agent(
#     model="claude-sonnet-4-6",
#     tools=[get_weather],
#     system_prompt="You are a helpful assistant",
# )



def llm_chat(model="qwen3.5-plus"):
    llm = ChatOpenAI(
        # model="qwen-vl-max-latest",
        model=model,
        api_key=settings.DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        temperature=0,
        streaming=True
    )
    json_llm = llm.bind(response_format={"type": "json_object"})

    return json_llm


def llm_openai(model='qwen3.5-plus'):
    llm = OpenAI(
        model=model,
        api_key=settings.OPENAI_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    json_llm = llm.bind(response_format={"type": "json_object"})
    return json_llm

'''

     stream = llm.stream(messages)
            full = next(stream)
            for chunk in stream:
                full += chunk
            full
'''