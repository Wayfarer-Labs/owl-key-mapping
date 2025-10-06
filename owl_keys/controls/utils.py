class FrameIterator:
    """
    Takes the dataframe outputted from extract_button_inputs
    Calling "next" returns a List[Dict] of all events that happened in that frame
    """
    def __init__(self, df):
        self.df = df
        self.current_frame_idx = 0
        self.max_frame = self.df['frame_idx'].max() if not self.df.empty else -1

    def __iter__(self):
        return self

    def __next__(self):
        if self.current_frame_idx > self.max_frame:
            raise StopIteration
        
        # Get all events for the current frame
        current_frame_events = self.df[self.df['frame_idx'] == self.current_frame_idx].to_dict('records')
        self.current_frame_idx += 1
        
        return current_frame_events

    def get_frame_events(self, frame_idx):
        return self.df[self.df['frame_idx'] == frame_idx].to_dict('records')
    
def decimal_to_ascii(decimal_value):
    """
    Converts a decimal keycode to a human-readable string.
    Handles special keycodes commonly used as keybinds in games.
    """
    special_keys = {
        32: "SPACE",
        18: "LSHIFT",
        20: "LCTRL",
        235: "LEFT",
        244: "RIGHT",
        80: "RSHIFT",
        245: "UP",
        242: "DOWN",
        13: "TAB",
    }
    if decimal_value in special_keys:
        return special_keys[decimal_value]
    try:
        # Only printable ASCII range (32-126) is mapped to characters
        if 32 <= decimal_value <= 126:
            return chr(decimal_value)
        else:
            return f"KEY_{decimal_value}"
    except Exception:
        return f"KEY_{decimal_value}"