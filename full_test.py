import os
import pandas as pd
import shutil
import random

from owl_keys.controls.extract_button_inputs import extract_button_inputs, get_timestamps_around
from owl_keys.visualizer.slicing import overlay_on_slices
from owl_keys.controls.utils import decimal_to_ascii
from owl_keys.chat.sync import ChatWrapper
from owl_keys.chat.validation import get_output

T_PLUS_MINUS = 1.0
N_WINDOWS = 4

def slice_and_bind(mp4_path, csv_path, metadata_path = None, fps = 60, delete_after_bind = True):
    button_inputs = extract_button_inputs(csv_path, 60)
    unique_mouse_actions = button_inputs[button_inputs['button_type'] == 'MOUSE']['id'].unique()
    unique_keyboard_actions = button_inputs[button_inputs['button_type'] == 'KEYBOARD']['id'].unique()

    chat = ChatWrapper()

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
        response = chat.chat(temp_folder_name, keyboard_action, "KEYBOARD")
        print(f"\"{decimal_to_ascii(keyboard_action)}\": {get_output(response)} | {temp_folder_name}")

        if delete_after_bind:
            shutil.rmtree(temp_folder_name)

slice_and_bind("sample/vid.mp4", "sample/inputs.csv", delete_after_bind=False)