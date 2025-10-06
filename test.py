import os
import pandas as pd
from owl_keys.controls.extract_button_inputs import extract_button_inputs, get_timestamps_around

path = "sample"
mp4_path = os.path.join(path, "vid.mp4")
csv_path = os.path.join(path, "inputs.csv")

button_inputs = extract_button_inputs(csv_path, 60)

from owl_keys.visualizer.slicing import overlay_on_slices

windows_frames, windows_ts = get_timestamps_around(button_inputs, 60, "KEYBOARD", 32, 4, t_plus_minus = 1.0)
overlay_on_slices(mp4_path, button_inputs, "output", frame_windows=windows_frames, fps=60)