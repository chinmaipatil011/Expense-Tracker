
import os
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from tools import TOOL_LIST, TOOL_MAP
from config import GEMINI_MODEL, OLLAMA_MODEL, MAX_AGENT_STEPS

load_dotenv()
MAX_STEPS = int(os.getenv("MAX_AGENT_STEPS", str(MAX_AGENT_STEPS)))

SYSTEM = """You are a concise personal expense assistant.

Tools:
- add_expense: saves a new expense.
- get_expense_summary: retrieves expense totals by category.
- calculate: performs safe arithmetic.

Rules:
1. Use add_expense for every expense write. Never claim it was saved unless it succeeds.
2. Use get_expense_summary for spending questions. Use its result as the source of truth.
3. If a user asks to add an expense and then summarize spending, add it first, then summarize.
4. Never invent amounts or categories.
5. If a tool fails, explain that the action could not be completed.
6. Ask for clarification only when required information is missing.
7. Keep responses concise."""

def get_llm():
    provider = os.getenv("PROVIDER", "gemini").strip().lower()

    if provider == "gemini":
        if not os.getenv("GOOGLE_API_KEY"):
            raise RuntimeError("GOOGLE_API_KEY is missing from .env")
        model = os.getenv("GEMINI_MODEL", GEMINI_MODEL)
        return ChatGoogleGenerativeAI(model=model, temperature=0)

    if provider == "ollama":
        model = os.getenv("OLLAMA_MODEL", OLLAMA_MODEL)
        return ChatOllama(model=model, temperature=0)

    raise RuntimeError("PROVIDER must be 'gemini' or 'ollama'")

def asks_for_summary(message):
    text = message.lower()
    terms = ("summary", "total", "how much have i spent",
             "spending", "spent so far", "overall")
    return any(term in text for term in terms)

def run_agent(user_message):
    llm = get_llm().bind_tools(TOOL_LIST)
    messages = [
        SystemMessage(content=SYSTEM),
        HumanMessage(content=user_message)
    ]
    used = []
    added_successfully = False
    summary_done = False
    combined_request = asks_for_summary(user_message)

    for step in range(MAX_STEPS):
        ai = llm.invoke(messages)
        messages.append(ai)
        calls = getattr(ai, "tool_calls", []) or []

        if not calls:
            content = ai.content
            if isinstance(content, list):
                content = "".join(
                    str(part.get("text", ""))
                    for part in content if isinstance(part, dict)
                )
            return str(content), used

        for call in calls:
            name = call.get("name")
            call_id = call.get("id", "")

            # Avoid repeating a summary if it was already retrieved.
            if name == "get_expense_summary" and summary_done:
                messages.append(ToolMessage(
                    content="Summary already retrieved. Use the previous result.",
                    tool_call_id=call_id
                ))
                continue

            if name not in TOOL_MAP:
                result = "Error: unknown tool."
                success = False
            else:
                try:
                    result = TOOL_MAP[name].invoke(call.get("args", {}))
                    success = not (
                        isinstance(result, str) and result.startswith("Tool error:")
                    )
                except Exception as exc:
                    result = f"Tool error: {exc}"
                    success = False

            used.append(name or "unknown")
            messages.append(ToolMessage(
                content=str(result),
                tool_call_id=call_id
            ))

            if name == "add_expense" and success:
                added_successfully = True
            if name == "get_expense_summary" and success:
                summary_done = True

        # Ensure combined requests retrieve the updated totals after a
        # successful write, even if the model doesn't request the summary.
        if combined_request and added_successfully and not summary_done:
            try:
                result = TOOL_MAP["get_expense_summary"].invoke({"days": 30})
                messages.append(ToolMessage(
                    content=str(result),
                    tool_call_id="forced_summary"
                ))
                used.append("get_expense_summary")
                summary_done = True
            except Exception as exc:
                messages.append(ToolMessage(
                    content=f"Tool error: {exc}",
                    tool_call_id="forced_summary"
                ))
                used.append("get_expense_summary")

    raise RuntimeError(
        f"Agent stopped after {MAX_STEPS} steps without a final answer."
    )
