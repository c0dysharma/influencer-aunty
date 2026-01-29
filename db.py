"""
MongoDB database layer for messages, chunks, and generated responses
"""

from bson import ObjectId
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import os
from models import MessageChunk, GeneratedResponse


class Database:
    """MongoDB database connection and operations"""

    def __init__(self):
        self.uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
        self.db_name = os.getenv('MONGODB_DB_NAME', 'influencer-aunty')
        self.client = None
        self.db = None

    def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            print(f"Connected to MongoDB: {self.db_name}")
            self._create_indexes()
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            print(f"Failed to connect to MongoDB: {e}")
            raise

    def _create_indexes(self):
        """Create indexes for optimized queries"""
        # Messages collection
        self.db.messages.create_index('created_at')
        self.db.messages.create_index('thread_id')
        self.db.messages.create_index('channel')

        # Message chunks collection
        self.db.message_chunks.create_index('created_at')

        # Generated responses collection
        self.db.generated_responses.create_index('created_at')
        print("Indexes created")

    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            print("MongoDB connection closed")

    # ========================================================================
    # Messages Collection Operations
    # ========================================================================

    def insert_message(self, user: str, text: str, team_id: str, ts: str, timestamp: int, channel: str, thread_id: Optional[str] = None) -> int:
        """Insert a Slack message into MongoDB"""
        message = {
            'user': user,
            'text': text,
            'team_id': team_id,
            'ts': ts,
            'timestamp': timestamp,
            'channel': channel,
            'thread_id': thread_id,
            'created_at': datetime.utcnow()
        }
        result = self.db.messages.insert_one(message)
        return result.inserted_id

    def update_message_thread(self, team_id: str, channel: str, ts: str, thread_id: str) -> bool:
        """Update a message's thread_id using composite key (team_id, channel, ts)"""
        result = self.db.messages.find_one_and_update(
            {'team_id': team_id, 'channel': channel, 'ts': ts},
            {'$set': {'thread_id': thread_id}}
        )
        return result is not None

    def update_message_text(self, team_id: str, channel: str, ts: str, text: str) -> bool:
        """Update a message's text using composite key"""
        result = self.db.messages.find_one_and_update(
            {'team_id': team_id, 'channel': channel, 'ts': ts},
            {'$set': {'text': text}}
        )
        return result is not None

    def get_messages_last_24h(self) -> List[Dict[str, Any]]:
        """Get all messages from the last 24 hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        messages = list(self.db.messages.find(
            {'created_at': {'$gte': cutoff_time}},
            {'user': 1, 'text': 1, 'thread_id': 1}  # Exclude MongoDB _id
        ).sort('created_at', 1))

        # Add message_id based on position for LLM pipeline compatibility
        for idx, msg in enumerate(messages):
            msg['_id'] = str(msg['_id'])

        return messages

    def get_messages_by_thread(self, thread_id: str) -> List[Dict[str, Any]]:
        """Get all messages in a specific thread"""
        messages = list(self.db.messages.find(
            {'thread_id': thread_id},
            {'_id': 0}
        ).sort('created_at', 1))

        for idx, msg in enumerate(messages):
            msg['message_id'] = idx

        return messages

    # ========================================================================
    # Message Chunks Collection Operations
    # ========================================================================

    def insert_message_chunk(self, _id: str, topic: str, summary: str,
                             message_ids: List[str], is_content_worthy: bool) -> str:
        """Insert a message chunk from LLM analysis"""
        message_ids = [ObjectId(msg_id) for msg_id in message_ids]

        chunk = MessageChunk(
            _id=ObjectId(_id),
            topic=topic,
            summary=summary,
            message_ids=message_ids,
            is_content_worthy=is_content_worthy
        )
        result = self.db.message_chunks.insert_one(chunk.model_dump())
        return str(result.inserted_id)

    def insert_message_chunks_batch(self, chunks: List[Dict[str, Any]]) -> List[str]:
        """Insert multiple chunks at once"""
        chunk_dicts = [
            MessageChunk(
                _id=ObjectId(c['_id']),
                topic=c['topic'],
                summary=c['summary'],
                message_ids=[ObjectId(msg_id) for msg_id in c['message_ids']],
                is_content_worthy=c['is_content_worthy']
            ).model_dump()
            for c in chunks
        ]
        result = self.db.message_chunks.insert_many(chunk_dicts)
        return [str(id) for id in result.inserted_ids]

    # ========================================================================
    # Generated Responses Collection Operations
    # ========================================================================

    def insert_generated_response(self, response: GeneratedResponse) -> str:
        """Insert a generated response"""
        result = self.db.generated_responses.insert_one(response.model_dump())
        return str(result.inserted_id)

    def insert_generated_responses_batch(self, responses: List[GeneratedResponse]) -> List[str]:
        """Insert multiple generated responses at once"""
        response_dicts = [r.model_dump() for r in responses]
        result = self.db.generated_responses.insert_many(response_dicts)
        return [str(id) for id in result.inserted_ids]

    def get_generated_responses_by_chunk(self, _id: ObjectId) -> List[Dict[str, Any]]:
        """Get all generated responses for a specific chunk"""
        responses = list(self.db.generated_responses.find(
            {'_id': _id},
            {'_id': 0}
        ))
        return responses

    def get_generated_responses_last_24h(self) -> List[Dict[str, Any]]:
        """Get all generated responses from last 24 hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        responses = list(self.db.generated_responses.find(
            {'created_at': {'$gte': cutoff_time}},
            {'_id': 0}
        ).sort('created_at', -1))
        return responses


# Global database instance
db = Database()


def init_db():
    """Initialize database connection"""
    db.connect()


def close_db():
    """Close database connection"""
    db.close()
