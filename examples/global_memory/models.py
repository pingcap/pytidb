from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class Message:
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


@dataclass
class SessionSummary:
    session_id: str
    summary: str
    message_count: int
    start_time: datetime
    end_time: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "summary": self.summary,
            "message_count": self.message_count,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionSummary":
        return cls(
            session_id=data["session_id"],
            summary=data["summary"],
            message_count=data["message_count"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]),
        )


@dataclass
class ChatSession:
    session_id: str
    messages: List[Message]
    start_time: datetime
    is_active: bool
    memory_enabled: bool
    previous_summaries: List[SessionSummary]

    def add_message(self, role: str, content: str) -> None:
        message = Message(role=role, content=content, timestamp=datetime.now())
        self.messages.append(message)

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get conversation history in format expected by LiteLLM"""
        history = []

        # Add previous session summaries if memory is enabled
        if self.memory_enabled and self.previous_summaries:
            combined_summary = self._combine_summaries()
            if combined_summary:
                history.append(
                    {
                        "role": "system",
                        "content": f"Previous conversation context: {combined_summary}",
                    }
                )

        # Add current session messages
        for message in self.messages:
            history.append({"role": message.role, "content": message.content})

        return history

    def _combine_summaries(self) -> str:
        """Combine multiple session summaries into a coherent context"""
        if not self.previous_summaries:
            return ""

        summaries_text = []
        for summary in self.previous_summaries:
            summaries_text.append(f"Session {summary.session_id}: {summary.summary}")

        return " | ".join(summaries_text)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "messages": [msg.to_dict() for msg in self.messages],
            "start_time": self.start_time.isoformat(),
            "is_active": self.is_active,
            "memory_enabled": self.memory_enabled,
            "previous_summaries": [
                summary.to_dict() for summary in self.previous_summaries
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatSession":
        return cls(
            session_id=data["session_id"],
            messages=[Message.from_dict(msg) for msg in data["messages"]],
            start_time=datetime.fromisoformat(data["start_time"]),
            is_active=data["is_active"],
            memory_enabled=data["memory_enabled"],
            previous_summaries=[
                SessionSummary.from_dict(summary)
                for summary in data["previous_summaries"]
            ],
        )


@dataclass
class AppState:
    """Application state for Streamlit session management"""

    current_session: Optional[ChatSession]
    memory_enabled: bool
    session_history: List[str]  # List of session IDs

    def __init__(self):
        self.current_session = None
        self.memory_enabled = True
        self.session_history = []
