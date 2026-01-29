"""
Pydantic models for MongoDB collections
"""

from bson import ObjectId
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
from uuid import uuid4


# ============================================================================
# Messages Collection
# ============================================================================

class Message(BaseModel):
    """Slack message with flat hierarchy"""
    user: str
    text: str
    team_id: str
    ts: str
    timestamp: int
    thread_id: Optional[str] = None
    channel: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "user": "alex",
                "team_id": "T123456",
                "ts": "1691480000.000200",
                "text": "Have you looked into ClawDBot lately?",
                "timestamp": 1769594405,
                "thread_id": None,
                "channel": "general",
                "created_at": "2026-01-29T10:00:00"
            }
        }


# ============================================================================
# MessageChunks Collection
# ============================================================================

class MessageChunk(BaseModel):
    """Chunk information from LLM analysis"""
    topic: str
    summary: str
    message_ids: List[ObjectId]
    is_content_worthy: bool
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "topic": "Privacy Concerns with ClawDBot",
                "summary": "Discussion about ClawDBot data collection practices",
                "message_ids": [0, 1, 2, 3, 4, 5],
                "is_content_worthy": True,
                "created_at": "2026-01-29T10:00:00"
            }

        }


# ============================================================================
# GeneratedResponse Collection
# ============================================================================

class XPost(BaseModel):
    """X/Twitter post structure"""
    hook: str
    tweets: List[str]


class LinkedInPost(BaseModel):
    """LinkedIn post structure"""
    content: str
    hook: str
    cta: str


class PostEvaluation(BaseModel):
    """Post evaluation scores"""
    external_value_score: int
    authenticity_score: int
    clarity_score: int
    engagement_score: int
    reasoning: str


class GeneratedResponse(BaseModel):
    """Generated post response from LLM pipeline"""
    chunk_id: ObjectId
    platform: Literal['x', 'linkedin']
    x_post: Optional[XPost] = None
    linkedin_post: Optional[LinkedInPost] = None
    evaluation: Optional[PostEvaluation] = None
    evaluation_passed: bool
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "chunk_id": 0,
                "platform": "x",
                "x_post": {
                    "hook": "Just realized ClawDBot has a serious privacy problem.",
                    "tweets": ["ClawDBot is reading message contents without clear opt-in.", "This is spyware-level behavior."]
                },
                "linkedin_post": None,
                "evaluation": {
                    "external_value_score": 8,
                    "authenticity_score": 9,
                    "clarity_score": 8,
                    "engagement_score": 7,
                    "reasoning": "Strong post addressing privacy concerns with tactical insights"
                },
                "evaluation_passed": True,
                "created_at": "2026-01-29T10:00:00"
            }
        }
