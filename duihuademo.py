"""
mindcraft_client.py
通用调用 MindCraft abab6.5s-chat 的轻量封装
"""
import os
from openai import OpenAI

# -------------------- 配置 --------------------
BASE_URL = "https://api.mindcraft.com.cn/v1/"
API_KEY  = os.getenv("MC_API_KEY", "MC-8962555AEC864AAA9627C0F15E275A1B")   # 建议用环境变量
MODEL    = "GLM-4-Flash"
CLIENT   = OpenAI(base_url=BASE_URL, api_key=API_KEY)

# -------------------- 工具函数 --------------------
def chat_once(messages: list[dict], *, max_tokens=4000, temp=0.2, reason=False) -> str:
    """
    同步一次性返回完整结果
    messages: [{"role":"system/user","content":"..."}, ...]
    """
    resp = CLIENT.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=temp,
        max_tokens=max_tokens,
        stream=False,
        extra_body={"reason": reason}
    )
    # resp.usage 里会返回 token 用量
    return resp.choices[0].message.content


def chat_stream(messages: list[dict], *, max_tokens=4000, temp=0.2, reason=False):
    """
    流式生成器，逐句 yield 字符串
    用法：
        for chunk in chat_stream(messages):
            print(chunk, end="", flush=True)
    """
    stream = CLIENT.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=temp,
        max_tokens=max_tokens,
        stream=True,
        extra_body={"reason": reason}
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


# -------------------- 自测 --------------------
if __name__ == "__main__":
    msgs = [
        {"role": "system", "content": "你是门酱，是一个喜欢搞抽象的网络乐子人。"},
        {"role": "user",   "content": "你好！你是谁？你能做什么？"}
    ]

    # 1. 同步调用
    print("【同步】")
    print(chat_once(msgs))

    # 2. 流式调用
    print("\n【流式】")
    for seg in chat_stream(msgs):
        print(seg, end="", flush=True)