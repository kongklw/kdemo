from datetime import datetime
from kdemo import settings
from openai import OpenAI


def convert_string_datetime(string):
    return datetime.strptime(string, '%Y-%m-%dT%H:%M:%S')

def convert_string_date(string):
    return datetime.strptime(string, '%Y-%m-%d')



def convert_seconds(seconds):
    hours = seconds // 3600
    min = (seconds % 3600) // 60
    sec = seconds % 60

    return "{}h {}m {}s".format(hours, min, sec)


client = OpenAI(
    api_key=settings.OPENAI_API_KEY
)


alibaba_client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
    api_key=settings.DASHSCOPE_API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

