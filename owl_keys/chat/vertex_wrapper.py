from openai import OpenAI
from google.auth.transport.requests import Request
from dotenv import load_dotenv
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from google.oauth2 import service_account
import os
import base64
import glob

from owl_keys.controls.utils import decimal_to_ascii
from .prompts import PROMPT_1

load_dotenv()


def _is_retryable_exception(exception):
    """Check if an exception should trigger a retry."""
    # Add your retry logic here - e.g., for rate limits, timeouts, etc.
    if isinstance(exception, Exception):
        error_str = str(exception).lower()
        return any(keyword in error_str for keyword in ['rate limit', 'timeout', 'quota', 'unavailable'])
    return False


class VertexChatWrapper:
    def __init__(self, model="gemini-2.0-flash-exp", project_id='openworld-main', location="us-central1"):
        self.model = model
        self.project_id = project_id
        self.location = location
        self.token_expiry = datetime.now() + timedelta(hours=1)

        # Define the necessary scope to access the Vertex AI API
        scopes = ['https://www.googleapis.com/auth/cloud-platform']
        
        # Get the service account key path from the environment
        key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not key_path:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set.")

        # --- CORRECTED AUTHENTICATION ---
        # Create credentials that generate ACCESS TOKENS using the specified scopes.
        # This is the type of credential the API is asking for.
        self.credentials = service_account.Credentials.from_service_account_file(
            key_path,
            scopes=scopes
        )
        
        self.client = None
        self._refresh_client()
    
    def _refresh_client(self):
        """Refresh the ID token and recreate the OpenAI client."""
        # Use a request object to refresh the ID token
        request = Request()
        self.credentials.refresh(request)

        
        self.client = OpenAI(
            # --- CORRECTED LINE ---
            # Added /endpoints/openapi to the end of the URL
            base_url=f"https://{self.location}-aiplatform.googleapis.com/v1beta1/projects/{self.project_id}/locations/{self.location}/endpoints/openapi",
            # Use the refreshed ID token as the API key
            api_key=self.credentials.token
        )


    # --- ADDED A SIMPLE CHAT METHOD FOR THE EXAMPLE ---
    def chat_completion(self, model: str, messages: list):
        """Handle text-based chat completions."""
        # Refresh is handled by the OpenAI client library implicitly now
        # by creating a new client if needed, but we can do it explicitly
        self._refresh_client()
        
        return self.client.chat.completions.create(
            model=model,
            messages=messages
        )

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        retry=retry_if_exception(_is_retryable_exception),
    )
    def responses_with_video(self, model: str, prompt: str, mp4_bytes: bytes):
        """
        Send prompt + video to Vertex's OpenAI-compatible API.
        This version correctly uses the chat.completions endpoint for multimodal input.
        """
        # Refresh client/token if necessary
        if datetime.now() >= self.token_expiry:
            self._refresh_client()

        # Encode the video bytes into a base64 string
        b64_video = base64.b64encode(mp4_bytes).decode("ascii")

        # Use the standard chat.completions endpoint, which supports multimodal content
        return self.client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        # Part 1: The text prompt
                        {"type": "text", "text": prompt},
                        # Part 2: The video data, formatted correctly for this endpoint
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:video/mp4;base64,{b64_video}"
                            }
                        }
                    ],
                }
            ],
            # This keyword is supported by the chat.completions.create method
            response_format={"type": "json_object"},
        )

    def chat(self, video_dir_path, action_id, action_type="KEYBOARD", exe_name=None):
        """
        Main chat method compatible with ChatWrapper interface.
        Processes multiple videos from a directory and returns the LLM response.
        """
        video_files = glob.glob(os.path.join(video_dir_path, "*.mp4"))
        
        if not video_files:
            raise ValueError(f"No video files found in {video_dir_path}")
        
        # Build the prompt
        message_parts = [PROMPT_1]
        
        # Add context message
        context_msg = f"\nAction Type: {action_type} | Action ID: {action_id} | ASCII: {decimal_to_ascii(action_id)} | Please classify the action."
        if exe_name is not None:
            context_msg += f" | Game Executable Name: {exe_name}"
        message_parts.append(context_msg)
        
        full_prompt = "\n".join(message_parts)
        
        # For now, process the first video (can be extended to handle multiple videos)
        # Vertex API with OpenAI compatibility might have limitations on multiple videos
        with open(video_files[0], "rb") as f:
            video_bytes = f.read()
        
        response = self.responses_with_video(self.model, full_prompt, video_bytes)
        
        # Extract the text response from the OpenAI-style response
        return response.choices[0].message.content