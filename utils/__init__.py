from datetime import datetime
from kdemo import settings


def convert_string_datetime(string):
    return datetime.strptime(string, '%Y-%m-%dT%H:%M:%S')


def convert_string_date(string):
    return datetime.strptime(string, '%Y-%m-%d')


def convert_seconds(seconds):
    hours = seconds // 3600
    min = (seconds % 3600) // 60
    sec = seconds % 60

    return "{}h {}m".format(hours, min)


class LazyOpenAIClient:
    def __init__(self, **kwargs):
        self._kwargs = kwargs
        self._client = None

    def _get(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(**self._kwargs)
        return self._client

    def __getattr__(self, item):
        return getattr(self._get(), item)


client = LazyOpenAIClient(api_key=settings.OPENAI_API_KEY)
alibaba_client = LazyOpenAIClient(
    api_key=settings.DASHSCOPE_API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
