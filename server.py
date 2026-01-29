"""
FastAPI server with Slack webhook integration and /generate endpoint
"""

import traceback
from bson import ObjectId
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, PlainTextResponse
import hmac
import hashlib
import json
import os
from datetime import datetime
from typing import List

from db import init_db, close_db, db
from models import GeneratedResponse, XPost, LinkedInPost, PostEvaluation
from llm import final_graph


# Initialize FastAPI app
app = FastAPI(
    title="ContentBot",
    description="Slack conversation to social media content generator",
    version="0.1.0"
)


# ============================================================================
# STARTUP / SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()
    print("Server started - Database connected")


@app.on_event("shutdown")
async def shutdown_event():
    """Close database on shutdown"""
    close_db()
    print("Server stopped - Database closed")


# ============================================================================
# SLACK WEBHOOK VERIFICATION
# ============================================================================

def verify_slack_request(request_body: bytes, timestamp: str, signature: str) -> bool:
    """
    Verify that the request came from Slack using request signature.
    Based on Slack's request verification documentation.
    """
    signing_secret = os.getenv('SLACK_SIGNING_SECRET')
    signing_version = os.getenv('SLACK_SIGNING_VERSION', 'v0')

    if not signing_secret:
        print("Warning: SLACK_SIGNING_SECRET not set")
        return False

    # Check timestamp is recent (within 5 minutes) unless overridden for dev/testing
    allow_old = os.getenv('SLACK_ALLOW_OLD_TIMESTAMP',
                          'false').lower() in ('1', 'true', 'yes')
    try:
        req_timestamp = int(float(timestamp))
    except Exception:
        print("Timestamp parse failed")
        if not allow_old:
            return False
        req_timestamp = 0

    current_time = int(datetime.utcnow().timestamp())

    if not allow_old and abs(current_time - req_timestamp) > 300:
        print(f"Timestamp verification failed: request too old")
        return False
    elif allow_old and abs(current_time - req_timestamp) > 300:
        print("Warning: accepting old Slack timestamp due to SLACK_ALLOW_OLD_TIMESTAMP")

    # Verify signature
    basestring = f"{signing_version}:{timestamp}:{request_body.decode()}"
    computed_hash = hmac.new(signing_secret.encode(
    ), basestring.encode(), hashlib.sha256).hexdigest()
    computed_sig = f"{signing_version}={computed_hash}"

    return hmac.compare_digest(computed_sig, signature)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/generate")
async def generate_posts():
    """
    Generate social media posts from messages in the last 24 hours.

    Process:
    1. Fetch messages from last 24h
    2. Run LLM pipeline (chunking, generation, evaluation)
    3. Store chunks and responses in MongoDB
    4. Return generated response IDs
    """
    try:
        # Get messages from last 24 hours
        messages = db.get_messages_last_24h()

        if not messages:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "No messages found in last 24 hours",
                    "messages_processed": 0,
                    "chunks_created": 0,
                    "responses_created": 0,
                    "response_ids": []
                }
            )

        print(f"Processing {len(messages)} messages")

        # Run LLM pipeline
        result = final_graph.invoke({
            'messages': messages,
            'max_iterations_per_job': 3
        })

        # Store chunks in database
        chunks = result.get('chunks', [])
        inserted_chunks = db.insert_message_chunks_batch(chunks)
        print(f"Stored {len(chunks)} chunks")

        # Process jobs and store responses
        jobs_result = result.get('jobs_result', [])
        responses_to_store = []

        for job in jobs_result:
            # Extract relevant fields from job
            chunk_id = job['chunk']['_id']
            platform = job['platform']

            # Build response based on platform
            if platform == 'x':
                x_post = job.get('x_post')
                response = GeneratedResponse(
                    chunk_id=ObjectId(chunk_id),
                    platform=platform,
                    x_post=XPost(**x_post) if x_post else None,
                    evaluation=PostEvaluation(
                        **job.get('evaluation')) if job.get('evaluation') else None,
                    evaluation_passed=job.get('evaluation_passed', False)
                )
            elif platform == 'linkedin':
                linkedin_post = job.get('linkedin_post')
                response = GeneratedResponse(
                    chunk_id=ObjectId(chunk_id),
                    platform=platform,
                    linkedin_post=LinkedInPost(
                        **linkedin_post) if linkedin_post else None,
                    evaluation=PostEvaluation(
                        **job.get('evaluation')) if job.get('evaluation') else None,
                    evaluation_passed=job.get('evaluation_passed', False)
                )
            else:
                continue

            responses_to_store.append(response)

        # Store responses
        response_ids = []
        if len(responses_to_store):
            response_ids = db.insert_generated_responses_batch(
                responses_to_store)
            print(f"Stored {len(responses_to_store)} generated responses")

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "messages_processed": len(messages),
                "chunks_created": len(chunks),
                "responses_created": len(responses_to_store),
                "response_ids": response_ids,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    except Exception as e:
        print(f"Error in /generate endpoint: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Generation failed: {str(e)}")


@app.post("/webhook/slack")
async def slack_webhook(request: Request):
    """
    Slack webhook endpoint to receive real-time messages.

    Slack sends event data which we store in MongoDB.
    """
    try:
        # Read request body first
        body = await request.body()
        print(body)

        # Parse JSON early to handle url_verification without strict header requirement
        data = json.loads(body)

        # Handle Slack URL verification challenge (respond with plain text)
        if data.get('type') == 'url_verification':
            return PlainTextResponse(content=data.get('challenge', ''), status_code=200)

        # Handle events
        if data.get('type') == 'event_callback':
            event = data.get('event', {})

            if event.get('type') == 'message':
                subtype = event.get('subtype')

                # Handle regular new messages (no subtype, not from bot)
                if not subtype and 'bot_id' not in event:
                    user = event.get('user', 'unknown')
                    text = event.get('text', '')
                    ts = event.get('ts', '')
                    team_id = data.get('team_id', '')
                    timestamp_ts = int(float(ts)) if ts else 0
                    channel = event.get('channel', '')
                    thread_ts = event.get('thread_ts')  # Optional

                    msg_id = db.insert_message(
                        user=user,
                        text=text,
                        team_id=team_id,
                        ts=ts,
                        timestamp=timestamp_ts,
                        channel=channel,
                        thread_id=thread_ts
                    )
                    print(f"Stored message {msg_id} from {user}")

                # Handle message_changed events
                elif subtype == 'message_changed':
                    changed = event.get('message', {})
                    ts = changed.get('ts', '')
                    thread_ts = changed.get('thread_ts')
                    channel = event.get('channel', '')
                    team_id = data.get('team_id', '')

                    if ts and thread_ts:
                        db.update_message_thread(
                            team_id, channel, ts, thread_ts)
                        print(
                            f"Updated message thread: {ts} -> thread_id={thread_ts}")

                    if ts and 'text' in changed:
                        db.update_message_text(
                            team_id, channel, ts, changed['text'])
                        print(f"Updated message text: {ts}")

        return JSONResponse({"ok": True})

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in /webhook/slack: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Webhook failed: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({"status": "ok", "timestamp": datetime.utcnow().isoformat()})


@app.get("/docs")
async def docs():
    """API documentation"""
    return JSONResponse({
        "title": "ContentBot API",
        "description": "Generate social media content from Slack conversations",
        "endpoints": {
            "POST /generate": "Generate posts from last 24h messages",
            "POST /webhook/slack": "Receive Slack events",
            "GET /health": "Health check",
            "GET /docs": "This documentation"
        }
    })


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv('SERVER_PORT', 8000))
    host = os.getenv('SERVER_HOST', '0.0.0.0')

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
