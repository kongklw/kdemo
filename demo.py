import os
import sys


def main() -> int:
    try:
        from dotenv import load_dotenv
    except Exception:
        load_dotenv = None

    if load_dotenv is not None:
        load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing env var: DASHSCOPE_API_KEY")

    # model_name = os.getenv("DASHSCOPE_MODEL", "tongyi-xiaomi-analysis-pro")
    model_name = os.getenv("DASHSCOPE_MODEL", "qwen3.5-122b-a10b")

    base_http_api_url = None
    try:
        import dashscope

        base_http_api_url = getattr(dashscope, "base_http_api_url", None)
    except Exception:
        base_http_api_url = None

    print(f"model_name={model_name}")
    print(f"dashscope_base_http_api_url={base_http_api_url}")

    from langchain_community.llms.tongyi import Tongyi

    llm = Tongyi(model=model_name, api_key=api_key)
    text = llm.invoke(input="你是谁？请用一句话回答。")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
