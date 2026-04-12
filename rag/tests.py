from django.test import TestCase
from langchain_openai import ChatOpenAI
# Create your tests here.
from dotenv import load_dotenv
import os
# load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

api_key = "sk-d3bee7338d164ababa70506e271ce474"
print(f'api_key: {api_key}')
model = ChatOpenAI(
    api_key=api_key,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    # model="qwen-vl-max-latest",
    model="qwen3.5-35b-a3b",
)

text = model.invoke(input="你是谁？请用一句话回答。")
print(text)
