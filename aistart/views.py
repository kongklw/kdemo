from django.shortcuts import render
from rest_framework.views import APIView
from openai import OpenAI
from rest_framework.response import Response
from kdemo import settings

client = OpenAI(
    api_key=settings.OPENAI_API_KEY
)


class OpenAIView(APIView):

    def post(self, request, *args, **kwargs):
        data = request.data
        content = data.get("content")
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            store=True,
            messages=[
                {"role": "user", "content": content}
            ]
        )
        msg = completion.choices[0].message.content

        return Response({'code': 200, 'data': msg, 'msg': 'ok'})
