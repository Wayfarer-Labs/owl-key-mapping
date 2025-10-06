import subprocess
import tempfile
import os

from .overlay import overlay_buttons_multi_window

def slice_video(vid_path, output_path, window_start, window_end):
    # Window here is in seconds
    subprocess.run([
        "ffmpeg",
        "-y",
        "-i", vid_path,
        "-ss", max(0, str(window_start)),
        "-t", max(0, str(window_end - window_start)),
        output_path
    ])

def slice_df(df, window_start, window_end):
    # Window here is in frame numbers
    return df[(df['frame_idx'] >= window_start) & (df['frame_idx'] <= window_end)]

def overlay_on_slices(vid_path, df, output_path, frame_windows, fps = 60):
    """
    Get an overlay video on a specific slice
    :param vid_path: Path to the full video
    :param df: Dataframe from extract_button_inputs output
    :param output_path: Folder with all video slices for output
    :param fps: Frames per second of the video
    :param frame_windows: Listof Tuple of (start, end) in frame numbers
    """
    overlay_buttons_multi_window(
        vid_path,
        df,
        output_path,
        fps=fps,
        frame_windows=frame_windows
    )
    # Compress every video in the output directory
    import glob

    video_files = glob.glob(os.path.join(output_path, "*.mp4"))
    for video_file in video_files:
        compressed_path = video_file + ".compressed.mp4"
        subprocess.run([
            "ffmpeg",
            "-y",
            "-i", video_file,
            "-vf", "fps=20",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "32",
            "-an",
            compressed_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.replace(compressed_path, video_file)