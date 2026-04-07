from __future__ import annotations

from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole


def _apply_stop_sequences(text: str, stop_sequences: list[str] | None) -> str:
    if not stop_sequences:
        return text
    stop_at = None
    for sequence in stop_sequences:
        index = text.find(sequence)
        if index != -1 and (stop_at is None or index < stop_at):
            stop_at = index
    return text if stop_at is None else text[:stop_at]


def _normalize_messages(messages, system_prompt: str = "", prefill: str = "") -> list[Messages]:
    normalized: list[Messages] = []
    if system_prompt:
        normalized.append(Messages(role=MessagesRole.SYSTEM, content=system_prompt))
    for message in messages:
        if isinstance(message, Messages):
            normalized.append(message)
            continue
        if isinstance(message, dict):
            role = message.get("role", "user")
            content = message.get("content", "")
        else:
            role = "user"
            content = str(message)
        if role == "assistant":
            role_enum = MessagesRole.ASSISTANT
        elif role == "system":
            role_enum = MessagesRole.SYSTEM
        else:
            role_enum = MessagesRole.USER
        normalized.append(Messages(role=role_enum, content=content))
    if prefill:
        normalized.append(Messages(role=MessagesRole.ASSISTANT, content=prefill))
    return normalized


class GigaChatRunner:
    def run(
        self,
        *,
        credentials: str,
        model: str,
        prompt_or_messages,
        system_prompt: str = "",
        prefill: str = "",
        stop_sequences: list[str] | None = None,
    ) -> str:
        client = GigaChat(credentials=credentials, verify_ssl_certs=False)
        if isinstance(prompt_or_messages, (list, tuple)):
            messages = _normalize_messages(prompt_or_messages, system_prompt=system_prompt, prefill=prefill)
        else:
            messages = []
            if system_prompt:
                messages.append(Messages(role=MessagesRole.SYSTEM, content=system_prompt))
            messages.append(Messages(role=MessagesRole.USER, content=str(prompt_or_messages)))
            if prefill:
                messages.append(Messages(role=MessagesRole.ASSISTANT, content=prefill))
        chat = Chat(model=model, max_tokens=2000, temperature=0.0, messages=messages)
        response = client.chat(chat)
        text = response.choices[0].message.content
        return _apply_stop_sequences(text, stop_sequences)
