import os
import sys
import pandas as pd
import shutil
import random
import json
from typing import Dict, Optional

# Path setup for imports
if os.path.basename(sys.path[0]) == os.path.basename(os.path.dirname(__file__)):
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from owl_keys.controls.extract_button_inputs import extract_button_inputs, get_timestamps_around
from owl_keys.visualizer.slicing import overlay_on_slices
from owl_keys.controls.utils import decimal_to_ascii
from owl_keys.chat.sync import ChatWrapper
from owl_keys.chat.validation import get_output
from owl_keys.database import KeybindingDatabase
from dotenv import load_dotenv
import ray

load_dotenv()  # Load environment variables from .env file

T_PLUS_MINUS = 1.0
N_WINDOWS = 4


@ray.remote
def process_keyboard_action(
    keyboard_action: int,
    mp4_path: str,
    button_inputs: pd.DataFrame,
    fps: int,
    exe_name: str,
    delete_after_bind: bool = True
) -> tuple[int, Optional[str], str]:
    """
    Process a single keyboard action: create video clips, send to LLM, get label.
    
    Returns:
        tuple of (keyboard_action, action_label, temp_folder_name)
    """
    temp_folder_name = f"clips/temp_{random.randint(0, 1000000)}"
    
    try:
        windows_frames, windows_ts = get_timestamps_around(
            button_inputs, fps, "KEYBOARD", keyboard_action, N_WINDOWS, t_plus_minus=T_PLUS_MINUS
        )
        
        if len(windows_frames) < N_WINDOWS:
            print(f"{windows_frames} less than {N_WINDOWS}")
            print(f"Not enough windows to classify {decimal_to_ascii(keyboard_action)}")
            return keyboard_action, None, temp_folder_name
        
        # Create video clips with overlays
        overlay_on_slices(mp4_path, button_inputs, temp_folder_name, frame_windows=windows_frames, fps=fps)
        
        # Query LLM
        chat = ChatWrapper()
        response = chat.chat(temp_folder_name, keyboard_action, "KEYBOARD", exe_name)
        action = get_output(response)
        
        print(f"\"{decimal_to_ascii(keyboard_action)}\": {action} | {temp_folder_name}")
        
        return keyboard_action, action, temp_folder_name
        
    finally:
        # Cleanup
        if delete_after_bind and os.path.exists(temp_folder_name):
            shutil.rmtree(temp_folder_name)


def slice_and_bind_parallel(
    mp4_path: str,
    csv_path: str,
    metadata_path: str,
    fps: int = 60,
    delete_after_bind: bool = True,
    db_path: str = "keybindings.db",
    max_parallel: int = 16  # Limit concurrent tasks to avoid API rate limits
) -> Dict[int, str]:
    """
    Parallelized version of slice_and_bind using Ray.
    
    Args:
        max_parallel: Maximum number of parallel tasks (adjust based on API rate limits)
    """
    # Extract button inputs
    button_inputs = extract_button_inputs(csv_path, fps)
    unique_keyboard_actions = button_inputs[button_inputs['button_type'] == 'KEYBOARD']['id'].unique()
    
    # Load metadata
    with open(metadata_path, "r") as f:
        metadata = json.load(f)
    exe_name = metadata['game_exe']
    hw_id = metadata['hardware_id']

    # Check if already processed
    with KeybindingDatabase(db_path) as db:
        if db.combo_exists(hw_id, exe_name):
            print(f"Keybindings for {exe_name} + {hw_id} already exist, skipping processing")
            existing_bindings = db.get_keybindings(hw_id, exe_name)
            print(f"Existing bindings: {existing_bindings}")
            return existing_bindings

    # Initialize Ray
    if not ray.is_initialized():
        ray.init()

    print(f"Processing {len(unique_keyboard_actions)} keyboard actions in parallel (max {max_parallel} concurrent)...")
    
    # Put shared data in Ray object store to avoid serialization overhead
    mp4_ref = ray.put(mp4_path)
    button_inputs_ref = ray.put(button_inputs)
    fps_ref = ray.put(fps)
    exe_name_ref = ray.put(exe_name)
    
    # Submit all tasks
    futures = []
    for keyboard_action in unique_keyboard_actions:
        future = process_keyboard_action.remote(
            keyboard_action,
            mp4_ref,
            button_inputs_ref,
            fps_ref,
            exe_name_ref,
            delete_after_bind
        )
        futures.append(future)
    
    # Process results in batches to control parallelism
    keybindings = {}
    batch_size = max_parallel
    
    for i in range(0, len(futures), batch_size):
        batch = futures[i:i + batch_size]
        results = ray.get(batch)
        
        for keyboard_action, action, temp_folder in results:
            if action is not None:
                keybindings[keyboard_action] = action

    # Store results in database
    with KeybindingDatabase(db_path) as db:
        db.insert_keybindings(hw_id, exe_name, keybindings)
        print(f"Stored {len(keybindings)} keybindings for {exe_name} + {hw_id}")

    print(f"Completed processing {len(keybindings)}/{len(unique_keyboard_actions)} keyboard actions")
    
    return keybindings


if __name__ == "__main__":
    try:
        keybindings = slice_and_bind_parallel(
            "sample/vid.mp4",
            "sample/inputs.csv",
            "sample/metadata.json",
            delete_after_bind=True,
            max_parallel=16  # Adjust based on Gemini API rate limits
        )
        print(f"\nFinal keybindings: {keybindings}")
    finally:
        # Shutdown Ray
        if ray.is_initialized():
            ray.shutdown()
