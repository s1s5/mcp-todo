import os
import sys

from ollama import Client
from pydantic import BaseModel

SYSTEM_PROMPT = """あなたは優秀な日本語堪能なプログラマです。
ユーザーの指示にタスクの内容が要件を満たしているかどうかを判断しなさい

# 問題ない場合の出力
{ "ok": true }
# 問題ある場合の出力
{ "ok": false, "reason": "理由" }
"""

USER_PROMPT_TEMPLATE = """
---
# {title}
# prompt
{prompt}
# context
{context}
---

上記タスク内容が、下記要件を満たしているかどうか判断しなさい
- 実装方法の選択・条件分岐・設計判断を含まれていないこと
- 「達成すべき状態（What）」のみを記述し、その状態を実現するための方法（How）を推測・提案・列挙がされていないこと
- 実現手段に関するあらゆる判断をタスク内に含めていないこと。

"""


class ValidateResult(BaseModel):
    ok: bool
    reason: str | None = None


def validate_task(title: str, prompt: str, context: str):
    client = Client(host=os.environ["OLLAMA_HOST"])

    response = client.chat(
        model=os.environ["OLLAMA_MODEL"],
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": USER_PROMPT_TEMPLATE.format(title=title, prompt=prompt, context=context),
            },
        ],
        format=ValidateResult.model_json_schema(),
    )
    data = ValidateResult.model_validate_json(response.message.content)  # type: ignore

    return data


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line

    from todo.models import Todo

    todo = Todo.objects.get(pk=sys.argv[1])
    print(validate_task(title=todo.title, prompt=todo.prompt, context=todo.context))
