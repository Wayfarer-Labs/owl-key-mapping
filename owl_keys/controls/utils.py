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