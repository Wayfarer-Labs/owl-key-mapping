from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
import glob

from owl_keys.controls.utils import decimal_to_ascii
from .prompts import PROMPT_1

load_dotenv()

class ChatWrapper:
    def __init__(self, model = "gemini-2.5-flash-lite"):
        self.client = genai.Client()
        self.model = model

    def chat(self, video_dir_path, action_id, action_type = "KEYBOARD", exe_name = None):
        video_files = glob.glob(os.path.join(video_dir_path, "*.mp4"))
        video_bytes_list = [open(video_file, "rb").read() for video_file in video_files]

        parts = [types.Part(text=PROMPT_1)]
        for video_bytes in video_bytes_list:
            parts.append(types.Part(inline_data=types.Blob(data=video_bytes, mime_type='video/mp4')))

        message = f"Action Type: {action_type} | Action ID: {action_id} | ASCII: {decimal_to_ascii(action_id)} | Please classify the action."
        if exe_name is not None:
            message += f" | Game Executable Name: {exe_name}"
        parts.append(types.Part(text=message))

        response = self.client.models.generate_content(
            model=self.model,
            contents=types.Content(
                parts=parts
            )
        )
        return response.candidates[0].content.parts[0].text


if __name__ == "__main__":
    chat = ChatWrapper()
    print(chat.chat("output", 32, "KEYBOARD"))