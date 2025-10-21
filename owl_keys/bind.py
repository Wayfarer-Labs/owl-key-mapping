import os
import sys
import pandas as pd
import shutil
import random
import json

# When this file is executed directly as a script (python owl_keys/bind.py),
# sys.path[0] is the package directory (owl_keys/) which prevents absolute
# imports like `from owl_keys...` from resolving. Ensure the project root is on
# sys.path so absolute imports work both when running from repo root and when
# running this file directly.
if os.path.basename(sys.path[0]) == os.path.basename(os.path.dirname(__file__)):
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from owl_keys.controls.extract_button_inputs import extract_button_inputs, get_timestamps_around
from owl_keys.visualizer.slicing import overlay_on_slices
from owl_keys.controls.utils import decimal_to_ascii
from owl_keys.chat.sync import ChatWrapper
from owl_keys.chat.validation import get_output
from owl_keys.database import KeybindingDatabase

T_PLUS_MINUS = 1.0
N_WINDOWS = 4

def slice_and_bind(mp4_path, csv_path, metadata_path, fps = 60, delete_after_bind = True, db_path = "keybindings.db"):
    button_inputs = extract_button_inputs(csv_path, 60)
    unique_mouse_actions = button_inputs[button_inputs['button_type'] == 'MOUSE']['id'].unique()
    unique_keyboard_actions = button_inputs[button_inputs['button_type'] == 'KEYBOARD']['id'].unique()
    with open(metadata_path, "r") as f:
        metadata = json.load(f)
    exe_name = metadata['game_exe']
    hw_id = metadata['hardware_id']

    # Check if this combo already exists in database
    with KeybindingDatabase(db_path) as db:
        if db.combo_exists(hw_id, exe_name):
            print(f"Keybindings for {exe_name} + {hw_id} already exist, skipping processing")
            existing_bindings = db.get_keybindings(hw_id, exe_name)
            print(f"Existing bindings: {existing_bindings}")
            return existing_bindings

    chat = ChatWrapper()
    keybindings = {}

#    for mouse_action in unique_mouse_actions:
#        windows_frames, windows_ts = get_timestamps_around(button_inputs, fps, "MOUSE", mouse_action, N_WINDOWS, t_plus_minus = T_PLUS_MINUS)
#        overlay_on_slices(mp4_path, button_inputs, temp_folder_name, frame_windows=windows_frames, fps=fps)
#        response = chat.chat(temp_folder_name, mouse_action, "MOUSE")
#        print(f"M{mouse_action}: {get_output(response)}")

    for keyboard_action in unique_keyboard_actions:
        temp_folder_name = f"clips/temp_{random.randint(0, 1000000)}"
        windows_frames, windows_ts = get_timestamps_around(button_inputs, fps, "KEYBOARD", keyboard_action, N_WINDOWS, t_plus_minus = T_PLUS_MINUS)
        if len(windows_frames) < N_WINDOWS: # Not enough windows to classify
            print(f"Not enough windows to classify {decimal_to_ascii(keyboard_action)}")
            continue
        overlay_on_slices(mp4_path, button_inputs, temp_folder_name, frame_windows=windows_frames, fps=fps)
        response = chat.chat(temp_folder_name, keyboard_action, "KEYBOARD", exe_name)
        action = get_output(response)
        print(f"\"{decimal_to_ascii(keyboard_action)}\": {action} | {temp_folder_name}")

        keybindings[keyboard_action] = action

        if delete_after_bind:
            shutil.rmtree(temp_folder_name)

    # Store keybindings in database
    with KeybindingDatabase(db_path) as db:
        db.insert_keybindings(hw_id, exe_name, keybindings)
        print(f"Stored {len(keybindings)} keybindings for {exe_name} + {hw_id}")

    return keybindings

if __name__ == "__main__":
    # Only run the example binding flow when executed as a script.
    slice_and_bind("sample/vid.mp4", "sample/inputs.csv", "sample/metadata.json", delete_after_bind=True)