from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from utils import alibaba_client, client


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

        msg = alibaba_llm(content)

        return Response({'code': 200, 'data': msg, 'msg': 'ok'})
