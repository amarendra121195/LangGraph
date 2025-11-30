# image_gen.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI
import os
import re
import requests
import base64
from typing import Optional

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY in environment or .env")

client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(title="Chat + Image Generator (OpenAI)")

# allow local frontend (restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def wants_image(text: str) -> bool:
    if not text:
        return False
    txt = text.lower().strip()
    # direct commands
    if txt.startswith("image:") or txt.startswith("picture:") or txt.startswith("photo:"):
        return True
    # verbs + nouns pattern
    verb = r"\b(draw|create|generate|show|make|render)\b"
    noun = r"\b(image|picture|photo|portrait|illustration|render)\b"
    if re.search(verb, txt) and re.search(noun, txt):
        return True
    # short phrases
    short_triggers = ["draw ", "create ", "generate ", "image of", "picture of", "photo of"]
    return any(k in txt for k in short_triggers)


class ChatRequest(BaseModel):
    message: str
    history: list  # list of {"is_user": bool, "text": str} - frontend supplies this


@app.get("/health")
def health():
    return {"status": "ok"}


def try_generate_image(prompt: str) -> dict:
    """
    Try several image models in order. Return dict with either:
      {"success": True, "image_base64": "..."}
    or
      {"success": False, "error": "message"}
    """
    # Models to try, in order. You can change order.
    image_models = ["dall-e-3", "gpt-image-1", "gpt-image-1-mini"]
    last_exception = None

    for model_name in image_models:
        try:
            # Use the client.images.generate call
            resp = client.images.generate(model=model_name, prompt=prompt, size="1024x1024")
            # Two possible response shapes:
            # - resp.data[0].b64_json (direct base64)
            # - resp.data[0].url (URL to image) — download and convert
            entry = resp.data[0]
            if getattr(entry, "b64_json", None):
                b64 = entry.b64_json
            elif getattr(entry, "url", None):
                # download url and encode
                url = entry.url
                r = requests.get(url, timeout=30)
                r.raise_for_status()
                b64 = base64.b64encode(r.content).decode()
            else:
                # unknown shape — convert repr to string to help debugging
                return {"success": False, "error": f"Image response missing b64_json/url from model {model_name}."}

            return {"success": True, "image_base64": b64, "model_used": model_name}
        except Exception as e:
            # remember last exception and try next model
            last_exception = e
            # if it's a permission/403, try next model — but record message
            continue

    return {"success": False, "error": f"All image model attempts failed. Last error: {last_exception}"}


@app.post("/chat")
def chat(req: ChatRequest):
    user_message = (req.message or "").strip()
    history = req.history or []

    # quick safety
    if not user_message:
        return {"type": "text", "response": "Please send a message."}

    # if user asked for image -> generate image + description
    if wants_image(user_message):
        img_result = try_generate_image(user_message)
        if not img_result["success"]:
            return {"type": "error", "message": img_result["error"]}

        image_b64 = img_result["image_base64"]
        model_used = img_result.get("model_used")

        # create a short description via chat LLM
        try:
            # Build a small context from history (last few messages) to keep description relevant
            chat_messages = [{"role": "system", "content": "You write short 2-4 sentence image descriptions."}]
            # include last up to 6 messages for context
            for h in history[-6:]:
                role = "user" if h.get("is_user") else "assistant"
                chat_messages.append({"role": role, "content": h.get("text", "")})
            chat_messages.append({"role": "user", "content": f"Write a short (2-4 sentence) description for this image: {user_message}"})

            desc_resp = client.chat.completions.create(model="gpt-4.1-mini", messages=chat_messages, temperature=0.2)
            description = desc_resp.choices[0].message.content
        except Exception as e:
            description = f"(Could not generate description: {e})"

        return {
            "type": "image",
            "image_base64": image_b64,
            "description": description,
            "model_used": model_used,
        }

    # Normal chat flow (text)
    # Build messages for chat completion from system + history + new user
    messages = [{"role": "system", "content": "You are a helpful assistant."}]
    for h in history[-20:]:  # include last 20 messages max
        role = "user" if h.get("is_user") else "assistant"
        messages.append({"role": role, "content": h.get("text", "")})
    messages.append({"role": "user", "content": user_message})

    try:
        resp = client.chat.completions.create(model="gpt-4.1-mini", messages=messages, temperature=0.2)
        assistant_reply = resp.choices[0].message.content
    except Exception as e:
        assistant_reply = f"Sorry — chat generation failed: {e}"

    return {"type": "text", "response": assistant_reply}
