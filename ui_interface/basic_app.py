import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.set_page_config(page_title="Chatbot App", layout="wide")

st.title("Chatbot")

# Sidebar controls
with st.sidebar:
    st.header("Model Settings")
    model = st.selectbox("OpenAI Model", ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"])
    max_tokens = st.slider("Max Tokens", 50, 1000, 300)
    temperature = st.slider("Temperature", 0.0, 1.0, 0.7)

# Initialize message history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Streamlit form to avoid session_state errors:
with st.form("chat_form", clear_on_submit=True):
    user_input = st.text_input("You:", "", key="input_area")
    send = st.form_submit_button("Send")

# Handle submission
if send and user_input.strip():
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Generate response using new OpenAI client format
    response = client.chat.completions.create(
        model=model,
        messages=st.session_state.messages,
        max_tokens=max_tokens,
        temperature=temperature
    )

    bot_message = response.choices[0].message.content

    # Add assistant message
    st.session_state.messages.append({"role": "assistant", "content": bot_message})

# Display chat history
st.write("### Conversation")
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f"**🧑 You:** {msg['content']}")
    else:
        st.markdown(f"**🤖 Bot:** {msg['content']}")
