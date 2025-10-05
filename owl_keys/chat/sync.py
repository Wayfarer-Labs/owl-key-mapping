from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

class ChatWrapper:
    def __init__(self, model = "gemini-2.5-flash-lite"):
        self.client = OpenAI(
            api_key=os.getenv("GEMINI_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        self.model = model

    def chat(self, message):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": message}]
        )
        return response.choices[0].message.content


if __name__ == "__main__":
    chat = ChatWrapper()
    print(chat.chat("Hello, how are you?"))