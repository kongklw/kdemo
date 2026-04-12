from rest_framework.views import APIView
from rest_framework import permissions
from rest_framework.response import Response
import os
from typing import Any, Optional
from utils.llm_model import llm_openai, llm_chat

import logging
logger = logging.getLogger(__name__)

_model: Optional[Any] = None


def _get_tongyi_model() -> Any:
    global _model
    if _model is not None:
        return _model

    from langchain_community.llms.tongyi import Tongyi

    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise ValueError("Missing env var: DASHSCOPE_API_KEY")

    model_name = os.getenv("DASHSCOPE_MODEL", "qwen-plus")
    _model = Tongyi(model=model_name, api_key=api_key)
    return _model


class CommonView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        print(f'hahah')
        try:
            model = llm_chat(model='qwen3.5-plus')
            ans = model.invoke(input="你是谁")
            return Response({"code": 200, "msg": "ok", "data": {"answer": ans}})
        except Exception as e:
            logger.exception(e)
            return Response({"code": 500, "msg": str(e), "data": None})
