import json
import pandas as pd
import ast
import torch

def safe_eval(arg_list):
    arg_list = arg_list.replace("false", "False")
    arg_list = arg_list.replace("true", "True")
    return ast.literal_eval(arg_list)

def extract_button_inputs(csv_path, fps):
    """
    Extract button input events from CSV and return simplified DataFrame.

    Args:
        csv_path: Path to the input CSV file
        fps: Frames per second for the video

    Returns:
        DataFrame with columns: event_type, button_type, id, frame_idx
        - event_type: "UP" or "DOWN"
        - button_type: "MOUSE" or "KEYBOARD"
        - id: integer identifier for the event
        - frame_idx: frame number (relative to START event)
    """
    # Load CSV - only read the first 3 columns to avoid issues with malformed JSON in event_args
    # Some CSVs have JSON with unescaped quotes that breaks parsing
    df = pd.read_csv(
        csv_path, 
        usecols=[0, 1, 2],
        names=['timestamp', 'event_type', 'event_args'],
        header=0,
        on_bad_lines='skip',
        low_memory=False
    )
    
    # Convert timestamp to numeric, coercing errors
    df['timestamp'] = pd.to_numeric(df['timestamp'], errors='coerce')
    
    # Drop rows where timestamp couldn't be parsed
    df = df.dropna(subset=['timestamp'])
    
    if df.empty or df['timestamp'].isna().all():
        raise ValueError(f"Could not parse 'timestamp' column as numeric in {csv_path}")

    # Find start time and normalize timestamps
    start_mask = df["event_type"] == "START"
    if start_mask.any():
        start_time = df[start_mask].iloc[-1]["timestamp"]
        df["timestamp"] = df["timestamp"] - start_time

    # Filter for keyboard and mouse button events only
    df = df[df["event_type"].isin(["KEYBOARD", "MOUSE_BUTTON"])].copy()
    
    if df.empty:
        raise ValueError(f"No KEYBOARD or MOUSE_BUTTON events found in {csv_path}")

    # Parse event_args to extract button ID and pressed state
    parsed_args = df["event_args"].apply(lambda x: safe_eval(x))
    df["id"] = parsed_args.apply(lambda x: x[0])
    df["is_pressed"] = parsed_args.apply(lambda x: x[1])

    # Map to button_type
    df["button_type"] = df["event_type"].map({
        "KEYBOARD": "KEYBOARD",
        "MOUSE_BUTTON": "MOUSE"
    })

    # Map to event_type (UP/DOWN)
    df["event_type"] = df["is_pressed"].map({
        True: "DOWN",
        False: "UP"
    })

    # Calculate frame index
    df["frame_idx"] = (df["timestamp"] * fps).round().astype(int)

    # Select and return only the required columns
    return df[["event_type", "button_type", "id", "frame_idx"]].reset_index(drop=True)

def get_timestamps_around(df, fps, button_type, identifier, n_ts, t_plus_minus = 2.5):
    """
    Get timestamp windows around segments of a video where a certain button was presed.

    :param df: The control dataframe produced by extract_button_inputs
    :param fps: The frames per second of the video
    :param button_type: "KEYBOARD" or "MOUSE"
    :param identifier: The id of the button/key i.e. 0, 1, 2, ...
    :param n_ts: The number of overall separate windows
    :param plus_minus_ts: The number of seconds to add before/after the event to give some buffer for labeller
    """

    frame_plus_minus = int(t_plus_minus * fps)

    # Simplest way of doing this is to create a bool tensor for states
    max_frames = df['frame_idx'].max()
    num_mouse_buttons = df[df['button_type']=='MOUSE']['id'].max() + 1
    num_keyboard_buttons = df[df['button_type']=='KEYBOARD']['id'].max() + 1

    input_tensor = torch.zeros(max_frames, num_keyboard_buttons + num_mouse_buttons, dtype=torch.bool)
    
    # Frame starts of events
    event_intervals_mouse = {}
    event_intervals_keyboard = {}

    def update(col, start ,end):
        input_tensor[start:end, col] = True 

    for _, row in df.iterrows():
        id_ = row['id']
        btn_type = row['button_type']
        event_type = row['event_type']

        if btn_type == 'MOUSE':
            if id_ in event_intervals_mouse: # Key was held down
                if event_type == 'DOWN':
                    continue # Down after down does nothing
                else:
                    # Was just released
                    start = event_intervals_mouse[id_]
                    end = row['frame_idx']
                    update(id_, start, end)
                    del event_intervals_mouse[id_]
            else:
                if event_type == 'DOWN':
                    event_intervals_mouse[id_] = row['frame_idx'] # Mark as held down
        elif btn_type == 'KEYBOARD':
            if id_ in event_intervals_keyboard: # Key was held down
                if event_type == 'DOWN':
                    continue # Down after down does nothing
                else:
                    # Was just released
                    start = event_intervals_keyboard[id_]
                    end = row['frame_idx']
                    update(id_+num_mouse_buttons, start, end)
                    del event_intervals_keyboard[id_]
            else:
                if event_type == 'DOWN':
                    event_intervals_keyboard[id_] = row['frame_idx'] # Mark as held down

    is_pressed = torch.zeros(max_frames, 2, dtype=torch.int16)
    is_pressed[:, 0] = input_tensor[:, identifier if button_type == "MOUSE" else identifier+num_mouse_buttons]
    is_pressed[:, 1] = input_tensor.to(torch.int16).sum(dim=1) # How many others pressed rn

    # Add another arange column of frame indices to the tensor
    is_pressed = torch.cat([is_pressed, torch.arange(max_frames).unsqueeze(1)], dim=1)

    # Filter by cases where is_pressed[:,0] is 1
    # Then sort by is_pressed[:,1] in ascending order

    is_pressed = is_pressed[is_pressed[:,0] == 1]
    is_pressed = is_pressed[is_pressed[:,1].argsort(descending=False)]

    # Now find n_ts rows such that is_pressed[:,-1] is not nearby in any other row's is_pressed[:,-1]
    exemplars_frame_idx = [] # Best frames to find active data
    n_exemplars = 0
    nearby_tol = 60*5 # Within 5 seconds

    for i in range(len(is_pressed)):
        frame_idx = is_pressed[i, -1]
        if not any(abs(exemplars_frame_idx[j] - frame_idx) < nearby_tol for j in range(len(exemplars_frame_idx))):
            exemplars_frame_idx.append(frame_idx)
            n_exemplars += 1
            if n_exemplars >= n_ts:
                break

    windows_frames = []
    windows_ts = []
    input_tensor_slices = []
    for frame_idx in exemplars_frame_idx:
        windows_frames.append([
            int(frame_idx - frame_plus_minus),
            int(frame_idx + frame_plus_minus)
        ])
        windows_ts.append([
            float(frame_idx) / float(fps) - float(t_plus_minus),
            float(frame_idx) / float(fps) + float(t_plus_minus)
        ])
        window_start = frame_idx - frame_plus_minus
        window_end = frame_idx + frame_plus_minus
        input_tensor_slices.append(input_tensor[window_start:window_end, :])

    return windows_frames, windows_ts