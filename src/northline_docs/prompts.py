from __future__ import annotations

SYSTEM_PROMPT = """
You answer questions about the Northline API from the retrieved documentation only.

Rules:
- If the user names v1 or v2, answer only for that version.
  Do not mix in the other version's fields, events, limits, or paths.
- If the retrieved documentation does not contain the answer, say you don't know.
  Do not fill the gap from general knowledge.
- Do not invent endpoints, body fields, headers, or event names.
- Do not provide API keys, webhook signing secrets, or access tokens.
  The documentation does not contain a usable key.
- Quote the version you are answering for when the user named one.
"""


def user_prompt(question: str, contexts: list[str], version: str | None) -> str:
    version_line = (
        "Version named by the user: none."
        if version is None
        else f"Version named by the user: {version}."
    )
    blocks = []
    for index, context in enumerate(contexts, start=1):
        blocks.append(f"[{index}]\n{context.strip()}")
    joined = "\n\n".join(blocks) if blocks else "(no documentation retrieved)"
    return f"{version_line}\n\nDocumentation:\n{joined}\n\nQuestion:\n{question}"
