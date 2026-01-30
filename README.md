# 🤖 Influencer Aunty

> Just like our friendly neighbourhood aunty who sneaks into our chats and generates content.

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-latest-orange.svg)](https://github.com/langchain-ai/langgraph)
[![MongoDB](https://img.shields.io/badge/MongoDB-latest-green.svg)](https://www.mongodb.com/)

---

## 📖 Overview

**Influencer Aunty** is a Slack bot that listens to your channel conversations and helps you generate engaging LinkedIn and X (Twitter) posts based on your actual discussions. Simply ask the bot, and it transforms your team's conversations into platform-optimized social media content.

### ✨ Key Features

- 🎧 **Passive Listening**: Sits quietly in your Slack channel, observing conversations
- 🎯 **Topic Chunking**: Intelligently groups messages by conversation topics using LLM-powered semantic analysis
- 🔄 **Parallel Generation**: Creates LinkedIn and X posts simultaneously using LangGraph's parallel execution
- 🎨 **Smart Evaluation**: Scores each post on authenticity, clarity, engagement potential, and value
- ♻️ **Iterative Refinement**: Automatically regenerates failed posts with feedback
- 💾 **MongoDB Storage**: Persists conversation history and generated posts
- 🚀 **On-Demand**: Generate posts only when you ask for them

### 🏗️ How It Works

```
Slack Channel Messages → Webhook → FastAPI Server → Storage

                    LangGraph Pipeline (With Storage)
                                   ↓
               ┌───────────────────┴───────────────────┐
               ▼                                       ▼
         Twitter Branch                         LinkedIn Branch
   (Generate → Evaluate → Loop)           (Generate → Evaluate -> Loop)
               ↓                                       ▼
               └───────────────────┬───────────────────┘
                                   ▼
                           Merge Results → MongoDB
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** installed
- **[uv](https://github.com/astral-sh/uv)** package manager
- **MongoDB** instance (local or [MongoDB Atlas](https://www.mongodb.com/cloud/atlas))
- **Slack workspace** with admin access
- **OpenAI API key**

---

## 📦 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/c0dysharma/influencer-aunty.git
cd influencer-aunty
```

### 2. Install uv and Dependencies

If you don't have `uv` installed:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Then install project dependencies:

```bash
# Sync dependencies with uv
uv sync
```

### 3. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Open `.env` and fill in your credentials. Here's what each variable means:

```env
OPENAI_API_KEY=sk-ant-xxxxx

# === MongoDB ===
MONGODB_URI=mongodb://localhost:27017
# For local: mongodb://localhost:27017
# For Atlas: mongodb+srv://username:password@cluster.mongodb.net/

MONGODB_DB_NAME=influencer_aunty
# Database name for storing conversations and posts

# === Slack Bot Credentials ===
SLACK_BOT_TOKEN=xoxb-xxxxx-xxxxx-xxxxxxxxxxxxx
SLACK_SIGNING_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# === FastAPI Server ===
SERVER_PORT=8000
SERVER_HOST=0.0.0.0
```

---

## 🔧 Slack App Setup

Follow these steps to create and configure your Slack bot:

### Step 1: Create a New Slack App

1. Visit [https://api.slack.com/apps](https://api.slack.com/apps)
2. Click **"Create New App"**
3. Select **"From scratch"**
4. Give it a name: `Influencer Aunty`
5. Select your workspace

### Step 2: Configure OAuth Scopes

Go to **OAuth & Permissions** in the sidebar and scroll to **Bot Token Scopes**. Add these scopes:

| Scope | Description | Why We Need It |
|-------|-------------|----------------|
| `channels:history` | View messages in public channels | Read conversation history |
| `channels:read` | View basic channel info | Access channel metadata |
| `chat:write` | Send messages as bot | Reply with post suggestions |
| `users:read` | View user info | Identify message authors |
| `app_mentions:read` | Listen for @mentions | Trigger on bot mentions |

### Step 3: Enable Event Subscriptions

1. Go to **Event Subscriptions** in the sidebar
2. Toggle **Enable Events** to **ON**
3. For **Request URL**, you need a public endpoint:

#### Local Development (using ngrok)

```bash
# Install ngrok from https://ngrok.com/download
# Start your FastAPI server first
uvicorn server:app --reload --port 8000

# In another terminal, expose it
ngrok http 8000
```

Copy the `https://` URL from ngrok (e.g., `https://abc123.ngrok-free.app`) and add `/webhook/slack`:

```
https://abc123.ngrok-free.app/webhook/slack
```

#### Production

Use your domain:
```
https://your-domain.com/webhook/slack
```

4. Under **Subscribe to bot events**, add:
   - `message.channels` - Messages posted to public channels
   - `app_mention` - When the bot is @mentioned

5. Click **Save Changes**

### Step 4: Install App to Workspace

1. Go to **Install App** in the sidebar
2. Click **Install to Workspace**
3. Review permissions and click **Allow**
4. Copy the **Bot User OAuth Token** (starts with `xoxb-`)
5. Paste it into your `.env` file as `SLACK_BOT_TOKEN`

### Step 5: Get Your Signing Secret

1. Go to **Basic Information** in the sidebar
2. Scroll to **App Credentials**
3. Copy the **Signing Secret**
4. Paste it into your `.env` file as `SLACK_SIGNING_SECRET`

### Step 6: Invite Bot to Your Channel

In your desired Slack channel, type:

```
/invite @Influencer Aunty
```

The bot should now appear in your channel! 🎉

---

## 🎮 Usage

### Start the Server

Activate your virtual environment and run:

```bash
# Using uv
uv run uvicorn server:app --reload

# Or if you activated the venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uvicorn server:app --reload
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### Generate Posts

In your Slack channel, simply mention the bot and ask:

```
@Influencer Aunty today
```


### What Happens Next

The bot will:
1. ✅ Fetch recent messages from the channel
2. ✅ Chunk them by conversation topic
3. ✅ Generate LinkedIn + X posts in parallel
4. ✅ Evaluate each post (score out of 40)
5. ✅ Retry failed posts with feedback
6. ✅ Reply in the thread with final suggestions

---

## 🛣️ Roadmap

- [ ] Different evaluator to check is_content_worthy
- [ ] How to efficiently handle thousands of messages ?
- [ ] Evaluate different models which works best
- [ ] Tools to check trends
- [ ] Generate based on user persona

---

## 🤝 Contributing

Contributions are welcome! Here's how:

1. Fork the repo
2. Create a branch: `git checkout -b feature/cool-feature`
3. Make your changes
4. Commit: `git commit -m 'Add cool feature'`
5. Push: `git push origin feature/cool-feature`
6. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

## 🙏 Acknowledgments

Built with:
- [LangGraph](https://github.com/langchain-ai/langgraph) - Agentic workflow orchestration
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [MongoDB](https://www.mongodb.com/) - Document database
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager

---

## 📬 Contact

**Kuldeep Sharma** - [@c0dysharma](https://github.com/c0dysharma)

**Email**: codysharma01@gmail.com

**Project Link**: [github.com/c0dysharma/influencer-aunty](https://github.com/c0dysharma/influencer-aunty)

---

<div align="center">

**⭐ If this project helped you, consider giving it a star!**

Made with ☕ and 💻 in India

</div>