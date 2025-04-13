from enum import Enum, auto


class SenderType(Enum):
    """Enum for who sent a message in a chat."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
