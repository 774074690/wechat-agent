from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    message: str
    contact: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    tool_used: str = "qwen"

class AgentStatus(BaseModel):
    running: bool
    contacts: list[str]
    send_method: str
    logs: list[str] = []
