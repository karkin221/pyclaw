"""
Session — what the Gateway resolves every inbound message to
(docs/concepts/session.md). Real sessions are keyed by channel/account/peer,
persisted to SQLite, and support daily/idle resets, archiving, and search.

This is the minimum that still means something: a key and an in-memory list
of chat messages.
"""
from dataclasses import dataclass, field


@dataclass
class Session:
    session_key: str
    history: list[dict] = field(default_factory=list)
