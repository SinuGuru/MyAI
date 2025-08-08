# Streamlit ChatGPT Chatbot

A simple chatbot web app built with Streamlit and OpenAI, featuring:
- Model selection (GPT-3.5 Turbo, GPT-4o, GPT-4 Turbo, GPT-4.1)
- Token usage counter for each message and total session
- Ready for Streamlit Community Cloud or local use

## Setup

1. Download all files and unzip them to a folder.
2. Install requirements:

   ```
   pip install -r requirements.txt
   ```

3. Add your OpenAI API key as `OPENAI_API_KEY` in Streamlit Secrets or paste it directly in `app.py` for local runs.
4. Run:

   ```
   streamlit run app.py
   ```

## Deployment

- Deployable on [Streamlit Community Cloud](https://streamlit.io/cloud)