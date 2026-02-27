import os
import re
import sys

from ollama import Client
from pydantic import BaseModel

SYSTEM_PROMPT = """あなたは優秀な日本語堪能なプログラマです。
ユーザーの指示にタスクの内容が要件を満たしているかどうかを判断しなさい

出力は下記のフォーマットのJSONのみ
# 問題ない場合の出力
{ "ok": true }
# 問題ある場合の出力
{ "ok": false, "reason": "理由", "suggestion": "改善案" }
"""

USER_PROMPT_TEMPLATE = """
# 課題
---
# {title}
# prompt
{prompt}
# context
{context}
---

# 問題
上記タスク内容が、下記要件を満たしているかどうか判断しなさい
- 「達成すべき状態（What）」が明確に記述されていること。

# 出力
出力は下記のフォーマットのJSONのみ
# 問題ない場合の出力
{{ "ok": true }}
# 問題ある場合の出力
{{ "ok": false, "reason": "理由", "suggestion": "改善案" }}
""".strip()


def clean_json_response(content: str) -> str:
    # ```json ... ``` を取り除く
    content = re.sub(r"```json\s*", "", content, flags=re.DOTALL)
    content = re.sub(r"```\s*$", "", content, flags=re.DOTALL)
    return content.strip()


class ValidateResult(BaseModel):
    ok: bool
    reason: str | None = None
    suggestion: str | None = None


def validate_task(title: str, prompt: str, context: str, debug: bool = False):
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
        options={
            "temperature": 0.2,
        },
    )
    if debug:
        print(
            USER_PROMPT_TEMPLATE.format(title=title, prompt=prompt, context=context),
        )
        from pprint import pprint

        pprint(response)

    data = ValidateResult.model_validate_json(clean_json_response(response.message.content))  # type: ignore

    return data


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()
    from django.core.management import execute_from_command_line

    from todo.models import Todo

    todo = Todo.objects.get(pk=sys.argv[1])
    print(validate_task(title=todo.title, prompt=todo.prompt, context=todo.context, debug=True))
