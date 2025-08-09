import os
import json
from datetime import date
import streamlit as st
import openai

# ---------- Daily usage tracking ----------
USAGE_FILE = "daily_usage.json"

def load_daily_usage():
    if os.path.exists(USAGE_FILE):
        with open(USAGE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_daily_usage(data):
    with open(USAGE_FILE, "w") as f:
        json.dump(data, f)

daily_usage = load_daily_usage()
today_str = date.today().isoformat()
if today_str not in daily_usage:
    daily_usage[today_str] = 0.0

# ---------- Page config ----------
st.set_page_config(page_title="Chatbot", page_icon="💬", layout="centered")
st.title("💬 ChatGPT Chatbot")

# ---------- Pricing ----------
PRICING = {
    "gpt-5":              {"input": 0.02,   "output": 0.06},    # placeholder pricing
    "gpt-4o":             {"input": 0.0005, "output": 0.0015},
    "gpt-4-turbo":        {"input": 0.01,   "output": 0.03},
    "gpt-4-1106-preview": {"input": 0.01,   "output": 0.03},
    "gpt-3.5-turbo":      {"input": 0.0005, "output": 0.0015},
}
def estimate_cost(model: str, in_tokens: int, out_tokens: int) -> float:
    p = PRICING.get(model, {"input": 0.0, "output": 0.0})
    return round((in_tokens / 1000) * p["input"] + (out_tokens / 1000) * p["output"], 5)

# ---------- Sidebar ----------
with st.sidebar:
    MODEL_OPTIONS = {
        "GPT-5":            "gpt-5",
        "GPT-4o (default)": "gpt-4o",
        "GPT-4 Turbo":      "gpt-4-turbo",
        "GPT-4.1":          "gpt-4-1106-preview",
        "GPT-3.5 Turbo":    "gpt-3.5-turbo",
    }
    model_label = st.selectbox("Model", list(MODEL_OPTIONS.keys()), index=1)
    model = MODEL_OPTIONS[model_label]

    system_prompt = st.text_area(
        "System instructions (optional)",
        placeholder="E.g., You are a helpful assistant that answers concisely.",
        height=80
    )

    if st.session_state.get("history"):
        history_text = "\n\n".join(
            [f"You: {m['content']}" if m["role"] == "user" else f"AI: {m['content']}"
             for m in st.session_state["history"]]
        )
        st.download_button("⬇️ Download Chat History", data=history_text, file_name="chat_history.txt")

    def reset_chat():
        st.session_state["history"] = []
        st.session_state["token_total"] = 0
        st.session_state["cost_total"] = 0.0
    st.button("🔁 Reset Chat", on_click=reset_chat)

# ---------- Session state ----------
if "history" not in st.session_state:
    st.session_state["history"] = []
if "token_total" not in st.session_state:
    st.session_state["token_total"] = 0
if "cost_total" not in st.session_state:
    st.session_state["cost_total"] = 0.0

# ---------- File upload ----------
file_context = ""
uploaded = st.file_uploader("Upload file (TXT, PY, CS, C, CPP)", type=["txt", "py", "cs", "c", "cpp"])
if uploaded:
    try:
        raw = uploaded.read().decode("utf-8", errors="ignore")
        max_chars = 30_000
        if len(raw) > max_chars:
            clipped = raw[:max_chars]
            file_context = clipped + f"\n\n[NOTE: File clipped from {len(raw)} to {max_chars} characters]"
        else:
            file_context = raw
    except Exception:
        file_context = ""

# ---------- OpenAI client ----------
client = openai.OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", "")))

# ---------- Render chat history ----------
for msg in st.session_state["history"]:
    if msg["role"] == "user":
        st.chat_message("user").markdown(msg["content"])
    else:
        st.chat_message("assistant").markdown(msg["content"])
        if "total_tokens" in msg:
            small = (
                f"Tokens – in: {msg.get('input_tokens','?')}, "
                f"out: {msg.get('output_tokens','?')}, "
                f"total: {msg.get('total_tokens','?')}"
            )
            cost = estimate_cost(msg.get("model",""), msg.get("input_tokens",0), msg.get("output_tokens",0))
            st.markdown(f"<span style='color:gray;font-size:12px'>{small} · est. cost: ${cost}</span>", unsafe_allow_html=True)

# ---------- User input ----------
prompt = st.chat_input("Type your message… (Shift+Enter for a new line)")
if prompt:
    st.session_state["history"].append({"role": "user", "content": prompt, "model": model})
    st.chat_message("user").markdown(prompt)

    messages = []
    if system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt.strip()})
    if file_context:
        messages.append({"role": "system", "content": f"Use this uploaded file as context:\n{file_context}"})
    messages.extend({"role": m["role"], "content": m["content"]} for m in st.session_state["history"])

    try:
        with st.spinner("Thinking…"):
            resp = client.chat.completions.create(model=model, messages=messages)
        reply = resp.choices[0].message.content
        usage = resp.usage

        cost_this_message = estimate_cost(model, usage.prompt_tokens, usage.completion_tokens)

        st.session_state["history"].append({
            "role": "assistant",
            "content": reply,
            "model": model,
            "input_tokens": usage.prompt_tokens,
            "output_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens
        })
        st.session_state["token_total"] += usage.total_tokens
        st.session_state["cost_total"] += cost_this_message

        # Update daily usage
        daily_usage[today_str] += cost_this_message
        save_daily_usage(daily_usage)

        st.chat_message("assistant").markdown(reply)
    except Exception as e:
        st.error(f"OpenAI error: {e}")

# ---------- Totals ----------
st.markdown(
    f"---\n**Session tokens:** {st.session_state['token_total']} · "
    f"**Est. session cost:** ${round(st.session_state['cost_total'], 5)} · "
    f"**Today’s total cost:** ${round(daily_usage[today_str], 5)}"
)