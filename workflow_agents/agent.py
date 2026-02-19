import os
import logging
import google.cloud.logging
import wikipedia

from callback_logging import log_query_to_model, log_model_response
from dotenv import load_dotenv

from google.adk import Agent
from google.adk.agents import SequentialAgent, LoopAgent, ParallelAgent
from google.adk.tools.tool_context import ToolContext
from google.adk.models import Gemini
from google.genai import types

cloud_logging_client = google.cloud.logging.Client()
cloud_logging_client.setup_logging()
load_dotenv()

model_name = os.getenv("MODEL")
RETRY_OPTIONS = types.HttpRetryOptions(initial_delay=1, attempts=6)

# TOOLS 

def wiki_research(query: str) -> str:
    """Search Wikipedia for a given query to find historical facts."""
    try:
        return wikipedia.summary(query, sentences=5)
    except Exception as e:
        return f"Error: {e}"

def exit_loop() -> str:
    """Call this tool ONLY when both positive and negative data are balanced and sufficient."""
    return "READY_FOR_VERDICT"

def set_state(tool_context: ToolContext, field: str, response: str) -> dict[str, str]:
    """Save or update data in the session state."""
    tool_context.state[field] = response
    logging.info(f"[State Updated: {field}]")
    return {"status": "success"}

def write_file(tool_context: ToolContext, filename: str, content: str) -> dict[str, str]:
    """Save the final verdict to a .txt file."""
    os.makedirs("verdicts", exist_ok=True)
    target_path = os.path.join("verdicts", filename)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(content)
    logging.info(f"[File Saved] {target_path}")
    return {"status": "success"}


# AGENTS

# The Investigation (Parallel): The Researchers 
# The Admirer
admirer = Agent(
    name="admirer",
    model=Gemini(model=model_name, retry_options=RETRY_OPTIONS),
    description="Finds positive achievements of a historical figure.",
    instruction="""
    Topic: { TOPIC? }
    You are the Admirer. Find positive aspects, achievements, and successes of the Topic.
    1. Use `wiki_research` tool. You MUST append keywords like 'achievements' or 'success' or else to the Topic to help your own research more.
    2. Use `set_state` tool to save your findings to the field 'pos_data'.
    3. List all the pros you could find.

    """,
    tools=[wiki_research, set_state],
)

# The Critic
critic = Agent(
    name="critic",
    model=Gemini(model=model_name, retry_options=RETRY_OPTIONS),
    description="Finds negative aspects and controversies of a historical figure.",
    instruction="""
    Topic: { TOPIC? }
    You are the Critic. Find negative aspects, controversies, and failures of the Topic.
    1. Use `wiki_research` tool. You MUST append keywords like 'controversy' or 'failures' or else to the Topic to help your own research more.
    2. Use `set_state` tool to save your findings to the field 'neg_data'.
    3. List all the cons you could find.
 
    """,
    tools=[wiki_research, set_state],
)

investigators = ParallelAgent(
    name="investigators",
    description="Runs Admirer and Critic at the same time.",
    sub_agents=[admirer, critic]
)

# Judge (Loop/AgentC)
judge = Agent(
    name="judge",
    model=Gemini(model=model_name, retry_options=RETRY_OPTIONS),
    description="Evaluates the evidence from Admirer and Critic.",
    instruction="""
    You are the Judge. Evaluate the evidence gathered:
    Positive Evidence: { pos_data? }
    Negative Evidence: { neg_data? }

    - If either side is lacking, unbalanced, or empty:
      Output an instruction on what the agents should look for with specifically keywords suggestion for the topic.

    - If the information is well-balanced and sufficient to write a neutral report:
      1. You MUST call the `exit_loop` tool.
      
    """,
    tools=[exit_loop],
    generate_content_config=types.GenerateContentConfig(temperature=0),
)

trial_court = LoopAgent(
    name="trial_court",
    description="Loops the investigation and judging process.",
    sub_agents=[investigators, judge],
    max_iterations=5
)

# Output
verdict_writer = Agent(
    name="verdict_writer",
    model=Gemini(model=model_name, retry_options=RETRY_OPTIONS),
    description="Writes the final neutral report and saves it.",
    instruction="""
    Topic: { TOPIC? }
    Positive: { pos_data? }
    Negative: { neg_data? }

    Write a comprehensive, neutral historical report comparing the pros and cons.
    The report should be written in 2 languages: 1. in English then Tranlate the paragraph before into 2.Thai.
    The report should be 3 well visualization seperate pros and cons clearly, no need to explain historically, Be IMPARTIAL and JUDGE this person or this events for short at the end of the report.
    Then, use the `write_file` tool to save this report. 
    For the filename, use the Topic name with no spaces (e.g., "ColdWar_verdict.txt").
    """,
    tools=[write_file],
)

# The Inquiry (Sequential/Root)
root_agent = Agent(
    name="root",
    model=Gemini(model=model_name, retry_options=RETRY_OPTIONS),
    description="Gets the topic from the user and starts the court.",
    instruction="""
    You are the Bailiff of the Historical Court.
    1. Ask the user for a historical figure or event to put on trial.
    2. When the user answers, use the `set_state` tool to save their answer to the field 'TOPIC'.
    3. Transfer to the sub_agent to begin the trial.
    """,
    tools=[set_state],
    sub_agents=[
        SequentialAgent(
            name="court_process",
            description="Runs the trial and verdict sequentially.",
            sub_agents=[trial_court, verdict_writer]
        )
    ]
)