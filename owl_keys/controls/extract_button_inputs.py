import json
import pandas as pd
import ast


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
    # Load CSV
    df = pd.read_csv(csv_path)

    # Find start time and normalize timestamps
    start_mask = df["event_type"] == "START"
    if start_mask.any():
        start_time = df[start_mask].iloc[-1]["timestamp"]
        df["timestamp"] = df["timestamp"] - start_time

    # Filter for keyboard and mouse button events only
    df = df[df["event_type"].isin(["KEYBOARD", "MOUSE_BUTTON"])].copy()

    # Parse event_args to extract button ID and pressed state
    parsed_args = df["event_args"].apply(lambda x: ast.literal_eval(x))
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
    frame_duration = 1.0 / fps
    df["frame_idx"] = (df["timestamp"] / frame_duration).round().astype(int)

    # Select and return only the required columns
    return df[["event_type", "button_type", "id", "frame_idx"]].reset_index(drop=True)

def get_timestamps_around(df, fps, event_type, identifier, n_ts, plus_minus_ts = 0.5):
    """
    Get timestamp windows around segments of a video where a certain button was presed.

    :param df: The control dataframe produced by extract_button_inputs
    :param fps: The frames per second of the video
    :param event_type: "KEYBOARD" or "MOUSE"
    :param identifier: The id of the button/key i.e. 0, 1, 2, ...
    :param n_ts: The number of overall separate windows
    :param plus_minus_ts: The number of seconds to add before/after the event to give some buffer for labeller
    """

    # Firstly we will convert to a new kind of dataframe that has columns
    # frame_idx | buttons_active 
    # frame_idx is same as before, buttons_active is a list of strings identifiying which buttons are "active"
    # to differentiate between mouse and keyboard we will do f"M{id}" for f"K{id}" for these strings
    # Creating buttons active will be a bit tricky because it abstracts away up/down
    # A button is active it is being held down, and hasn't been released yet
    # Activity becomes false when button is release

    # Preserve dict for all buttons
    button_states = {}
    output_rows = {}

    rows_in_frame = []
    crnt_frame = None

    # For loop through each of them
    for _, row in df.iterrows():
        frame_idx = row['frame_idx']

        if crnt_frame is not None and crnt_frame == frame_idx: # Same frame as before
            rows_in_frame.append(row)
            continue
        elif len(rows_in_frame) == 0: # 
            crnt_frame = frame_idx
            rows_in_frame.append(row)