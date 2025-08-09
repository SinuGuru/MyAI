import streamlit as st
import openai

st.title("💬 ChatGPT Chatbot")

# --- Sidebar: Model Selector + Download ---
with st.sidebar:
    MODEL_OPTIONS = {
        "GPT-3.5 Turbo": "gpt-3.5-turbo",
        "GPT-4o": "gpt-4o",
        "GPT-4 Turbo": "gpt-4-turbo",
        "GPT-4.1": "gpt-4-1106-preview"
    }
    model_label = st.selectbox("Choose model", list(MODEL_OPTIONS.keys()), index=1)
    model = MODEL_OPTIONS[model_label]

    if st.session_state.get("history"):
        history_text = "\n\n".join(
            [f"You: {m['content']}" if m["role"] == "user" else f"AI: {m['content']}" for m in st.session_state["history"]]
        )
        st.download_button("⬇️ Download Chat History", data=history_text, file_name="chat_history.txt")

# --- Pricing ---
PRICING = {
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "gpt-4o": {"input": 0.0005, "output": 0.0015},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4-1106-preview": {"input": 0.01, "output": 0.03}
}
def estimate_cost(model, input_tokens, output_tokens):
    p = PRICING.get(model, {"input": 0, "output": 0})
    return round((input_tokens / 1000) * p["input"] + (output_tokens / 1000) * p["output"], 5)

# --- Init session ---
if "history" not in st.session_state:
    st.session_state["history"] = []
if "token_total" not in st.session_state:
    st.session_state["token_total"] = 0
# Rotating key to clear input safely (2025-proof)
if "input_key" not in st.session_state:
    st.session_state["input_key"] = 0

# --- File Upload (code/text) ---
file_content = ""
uploaded_file = st.file_uploader("Upload file (TXT, PY, CS, C, CPP)", type=["txt", "py", "cs", "c", "cpp"])
if uploaded_file:
    try:
        file_content = uploaded_file.read().decode("utf-8", errors="ignore")
    except Exception:
        file_content = ""

# --- Show chat history ---
for entry in st.session_state["history"]:
    if entry["role"] == "user":
        st.markdown(f"**You:** {entry['content']}")
    else:
        tokens_info = f"Input: {entry.get('input_tokens', '?')}, Output: {entry.get('output_tokens', '?')}, Total: {entry.get('total_tokens', '?')}"
        cost = estimate_cost(entry.get("model", ""), entry.get("input_tokens", 0), entry.get("output_tokens", 0))
        st.markdown(
            f"**AI ({entry['model']}):** {entry['content']}\n"
            f"<span style='color:gray;font-size:small;'>Tokens – {tokens_info}<br>Estimated Cost: ${cost}</span>",
            unsafe_allow_html=True
        )
st.markdown(f"---\n**Total Tokens Used:** {st.session_state['token_total']}")

# --- Reset Chat ---
def reset_chat():
    st.session_state["history"] = []
    st.session_state["token_total"] = 0
    st.session_state["input_key"] += 1  # also clears the box on next render
st.button("🔁 Reset Chat", on_click=reset_chat)

# --- Multiline message box at the bottom (clears after send) ---
msg = st.text_area(
    "Message",
    key=f"user_msg_{st.session_state['input_key']}",
    height=110,
    placeholder="Type your message... (Shift+Enter for new line)",
)

send = st.button("Send")

# --- OpenAI call ---
if send and msg.strip():
    st.session_state["history"].append({"role": "user", "content": msg, "model": model})
    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    def chat_with_openai(prompt, chat_history, model):
        messages = [{"role": e["role"], "content": e["content"]} for e in chat_history]
        if file_content:
            messages.insert(0, {"role": "system", "content": f"Use this uploaded file as context:\n{file_content}"})
        messages.append({"role": "user", "content": prompt})
        resp = client.chat.completions.create(model=model, messages=messages)
        return resp.choices[0].message.content, resp.usage

    reply, usage = chat_with_openai(msg, st.session_state["history"], model)
    st.session_state["history"].append({
        "role": "assistant",
        "content": reply,
        "model": model,
        "input_tokens": usage.prompt_tokens,
        "output_tokens": usage.completion_tokens,
        "total_tokens": usage.total_tokens
    })
    st.session_state["token_total"] += usage.total_tokens

    # Clear the textarea safely by rotating the key
    st.session_state["input_key"] += 1