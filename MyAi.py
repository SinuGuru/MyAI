import streamlit as st
import openai

st.title("💬 ChatGPT Chatbot (Model Picker + Token Counter)")

client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

MODEL_OPTIONS = {
    "GPT-3.5 Turbo": "gpt-3.5-turbo",
    "GPT-4o": "gpt-4o",
    "GPT-4 Turbo": "gpt-4-turbo",
    "GPT-4.1": "gpt-4-1106-preview"
}

model_label = st.selectbox(
    "Choose which AI model to use:",
    list(MODEL_OPTIONS.keys())
)
model = MODEL_OPTIONS[model_label]

# Initialize session state
if "history" not in st.session_state:
    st.session_state["history"] = []
if "token_total" not in st.session_state:
    st.session_state["token_total"] = 0

user_input = st.text_input("You:", key="user_input")

def chat_with_openai(prompt, chat_history, model):
    messages = [{"role": entry["role"], "content": entry["content"]} for entry in chat_history]
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=model,
        messages=messages
    )
    answer = response.choices[0].message.content
    usage = response.usage
    return answer, usage

if st.button("Send") or user_input:
    if user_input:
        st.session_state["history"].append({
            "role": "user",
            "content": user_input,
            "model": model
        })
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
        st.experimental_rerun()  # Refresh the app to clear input

# Display chat history
for entry in st.session_state["history"]:
    if entry["role"] == "user":
        st.markdown(f"**You:** {entry['content']} _(Model: {MODEL_OPTIONS.get(entry.get('model', ''), '')})_")
    elif entry["role"] == "assistant":
        model_used = [k for k, v in MODEL_OPTIONS.items() if v == entry.get("model", "")]
        model_used = model_used[0] if model_used else entry.get("model", "")
        tokens_info = f"Input: {entry.get('input_tokens', '?')}, Output: {entry.get('output_tokens', '?')}, Total: {entry.get('total_tokens', '?')}"
        st.markdown(
            f"**ChatGPT ({model_used}):** {entry['content']}"
            f"<span style='color:gray;font-size:small;'>Tokens – {tokens_info}</span>",
            unsafe_allow_html=True
        )

st.markdown(f"---\n**Total Tokens Used in this session:** {st.session_state['token_total']}")