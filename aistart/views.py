import uuid
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from utils import alibaba_client, client
from django.core.cache import cache
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage, trim_messages
from django_redis import get_redis_connection
from utils.chatApp import obtain_app

con = get_redis_connection("default")  # Use the name you have defined for Redis in settings.CACHES
connection_pool = con.connection_pool
print("Created connections so far: %d" % connection_pool._created_connections)


def openai_llm(content):
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        store=True,
        messages=[
            {"role": "user", "content": content}
        ]
    )
    return completion.choices[0].message.content


def alibaba_llm(content):
    completion = alibaba_client.chat.completions.create(
        model="qwen-plus",  # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
        messages=[
            {'role': 'system', 'content': 'You are a helpful assistant.'},
            {'role': 'user', 'content': content}],
    )

    return completion.choices[0].message.content


class OpenAIView(APIView):

    def post(self, request, *args, **kwargs):
        data = request.data
        content = data.get("content")
        thread_id = data.get("thread_id")
        if len(thread_id) == 0:
            thread_id = str(uuid.uuid4())

        app = obtain_app()
        language = "chinese"
        config = {"configurable": {"thread_id": thread_id}}

        output = app.invoke({"messages": [{"role": "user", "content": content}], "language": language}, config)
        msg = output["messages"][-1].content

        # output = app.invoke({"messages": [{"role": "user", "content": "我的名字叫什么"}], "language": language}, config)
        # res2 = output["messages"][-1].content
        # print(res2)

        return Response({'code': 200, 'data': {"msg": msg, "thread_id": thread_id}, 'msg': 'ok'})
