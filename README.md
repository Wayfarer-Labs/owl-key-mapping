# owl-key-mapping

VLMs for getting keybinds from game + control setup

## Overview

This project uses Vision Language Models (VLMs) to automatically identify and label keybindings from gameplay videos. It processes video clips of key presses, overlays control information, and uses Google's Gemini or Vertex AI to classify the actions performed by each key/button.

## Features

- Parallel processing using Ray for efficient handling of multiple keybindings
- Support for both Google Gemini API and Vertex AI
- Automatic video slicing and overlay generation
- SQLite database for storing keybinding mappings
- Support for keyboard and mouse inputs

## Setup

### Prerequisites

- Python 3.8+
- Access to Google Gemini API or Vertex AI
- Video files (.mp4) with corresponding input data

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd owl-key-mapping
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### API Configuration

#### Option 1: Google Gemini API
1. Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a `.env` file in the project root:
   ```
   GOOGLE_API_KEY=your_api_key_here
   ```

#### Option 2: Vertex AI
1. Set up a Google Cloud Project with Vertex AI enabled
2. Create a service account and download the JSON key file
3. Set the environment variable:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json
   ```
   Or add it to your `.env` file:
   ```
   GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json
   ```

## Data Preparation

Each sample requires three files in a directory:

1. `vid.mp4` - The gameplay video file
2. `inputs.csv` - CSV file containing button input data with columns for timestamps, button types, and IDs
3. `metadata.json` - JSON file with game metadata:
   ```json
   {
     "game_exe": "game_executable_name.exe",
     "hardware_id": "unique_hardware_identifier"
   }
   ```

## Usage

### Basic Usage

Run the parallel keybinding extraction:

```bash
python owl_keys/bind_parallel.py --data_dir /path/to/data --db_path keybindings.db
```

### Command Line Arguments

- `--data_dir`: Directory containing sample subdirectories (default: "/mnt/data/waypoint_1/owl_control/kbm/fps")
- `--db_path`: Path to the SQLite database file (default: "keybindings.db")
- `--use_google_genai`: Use Gemini API instead of Vertex AI (default: False, uses Vertex AI)
- `--max_parallel`: Maximum number of parallel tasks (default: 31)

### Example

```bash
python owl_keys/bind_parallel.py \
  --data_dir /mnt/data/game_samples \
  --db_path my_keybindings.db \
  --max_parallel 16 \
  --use_google_genai
```

This will process all samples in `/mnt/data/game_samples`, using the Gemini API with up to 16 parallel tasks, and store results in `my_keybindings.db`.

## Output

The script outputs keybinding mappings in the format:
```
{
  key_code: "action_description",
  ...
}
```

For example:
```json
{
  87: "move forward",
  83: "move backward",
  65: "strafe left",
  68: "strafe right",
  32: "jump"
}
```

## Database

Keybindings are stored in a SQLite database with the following schema:
- `hw_id`: Hardware identifier
- `game_exe`: Game executable name
- `key_code`: Numerical key/button code
- `action`: Human-readable action description
- `created_at`: Timestamp of creation

## Testing

Run the test script to verify basic functionality:

```bash
python test.py
```

For a full sequential test:

```bash
python full_test.py
```

## Architecture

- `owl_keys/bind_parallel.py`: Main parallel processing script
- `owl_keys/controls/`: Input extraction and processing utilities
- `owl_keys/visualizer/`: Video slicing and overlay generation
- `owl_keys/chat/`: LLM integration (Gemini and Vertex AI)
- `owl_keys/database.py`: Database operations

## Troubleshooting

- Ensure your API keys are correctly configured
- Check that video files are accessible and not corrupted
- Verify CSV input data format matches expectations
- For Vertex AI, ensure your service account has appropriate permissions
- Reduce `max_parallel` if hitting API rate limits
