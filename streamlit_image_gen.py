# streamlit_image_gen.py
import streamlit as st
import requests
import base64
from io import BytesIO

API_URL = "http://127.0.0.1:8000/chat"

st.set_page_config(page_title="Chat + Image Generator", layout="centered")

# Sidebar controls
st.sidebar.title("New chat")
if "chat" not in st.session_state:
    st.session_state.chat = []

if st.sidebar.button("🆕 Start New Session"):
    st.session_state.chat = []

# st.sidebar.markdown("Tip: Say 'create an image of a girl sitting in the park' or 'draw a girl'")

st.title("AI Chat + Image Generation")
# st.write("Chat naturally. If you ask for an image, it will be generated automatically and described.")

# Display chat history
def render_history():
    for msg in st.session_state.chat:
        if msg["type"] == "text":
            if msg.get("is_user"):
                with st.chat_message("user"):
                    st.write(msg["text"])
            else:
                with st.chat_message("assistant"):
                    st.write(msg["text"])
        elif msg["type"] == "image":
            with st.chat_message("assistant"):
                st.write(msg.get("description", ""))
                # display image from raw bytes using BytesIO
                st.image(BytesIO(msg["image_bytes"]), use_column_width=True)
                st.download_button(
                    "Download Image",
                    data=msg["image_bytes"],
                    file_name="generated_image.png",
                    mime="image/png"
                )

# initial render
render_history()

# Input
user_input = st.chat_input("Type a message")

if user_input:
    # Store user message in session
    st.session_state.chat.append({"is_user": True, "type": "text", "text": user_input})
    # Build payload and send
    payload = {"message": user_input, "history": st.session_state.chat}
    try:
        resp = requests.post(API_URL, json=payload, timeout=90)
        resp.raise_for_status()
    except Exception as e:
        st.session_state.chat.append({"is_user": False, "type": "text", "text": f"❌ Backend error: {e}"})
        st.rerun()
    data = resp.json()

    if data.get("type") == "text":
        st.session_state.chat.append({"is_user": False, "type": "text", "text": data.get("response", "")})
    elif data.get("type") == "image":
        b64 = data.get("image_base64")
        if b64:
            image_bytes = base64.b64decode(b64)
            st.session_state.chat.append({
                "is_user": False,
                "type": "image",
                "description": data.get("description", ""),
                "image_bytes": image_bytes
            })
        else:
            st.session_state.chat.append({"is_user": False, "type": "text", "text": "⚠️ Image returned but no data available."})
    elif data.get("type") == "error":
        st.session_state.chat.append({"is_user": False, "type": "text", "text": "⚠️ " + data.get("message", "")})
    else:
        st.session_state.chat.append({"is_user": False, "type": "text", "text": "⚠️ Unknown response type from server."})

    st.rerun()

