from PIL import Image
import torch
import base64
from io import BytesIO

def tensor_to_pil_sequence(frames, desired_frames = 5, desired_size = (256, 256)):
    # frames is [t,c,h,w] assumed mmap [0,255] rgb uint8

    # First get desired frames interspersed throughout video
    # Should include first and last frame
    skip = len(frames) // (desired_frames)
    target_frames = frames[::skip]
    target_frames = target_frames.permute(0, 2, 3, 1)

    # Convert to PIL images then resize
    target_frames = [Image.fromarray(frame.contiguous().numpy()) for frame in target_frames]
    target_frames = [frame.resize(desired_size) for frame in target_frames]
    return target_frames

def encode_to_b64(image):
    """
    Convert a PIL image or bytes-like object to a base64-encoded string.
    Returns the encoded string suitable for use in the API.
    """
    if isinstance(image, Image.Image):
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()
    elif isinstance(image, (bytes, bytearray)):
        image_bytes = image
    else:
        raise TypeError("image must be a PIL.Image or bytes")

    return base64.b64encode(image_bytes).decode("utf-8")

def multimodal_prompt(text, images):
    """
    Construct the content list for a multimodal message:
    - Starts with text
    - Follows with one item per image (base64-encoded)
    Each image item uses the 'image_url' type.
    """
    content = [{"type": "text", "text": text}]
    for img in images:
        b64 = encode_to_b64(img)
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"}
        })
    return content

if __name__ == "__main__":
    frames = torch.randint(0, 255, (100, 3, 256, 256)).to(torch.uint8)
    target_frames = tensor_to_pil_sequence(frames)
    print(len(target_frames))
    print(target_frames[0])
    print(target_frames[0].size)
    content = multimodal_prompt("What do you see in these images?", target_frames)
    
    from .sync import ChatWrapper
    chat = ChatWrapper()
    response = chat.chat(content)
    print(response)