import os
import pandas as pd
from owl_keys.controls.extract_button_inputs import extract_button_inputs, get_timestamps_around

path = "/mnt/data/datasets/extracted_tars/6049da38b3354166"
mp4_path = os.path.join(path, "000000.mp4")
csv_path = os.path.join(path, "000000.csv")

button_inputs = extract_button_inputs(csv_path, 60)

from owl_keys.visualizer.overlay import overlay_buttons
#overlay_buttons(mp4_path, button_inputs, "output_3.mp4", min_frames = 60*35, max_frames = 60*45)

# Filter for frames between 60*35 and 60*45 (inclusive of 60*35, exclusive of 60*45)
start_frame = 60 * 35
end_frame = 60 * 45

# Only keep rows where id is in [87, 65, 83, 68] (WASD)
wasd_ids = [87, 65, 83, 68]
wasd_map = {87: 'W', 65: 'A', 83: 'S', 68: 'D'}

filtered = button_inputs[
    (button_inputs['frame_idx'] >= start_frame) &
    (button_inputs['frame_idx'] < end_frame) &
    (button_inputs['id'].isin(wasd_ids))
].copy()

# Map id to WASD character
filtered['wasd_char'] = filtered['id'].map(wasd_map)

# Remove button type, convert frame number to timestamp,
# but add offset
filtered['frame_idx'] = filtered['frame_idx'] - start_frame
filtered['timestamp'] = filtered['frame_idx'] * (1.0 / 60)

# Remove frame_idx and id
filtered = filtered[['event_type', 'wasd_char', 'timestamp']]

# Save to CSV
filtered.to_csv("wasd_slice.csv", index=False)
