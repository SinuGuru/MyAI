import os
import json
import requests
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

# ---------- OpenAI API Key ----------
OPENAI_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
client = openai.OpenAI(api_key=OPENAI_KEY)

# ---------- Remaining monthly allowance ----------
@st.cache_data(ttl=120)
def fetch_openai_remaining(api_key: str):
    try:
        today = date.today()
        start_date = today.replace(day=1).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")

        # Get subscription details
        sub_url = "https://api.openai.com/v1/dashboard/billing/subscription"
        headers = {"Authorization": f"Bearer {api_key}"}
        sub_resp = requests.get(sub_url, headers=headers, timeout=10)
        if sub_resp.status_code != 200:
            return None
        hard_limit = sub_resp.json().get("hard_limit_usd", 0.0)

        # Get usage this month
        usage_url = f"https://api.openai.com/v1/dashboard/billing/usage?start_date={start_date}&end_date={end_date}"
        usage_resp = requests.get(usage_url, headers=headers, timeout=10)
        if usage_resp.status_code != 200:
            return None
        total_usage = usage_resp.json().get("total_usage", 0) / 100  # cents to USD

        return max(hard_limit - total_usage, 0.0)
    except Exception:
        return None

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

    cols = st.columns((1, 1))
    with cols[0]:
        refresh_balance = st.button("🔄 Refresh balance")
    with cols[1]:
        show_balance = st.checkbox("Show balance", value=True)

    balance_value = fetch_openai_remaining(OPENAI_KEY) if show_balance else None
    if show_balance:
        if balance_value is None:
            st.info("Balance: unavailable (check API key or billing).")
        else:
            st.success(f"Remaining monthly allowance: **${balance_value:.2f}**")

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

# ---------- File upload (auto-load into chat) ----------
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

        # Add system message with file content
        st.session_state["history"].append({
            "role": "system",
            "content": f"File '{uploaded.name}' loaded. Content:\n\n{file_context}"
        })
        # Add confirmation message
        st.session_state["history"].append({
            "role": "assistant",
            "content": f"✅ I have loaded the file **{uploaded.name}** into our conversation context."
        })
    except Exception:
        st.error("❌ Could not read the uploaded file.")

# ---------- Render chat history ----------
for msg in st.session_state["history"]:
    if msg["role"] == "user":
        st.chat_message("user").markdown(msg["content"])
    elif msg["role"] == "assistant":
        st.chat_message("assistant").markdown(msg["content"])
    # Don't display raw system messages

# ---------- User input ----------
prompt = st.chat_input("Type your message… (Shift+Enter for a new line)")
if prompt:
    st.session_state["history"].append({"role": "user", "content": prompt, "model": model})
    st.chat_message("user").markdown(prompt)

    # Build messages (include system messages and user/assistant turns)
    messages = []
    if system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt.strip()})
    messages.extend({"role": m["role"], "content": m["content"]} for m in st.session_state["history"] if m["role"] != "assistant" or m.get("model"))

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

        daily_usage[today_str] += cost_this_message
        save_daily_usage(daily_usage)

        st.chat_message("assistant").markdown(reply)
    except Exception as e:
        st.error(f"OpenAI error: {e}")

# ---------- Totals ----------
totals_line = (
    f"**Session tokens:** {st.session_state['token_total']} · "
    f"**Est. session cost:** ${round(st.session_state['cost_total'], 5)} · "
    f"**Today’s total cost:** ${round(daily_usage[today_str], 5)}"
)
if show_balance:
    if balance_value is None:
        totals_line += " · **Balance:** n/a"
    else:
        totals_line += f" · **Balance:** ${balance_value:.2f}"
st.markdown("---\n" + totals_line)