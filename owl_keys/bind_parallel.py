import os
import sys
import pandas as pd
import shutil
import random
import json
import time
import logging
from typing import Dict, Optional

# Path setup for imports
if os.path.basename(sys.path[0]) == os.path.basename(os.path.dirname(__file__)):
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from owl_keys.controls.extract_button_inputs import extract_button_inputs, get_timestamps_around
from owl_keys.visualizer.slicing import overlay_on_slices
from owl_keys.controls.utils import decimal_to_ascii
from owl_keys.chat.sync import ChatWrapper
from owl_keys.chat.vertex_wrapper import VertexChatWrapper
from owl_keys.chat.validation import get_output
from owl_keys.database import KeybindingDatabase
from dotenv import load_dotenv
import ray
from tqdm import tqdm

load_dotenv()  # Load environment variables from .env file

T_PLUS_MINUS = 1.0
N_WINDOWS = 4

# Suppress Ray logs
os.environ["RAY_DEDUP_LOGS"] = "0"
logging.getLogger("ray").setLevel(logging.WARNING)


def process_keyboard_action(
    keyboard_action: int,
    mp4_path: str,
    button_inputs: pd.DataFrame,
    fps: int,
    exe_name: str,
    delete_after_bind: bool = True,
    use_vertex: bool = False,
    vertex_model: str = "gemini-2.0-flash-exp",
    gemini_model: str = "gemini-2.5-flash-lite"
) -> tuple[int, Optional[str], str]:
    """
    Process a single keyboard action: create video clips, send to LLM, get label.
    
    Returns:
        tuple of (keyboard_action, action_label, temp_folder_name)
    """
    temp_folder_name = f"clips/temp_{random.randint(0, 1000000)}"
    
    try:
        windows_frames, windows_ts = get_timestamps_around(
            button_inputs, fps, "KEYBOARD", keyboard_action, N_WINDOWS, t_plus_minus=T_PLUS_MINUS
        )
        
        if len(windows_frames) < N_WINDOWS:
            logging.debug(f"{windows_frames} less than {N_WINDOWS}")
            logging.debug(f"Not enough windows to classify {decimal_to_ascii(keyboard_action)}")
            return keyboard_action, None, temp_folder_name
        
        # Create video clips with overlays
        overlay_on_slices(mp4_path, button_inputs, temp_folder_name, frame_windows=windows_frames, fps=fps)
        
        # Query LLM - choose between Gemini API or Vertex API
        if use_vertex:
            chat = VertexChatWrapper(model=vertex_model)
        else:
            chat = ChatWrapper(model=gemini_model)
        
        response = chat.chat(temp_folder_name, keyboard_action, "KEYBOARD", exe_name)
        action = get_output(response)
        
        logging.info(f"\"{decimal_to_ascii(keyboard_action)}\": {action} | {temp_folder_name}")
        
        return keyboard_action, action, temp_folder_name
        
    finally:
        # Cleanup
        if delete_after_bind and os.path.exists(temp_folder_name):
            shutil.rmtree(temp_folder_name)


@ray.remote
def process_video_sample(
    sample_dir: str,
    data_dir: str,
    db_path: str,
    delete_after_bind: bool = True,
    use_vertex: bool = False,
    vertex_model: str = "google/gemini-2.0-flash",
    gemini_model: str = "gemini-2.5-flash-lite",
    fps: int = 60
) -> tuple[str, Optional[Dict[int, str]], Optional[str]]:
    """
    Process a single video sample: extract inputs, process all keyboard actions sequentially.
    
    Returns:
        tuple of (sample_name, keybindings_dict or None, error_message or None)
    """
    try:
        mp4_dir = os.path.join(data_dir, sample_dir)
        mp4_files = [f for f in os.listdir(mp4_dir) if f.lower().endswith(".mp4")]
        
        if not mp4_files:
            return sample_dir, None, f"No mp4 found in {mp4_dir}"
        
        mp4_name = mp4_files[0]
        mp4_path = os.path.join(mp4_dir, mp4_name)
        csv_path = os.path.join(data_dir, sample_dir, "inputs.csv")
        metadata_path = os.path.join(data_dir, sample_dir, "metadata.json")
        
        # Extract button inputs
        button_inputs = extract_button_inputs(csv_path, fps)
        unique_keyboard_actions = button_inputs[button_inputs['button_type'] == 'KEYBOARD']['id'].unique()
        
        # Load metadata
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        exe_name = metadata['game_exe']
        hw_id = metadata['hardware_id']
        
        # Check if already processed
        with KeybindingDatabase(db_path) as db:
            if db.combo_exists(hw_id, exe_name):
                existing_bindings = db.get_keybindings(hw_id, exe_name)
                return sample_dir, existing_bindings, None
        
        # Process keyboard actions sequentially
        keybindings = {}
        for keyboard_action in unique_keyboard_actions:
            keyboard_action_int, action, temp_folder = process_keyboard_action(
                keyboard_action,
                mp4_path,
                button_inputs,
                fps,
                exe_name,
                delete_after_bind,
                use_vertex,
                vertex_model,
                gemini_model
            )
            if action is not None:
                keybindings[keyboard_action_int] = action
        
        # Store results in database
        with KeybindingDatabase(db_path) as db:
            db.insert_keybindings(hw_id, exe_name, keybindings)
        
        return sample_dir, keybindings, None
        
    except Exception as e:
        return sample_dir, None, str(e)


def process_videos_parallel(
    data_dir: str,
    db_path: str = "keybindings.db",
    max_parallel: int = 16,
    delete_after_bind: bool = True,
    use_vertex: bool = False,
    vertex_model: str = "google/gemini-2.0-flash",
    gemini_model: str = "gemini-2.5-flash-lite",
    fps: int = 60
) -> Dict[str, Dict[int, str]]:
    """
    Process multiple video samples in parallel using Ray.
    Each video is processed as a separate Ray task, with keyboard actions processed sequentially within each video.
    
    Args:
        data_dir: Directory containing sample subdirectories
        db_path: Path to the keybinding database
        max_parallel: Maximum number of parallel video processing tasks
        delete_after_bind: Whether to delete temporary files after processing
        use_vertex: If True, use Vertex API; if False, use Gemini API
        vertex_model: Model name for Vertex API
        gemini_model: Model name for Gemini API
        fps: Frames per second for video processing
        
    Returns:
        Dictionary mapping sample names to their keybindings
    """
    # Initialize Ray once
    if not ray.is_initialized():
        ray.init(num_cpus=max_parallel, logging_level=logging.WARNING)
    
    # Get all sample directories
    sample_dirs = [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))]
    total_samples = len(sample_dirs)
    
    api_type = "Vertex API" if use_vertex else "Gemini API"
    model_name = vertex_model if use_vertex else gemini_model
    logging.info(f"Processing {total_samples} video samples in parallel using {api_type} with model {model_name} (max {max_parallel} concurrent)...")
    
    # Submit all video processing tasks at once
    futures = []
    for sample_dir in sample_dirs:
        future = process_video_sample.options(num_cpus=1).remote(
            sample_dir,
            data_dir,
            db_path,
            delete_after_bind,
            use_vertex,
            vertex_model,
            gemini_model,
            fps
        )
        futures.append(future)
    
    # Process results as they complete with tqdm progress bar
    all_keybindings = {}
    
    with tqdm(total=total_samples, desc="Processing videos", unit="video") as pbar:
        while futures:
            # Wait for any task to complete
            done, futures = ray.wait(futures, num_returns=1, timeout=None)
            
            for done_ref in done:
                try:
                    sample_name, keybindings, error = ray.get(done_ref)
                    if error:
                        logging.warning(f"Error processing {sample_name}: {error}")
                    elif keybindings:
                        all_keybindings[sample_name] = keybindings
                        logging.info(f"Completed {sample_name}: {len(keybindings)} keybindings")
                except Exception as e:
                    logging.error(f"Failed to get result: {e}")
                
                pbar.update(1)
    
    logging.info(f"Completed processing {len(all_keybindings)}/{total_samples} video samples")
    
    return all_keybindings

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Bind keybindings in parallel using Gemini or Vertex API")
    parser.add_argument("--data_dir", type=str, default="/mnt/data/waypoint_1/owl_control/kbm/fps", help="Directory containing sample subdirectories")
    parser.add_argument("--db_path", type=str, default="keybindings.db", help="Path to the keybinding database")
    parser.add_argument("--use_google_genai", action="store_true", help="Use Gemini API instead of Vertex API")
    parser.add_argument("--max_parallel", type=int, default=31, help="Maximum number of parallel video processing tasks")
    parser.add_argument("--fps", type=int, default=60, help="Frames per second for video processing")
    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        filename='keybinding_processing.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    if os.path.exists(args.data_dir):
        logging.info(f"Data directory: {args.data_dir}")
    else:
        print(f"Data directory {args.data_dir} does not exist!")
        sys.exit(1)
    
    use_vertex = not args.use_google_genai
    logging.info(f"Database path: {args.db_path} | Using Vertex API: {use_vertex} | Max parallel: {args.max_parallel}")
    
    try:
        all_keybindings = process_videos_parallel(
            data_dir=args.data_dir,
            db_path=args.db_path,
            max_parallel=args.max_parallel,
            delete_after_bind=True,
            use_vertex=use_vertex,
            fps=args.fps
        )
        
        logging.info(f"Successfully processed {len(all_keybindings)} video samples")
        print(f"\nCompleted! Processed {len(all_keybindings)} video samples.")
        
    except Exception as e:
        logging.error(f"Error during parallel processing: {e}")
        raise
    finally:
        # Shutdown Ray
        if ray.is_initialized():
            ray.shutdown()
