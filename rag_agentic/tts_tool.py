from openai import OpenAI

client = OpenAI()

def generate_tts_audio(text: str, file_path: str = "assistant_output.mp3"):
    """
    Generates speech from text using OpenAI GPT-4o-Mini-TTS.
    Returns the path to the generated MP3 file.
    """

    response = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="alloy",
        input=text
    )

    with open(file_path, "wb") as f:
        f.write(response.read())

    return file_path
