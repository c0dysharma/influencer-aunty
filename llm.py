from operator import add
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from typing import Annotated, TypedDict, Literal
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
import json
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# LLM INITIALIZATION
# ============================================================================

geimini_2_5_flash = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
)

open_ai_4_0_mini = init_chat_model('gpt-4o-mini')

# ============================================================================
# TYPE DEFINITIONS
# ============================================================================


class ChunkMessageOutput(TypedDict):
    topic: Annotated[str, 'Topic of the conversations it is about']
    summary: Annotated[str, 'Summary of this chunk of messages']
    message_ids: Annotated[list[int], 'List of ids for this conversations']
    is_content_worthy: Annotated[bool,
                                 'True if we can make a social media content about this chunk or not']


class ChunkingMessagesOutput(TypedDict):
    chunks: Annotated[list[ChunkMessageOutput],
                      'List of all the chunks made from past conversations']


class XGenerationOutput(TypedDict):
    hook: Annotated[str, 'Punchy hook very first line for the twitter post.']
    tweets: Annotated[list[str], 'List of one or many tweets on this topic.']


class LinkedinGenerationOutput(TypedDict):
    content: Annotated[str, 'Full LinkedIn post text (150-200 words)']
    hook: Annotated[str, 'Opening line that grabs attention']
    cta: Annotated[str, 'Call to action at the end of the post']


class PostEvaluationOutput(TypedDict):
    external_value_score: Annotated[int, 'Score 0-10: Useful to non-insiders?']
    authenticity_score: Annotated[int, 'Score 0-10: Genuine vs corporate?']
    clarity_score: Annotated[int, 'Score 0-10: Message clear?']
    engagement_score: Annotated[int, 'Score 0-10: Would people interact?']
    reasoning: Annotated[str, 'Explanation of the scores and evaluation']


class GeneratedChunksOutput(TypedDict, ChunkMessageOutput):
    chunk_id: int


class JobState(TypedDict):
    chunk: GeneratedChunksOutput
    platform: Literal['x', 'linkedin']
    chunk_messages: list[dict]

    x_post: XGenerationOutput
    linkedin_post: LinkedinGenerationOutput
    evaluation: PostEvaluationOutput
    evaluation_passed: bool

    iteration: int
    max_iterations: int


class GlobalState(TypedDict):
    messages: list[dict]
    chunks: list[GeneratedChunksOutput]
    jobs: Annotated[list[JobState], add]
    jobs_result: Annotated[list[JobState], add]
    max_iterations_per_job: int

# ============================================================================
# LLM CHAINS
# ============================================================================


chunking_llm = open_ai_4_0_mini.with_structured_output(ChunkingMessagesOutput)
x_generation_llm = open_ai_4_0_mini.with_structured_output(XGenerationOutput)
linkedin_generation_llm = open_ai_4_0_mini.with_structured_output(
    LinkedinGenerationOutput)
evaluation_llm = open_ai_4_0_mini.with_structured_output(PostEvaluationOutput)

# ============================================================================
# GRAPH FUNCTIONS
# ============================================================================


def chunk_messages(state: GlobalState) -> GlobalState:
    res = chunking_llm.invoke([
        SystemMessage(content="""Analyze these Slack messages and group them by conversation topic.

For each chunk, provide:
1. A clear topic name
2. A concise summary of the conversation
3. The message IDs included in this chunk
4. Content-worthiness evaluation: Set is_content_worthy to True only if the conversation:
   - Contains interesting insights, opinions, or discussions
   - Would be valuable/engaging for social media audiences
   - Has substance beyond casual small talk
   - Could generate meaningful engagement (likes, comments, shares)
   
   Set to False for:
   - Personal conversations (e.g., gym routines, personal questions)
   - Technical debugging or internal processes
   - Casual banter without insights
   - Sensitive or private topics"""),
        HumanMessage(
            content=json.dumps(state['messages'], indent=2)
        )
    ])
    # add a chunk_id field
    chunks = [{"chunk_id": i, **chunk}
              for i, chunk in enumerate(res['chunks'])]
    return {'chunks': chunks}


def prepare_jobs(state: GlobalState):
    """Create jobs from chunks and store in state."""
    jobs = []

    for chunk in state["chunks"]:
        # if chunks are not content worthy, don't create jobs for then
        if not chunk['is_content_worthy']:
            continue
        
        chunk_messages = [
            msg for msg in state['messages'] if msg['message_id'] in chunk['message_ids']]

        for platform in ("x", "linkedin"):
            job = {
                "chunk": chunk,
                "platform": platform,
                "chunk_messages": chunk_messages,
                "iteration": 0,
                "max_iterations": state['max_iterations_per_job'],
            }
            jobs.append(job)

    print(f"Final jobs count: {len(jobs)}")
    return {"jobs": jobs}


def continue_to_jobs(state: GlobalState):
    """Route each job to process_job node using Send."""
    return [Send("process_job", job) for job in state["jobs"]]


def generate_x_post(state: JobState) -> JobState:
    # support being passed the chunk and its messages separately
    if not state['chunk']['is_content_worthy']:
        return {'x_post': None}

    x_system_prompt = """You are a tech founder creating Twitter/X content from internal team conversations.

Your task: Transform the provided Slack conversation into engaging Twitter/X posts that share tactical insights and authentic founder perspectives.

OUTPUT STRUCTURE (you must provide both fields):
1. `hook`: A punchy, attention-grabbing first line (1-2 sentences max). This is the opener that makes people stop scrolling. Use questions, bold statements, or surprising insights.
2. `tweets`: A list of 1-3 tweets (strings) that follow the hook. These should form a cohesive thread with tactical insights and clear takeaways.

REQUIREMENTS:
- Generate 1-3 tweets maximum in the `tweets` list (use multiple only if the topic needs a thread)
- The `hook` must be strong and grab attention immediately
- Write in an authentic founder voice (conversational, insightful, not corporate)
- Include punchy, tactical insights that provide real value
- Each tweet should end with a clear takeaway that readers can act on
- Keep tweets concise and impactful (under 280 characters each)
- Use natural language, avoid jargon unless necessary
- Make it feel like a real founder sharing learnings, not marketing copy

TONE:
- Direct and honest
- Slightly casual but professional
- Thoughtful and insightful
- Engaging and relatable

STRUCTURE EXAMPLE:
hook: "Just tested the new STT models. ElevenLabs should be worried."
tweets: [
  "Lower latency + better accent handling = game changer for voice apps.",
  "Accuracy > fancy features. Every time."
]

Now transform the conversation below into Twitter/X posts following these guidelines. Provide both the hook and the tweets list."""

    # if evaluation failed previously add the reasoning
    reasoning = ""
    if not state.get('evaluation_passed', True) and state.get('evaluation') is not None:
        reasoning = f"""
Previously Generated Content
{json.dumps(state['x_post'])}

Previous Evaluation Scores:
External Value: {state['evaluation']['external_value_score']}/10
Authenticity: {state['evaluation']['authenticity_score']}/10
Clarity: {state['evaluation']['clarity_score']}/10
Engagement Potential: {state['evaluation']['engagement_score']}/10 

Reasoning: {state['evaluation']['reasoning']}

"""
    x_system_prompt += reasoning
    x_human_prompt = f"""Topic: {state['chunk']['topic']}
Summary: {state['chunk']['summary']}         

Original conversation messages:
{json.dumps(state['chunk_messages'], indent=2)}"""
    x_post = x_generation_llm.invoke([
        SystemMessage(content=x_system_prompt),
        HumanMessage(content=x_human_prompt)
    ])

    return x_post


def generate_linkedin_post(state: JobState) -> JobState:
    # support being passed the chunk and its messages separately
    if not state['chunk']['is_content_worthy']:
        return {'linkedin_post': None}

    linkedin_system_prompt = """You are a tech founder creating LinkedIn content from internal team conversations.

Transform the Slack conversation into a professional LinkedIn post (150-200 words) with storytelling tone.

REQUIREMENTS:
- 150-200 words for content field
- Professional storytelling tone
- Strong hook that captures attention
- Practical insights/lessons readers can apply
- Clear CTA at the end
- Authentic founder voice (professional but relatable)

TONE: Professional, conversational, thoughtful, engaging, authentic."""

    # if evaluation failed previously add the reasoning
    reasoning = ""
    if not state.get('evaluation_passed', True) and state.get('evaluation') is not None:
        reasoning = f"""
Previously Generated Content
{json.dumps(state['linkedin_post'])}

Previous Evaluation Scores:
External Value: {state['evaluation']['external_value_score']}/10
Authenticity: {state['evaluation']['authenticity_score']}/10
Clarity: {state['evaluation']['clarity_score']}/10
Engagement Potential: {state['evaluation']['engagement_score']}/10 

Reasoning: {state['evaluation']['reasoning']}

"""
    linkedin_system_prompt += reasoning

    linkedin_human_prompt = f"""Topic: {state['chunk']['topic']}
Summary: {state['chunk']['summary']}

Original conversation messages:
{json.dumps(state['chunk_messages'], indent=2)}"""

    linkedin_post = linkedin_generation_llm.invoke([
        SystemMessage(content=linkedin_system_prompt),
        HumanMessage(content=linkedin_human_prompt)
    ])

    return linkedin_post


def generate_post(state: JobState) -> JobState:
    if not state['chunk']['is_content_worthy']:
        return {}

    if state['platform'] == 'x':
        res = generate_x_post(state)
        return {'x_post': res, 'iteration': state['iteration'] + 1}
    elif state['platform'] == 'linkedin':
        res = generate_linkedin_post(state)
        return {'linkedin_post': res, 'iteration': state['iteration'] + 1}
    else:
        raise ValueError(f"Unknown platform: {state['platform']}")


def evaluate_post(state: JobState) -> JobState:
    # if no post was generated, skip evaluation
    if state['platform'] == 'x' and state.get('x_post') is None:
        return {'evaluation': None, 'evaluation_passed': True}
    if state['platform'] == 'linkedin' and state.get('linkedin_post') is None:
        return {'evaluation': None, 'evaluation_passed': True}

    platform = state['platform']

    # Base evaluation prompt
    base_prompt = """You are an expert social media content evaluator. Evaluate the provided post based on these criteria:

SCORING CRITERIA (0-10 scale for each):
1. External Value (0-10): Is this useful to non-insiders? Would someone outside the company/team find value?
2. Authenticity (0-10): Does this feel genuine and authentic, or corporate/marketing-like?
3. Clarity (0-10): Is the message clear and easy to understand?
4. Engagement Potential (0-10): Would people want to interact (like, comment, share)?


Provide detailed reasoning explaining each score."""

    # Platform-specific additions
    if platform == 'x':
        platform_specific = """
PLATFORM: Twitter/X

SPECIFIC CHECKLIST:
- Punchy, tactical insights: Does it provide actionable, tactical value?
- Strong hook in first tweet: Does the hook grab attention immediately?
- Authentic founder voice: Does it sound like a real founder, not corporate PR?
- Clear takeaway: Is there a clear, actionable lesson or insight?

Evaluate how well the post meets these Twitter/X-specific requirements."""

        # Format post content for evaluation
        hook = state['x_post'].get('hook', '')
        tweets = state['x_post'].get('tweets', [])
        post_content = f"Hook: {hook}\n\nTweets:\n" + \
            "\n".join([f"{i+1}. {tweet}" for i, tweet in enumerate(tweets)])

    elif platform == 'linkedin':
        platform_specific = """
PLATFORM: LinkedIn

SPECIFIC CHECKLIST:
- Professional storytelling tone: Is it polished but authentic?
- Starts with a hook: Does it begin with an attention-grabbing opening?
- Practical insight/lesson: Does it provide actionable insights readers can apply?
- Clear call-to-action: Is there a clear CTA that encourages engagement?

Evaluate how well the post meets these LinkedIn-specific requirements."""

        # Format post content for evaluation
        hook = state['linkedin_post'].get('hook', '')
        content = state['linkedin_post'].get('content', '')
        cta = state['linkedin_post'].get('cta', '')
        post_content = f"Hook: {hook}\n\nContent:\n{content}\n\nCTA: {cta}"
    else:
        raise ValueError(
            f"Unknown platform: {state['platform']}. Use 'x' or 'linkedin'")

    # Combine prompts
    full_prompt = base_prompt + "\n\n" + platform_specific

    # Create evaluation message
    evaluation_message = f"""Post to evaluate:

{post_content}

Evaluate this post according to the criteria above."""

    # Invoke evaluation LLM
    result = evaluation_llm.invoke([
        SystemMessage(content=full_prompt),
        HumanMessage(content=evaluation_message)
    ])

    total_score = (
        result['external_value_score'] +
        result['authenticity_score'] +
        result['clarity_score'] +
        result['engagement_score']
    )
    return {'evaluation': result, 'evaluation_passed': True if total_score >= 30 else False}


def re_try_generation(state: JobState) -> Literal['end', 'retry']:
    if state['evaluation_passed'] or state['iteration'] >= state['max_iterations']:
        return 'end'
    return 'retry'

# ============================================================================
# GRAPH CONSTRUCTION
# ============================================================================


# Subgraph for processing individual jobs
job_graph = StateGraph(JobState)

job_graph.add_node("generate_post", generate_post)
job_graph.add_node("evaluate_post", evaluate_post)

job_graph.add_edge(START, "generate_post")
job_graph.add_edge("generate_post", "evaluate_post")
job_graph.add_conditional_edges("evaluate_post", re_try_generation, {
                                "end": END, "retry": "generate_post"})

job_subgraph = job_graph.compile()

# Main graph


def process_job(job: JobState):
    """Wrapper function to process a single job through the job subgraph and return result."""
    print(f"\n=== process_job called for {job['chunk']['topic']} ===")
    result = job_subgraph.invoke(job)
    print(f"=== process_job completed ===\n")
    # Return as list to be added to jobs_result via reducer
    return {'jobs_result': [result]}


graph = StateGraph(GlobalState)
graph.add_node("chunk_messages", chunk_messages)
graph.add_node("prepare_jobs", prepare_jobs)
graph.add_node("process_job", process_job)

graph.add_edge(START, "chunk_messages")
graph.add_edge("chunk_messages", "prepare_jobs")
# Use add_conditional_edges with continue_to_jobs routing function for Send API
graph.add_conditional_edges("prepare_jobs", continue_to_jobs, ["process_job"])
graph.add_edge("process_job", END)

final_graph = graph.compile()
