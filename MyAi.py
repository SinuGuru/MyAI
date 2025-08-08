import streamlit as st
import openai
from io import StringIO

# --- Session Theme Handling ---
if "theme" not in st.session_state:
    st.session_state["theme"] = "dark"

theme = st.sidebar.radio("Theme", ["🌙 Dark", "☀️ Light"], index=0 if st.session_state["theme"] == "dark" else 1)
st.session_state["theme"] = "light" if theme == "☀️ Light" else "dark"

# --- Apply Theme Styles ---
if st.session_state["theme"] == "dark":
    st.markdown("""
    <style>
    body { background-color: #0E1117; color: white; }
    .stTextInput > div > div > input { background-color: #1C1F26; color: white; }
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
    body { background-color: #FFFFFF; color: black; }
    .stTextInput > div > div > input { background-color: #f0f2f6; color: black; }
    </style>
    """, unsafe_allow_html=True)

# --- Pricing Table ---
PRICING = {
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "gpt-4o": {"input": 0.0005, "output": 0.0015},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4-1106-preview": {"input": 0.01, "output": 0.03}
}

def estimate_cost(model, input_tokens, output_tokens):
    p = PRICING.get(model, {"input": 0, "output": 0})
    return round((input_tokens / 1000) * p["input"] + (output_tokens / 1000) * p["output"], 5)

# --- Sidebar ---
MODEL_OPTIONS = {
    "GPT-3.5 Turbo": "gpt-3.5-turbo",
    "GPT-4o": "gpt-4o",
    "GPT-4 Turbo": "gpt-4-turbo",
    "GPT-4.1": "gpt-4-1106-preview"
}
model_label = st.sidebar.selectbox("Choose model", list(MODEL_OPTIONS.keys()), index=1)
model = MODEL_OPTIONS[model_label]

# Download button
if st.session_state.get("history"):
    history_text = "\n\n".join([
        f"You: {msg['content']}" if msg["role"] == "user" else f"AI: {msg['content']}"
        for msg in st.session_state["history"]
    ])
    st.sidebar.download_button("⬇️ Download Chat History", data=history_text, file_name="chat_history.txt")

# --- Initialization ---
if "history" not in st.session_state:
    st.session_state["history"] = []
if "token_total" not in st.session_state:
    st.session_state["token_total"] = 0

# --- OpenAI Client ---
client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- File Upload (code/text support) ---
file_content = ""
uploaded_file = st.file_uploader("Upload a file (TXT, Python, C#, C, C++)", type=["txt", "py", "cs", "c", "cpp"])
if uploaded_file:
    file_extension = uploaded_file.name.split('.')[-1]
    if file_extension in ["txt", "py", "cs", "c", "cpp"]:
        file_content = uploaded_file.read().decode("utf-8")

# --- Reset Button ---
if st.button("🔁 Reset Chat"):
    st.session_state["history"] = []
    st.session_state["token_total"] = 0
    st.experimental_rerun()

# --- Chat Input ---
user_input = st.text_input("You:", key="user_input")

def chat_with_openai(prompt, chat_history, model):
    messages = [{"role": entry["role"], "content": entry["content"]} for entry in chat_history]
    if file_content:
        messages.insert(0, {"role": "system", "content": f"Use this uploaded file as context:\n{file_content}"})
    messages.append({"role": "user", "content": prompt})
    response = client.chat.completions.create(model=model, messages=messages)
    return response.choices[0].message.content, response.usage

if st.button("Send") or user_input:
    if user_input:
        st.session_state["history"].append({"role": "user", "content": user_input, "model": model})
        response, usage = chat_with_openai(user_input, st.session_state["history"], model)
        st.session_state["history"].append({
            "role": "assistant",
            "content": response,
            "model": model,
            "input_tokens": usage.prompt_tokens,
            "output_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens
        })
        st.session_state["token_total"] += usage.total_tokens
        st.experimental_rerun()

# --- Chat History ---
for entry in st.session_state["history"]:
    if entry["role"] == "user":
        st.markdown(f"**You:** {entry['content']}")
    elif entry["role"] == "assistant":
        tokens_info = f"Input: {entry.get('input_tokens', '?')}, Output: {entry.get('output_tokens', '?')}, Total: {entry.get('total_tokens', '?')}"
        cost = estimate_cost(entry.get("model", ""), entry.get("input_tokens", 0), entry.get("output_tokens", 0))
        st.markdown(
            f"**AI ({entry['model']}):** {entry['content']}\n"
            f"<span style='color:gray;font-size:small;'>Tokens – {tokens_info}<br>Estimated Cost: ${cost}</span>",
            unsafe_allow_html=True
        )

st.markdown(f"---\n**Total Tokens Used:** {st.session_state['token_total']}")