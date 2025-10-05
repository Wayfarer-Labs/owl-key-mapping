import cv2
from ..controls.utils import FrameIterator

# Constants define shapes/dimensions of different things
MOUSE_BOX_OFFSET_X = 10
MOUSE_BOX_OFFSET_Y = 400
KEYBOARD_BOX_OFFSET_X = 10
KEYBOARD_BOX_OFFSET_Y = 450

MOUSE_BOX_SIZE = 20
KEYBOARD_BOX_SIZE = 20

MOUSE_BOX_COLOR = (255, 0, 0)
KEYBOARD_BOX_COLOR = (0, 255, 0)

MOUSE_BOX_HORIZONTAL_SPACING = 10
KEYBOARD_BOX_HORIZONTAL_SPACING = 10

FONT_SIZE = 16

"""
Draws an overlay of buttons over a video with the following specifications:

Each mouse button becomes a red box. There is text over the box with the ID of the button.
The box turns MOUSE_BOX_COLOR while the button is actively being pressed (between DOWN and UP events).
The first mouse box is placed at (MOUSE_BOX_OFFSET_X, MOUSE_BOX_OFFSET_Y).
The rest are placed at the same Y but with varying X coordinates s.t. second box would be at (MOUSE_BOX_OFFSET_X + MOUSE_BOX_SIZE + MOUSE_BOX_HORIZONTAL_SPACING, MOUSE_BOX_OFFSET_Y).

The same applies to keyboard button boxes, which are also red to start but become KEYBOARD_BOX_COLOR when pressed.
Most things are the same but the two rows of buttons are at different Y coordinates.

Font size for text above buttons should be FONT_SIZE
"""

def overlay_buttons(vid_path, df, output_path, fps = 60, min_frames = None, max_frames = None):
    # Df is output from extract_button_inputs
    # cols are event_type (DOWN/UP), button_type (MOUSE/KEYBOARD), id (int), frame_idx (int)

    # Track button states and positions
    mouse_buttons = {}  # id -> {x, y, pressed}
    keyboard_buttons = {}  # id -> {x, y, pressed}

    # Discover all unique button IDs and assign positions
    mouse_idx = 0
    keyboard_idx = 0

    # Establish all boxes we will need and their coordinates
    for _, row in df.iterrows():
        btn_id = row['id']
        btn_type = row['button_type']

        if btn_type == 'MOUSE' and btn_id not in mouse_buttons:
            x = MOUSE_BOX_OFFSET_X + mouse_idx * (MOUSE_BOX_SIZE + MOUSE_BOX_HORIZONTAL_SPACING)
            mouse_buttons[btn_id] = {'x': x, 'y': MOUSE_BOX_OFFSET_Y, 'pressed': False}
            mouse_idx += 1
        elif btn_type == 'KEYBOARD' and btn_id not in keyboard_buttons:
            x = KEYBOARD_BOX_OFFSET_X + keyboard_idx * (KEYBOARD_BOX_SIZE + KEYBOARD_BOX_HORIZONTAL_SPACING)
            keyboard_buttons[btn_id] = {'x': x, 'y': KEYBOARD_BOX_OFFSET_Y, 'pressed': False}
            keyboard_idx += 1

    # Open video
    cap = cv2.VideoCapture(vid_path)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, fps, (512, 512))

    frame_iterator = FrameIterator(df)

    frame_idx = 0
    df_idx = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        events = frame_iterator.get_frame_events(frame_idx)
        if events:
            for event in events:
                id_ = event['id']
                btn_type = event['button_type']
                event_type = event['event_type']
                if btn_type == 'MOUSE':
                    mouse_buttons[id_]['pressed'] = event_type == 'DOWN'
                else:
                    keyboard_buttons[id_]['pressed'] = event_type == 'DOWN'

        # Draw mouse buttons
        for btn_id, btn in mouse_buttons.items():
            color = MOUSE_BOX_COLOR if btn['pressed'] else (0, 0, 255)  # Red when unpressed
            cv2.rectangle(frame, (btn['x'], btn['y']),
                         (btn['x'] + MOUSE_BOX_SIZE, btn['y'] + MOUSE_BOX_SIZE),
                         color, -1)
            cv2.putText(frame, str(btn_id), (btn['x'], btn['y'] - 2),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

        # Draw keyboard buttons
        for btn_id, btn in keyboard_buttons.items():
            color = KEYBOARD_BOX_COLOR if btn['pressed'] else (0, 0, 255)  # Red when unpressed
            cv2.rectangle(frame, (btn['x'], btn['y']),
                         (btn['x'] + KEYBOARD_BOX_SIZE, btn['y'] + KEYBOARD_BOX_SIZE),
                         color, -1)
            cv2.putText(frame, str(btn_id), (btn['x'], btn['y'] - 2),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                       
        if frame_idx >= min_frames:
            writer.write(frame)
        frame_idx += 1

        if max_frames is not None and frame_idx >= max_frames:
            break

    cap.release()
    writer.release()
