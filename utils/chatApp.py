import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage, trim_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langchain_core.prompts import ChatPromptTemplate, ChatMessagePromptTemplate, MessagesPlaceholder
from typing import Sequence
from typing_extensions import Annotated, TypedDict
from langgraph.graph.message import add_messages
from kdemo import settings

os.environ["LANGSMITH_TRACING"] = settings.LANGSMITH_TRACING
os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY

# alibaba model
model = ChatOpenAI(
    api_key=settings.DASHSCOPE_API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    model="qwen-vl-max-latest",
)

json_model = model.bind(response_format={"type": "json_object"})

prompt_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful assistant. Answer all questions to the best of your ability in {language}",
        ),
        MessagesPlaceholder(variable_name="messages")
    ]
)


class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    language: str


def call_model(state: State):
    prompt = prompt_template.invoke(state)
    response = json_model.invoke(prompt)

    # trimmed_messages = trimmer.invoke(state["messages"])
    # prompt = prompt_template.invoke(
    #     {"messages": trimmed_messages, "language": state["language"]})
    # response = model.invoke(prompt)
    return {"messages": [response]}


def call_model_json(state: State):
    prompt = prompt_template.invoke(state)
    response = json_model.invoke(prompt)
    return {"messages": [response]}


def obtain_app(type='norm'):
    workflow = StateGraph(state_schema=State)
    workflow.add_edge(START, 'model')
    if type == 'json':
        workflow.add_node('model', call_model_json)
    else:
        workflow.add_node('model', call_model)

    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    return app
