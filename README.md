# VLC Video Logger

## Overview
VLC Video Logger is a Python application that integrates VLC media player for video playback while providing logging functionality. Users can play videos, control playback, and log events related to video playback in a CSV file.

## Project Structure
```
vlc-video-logger
├── src
│   ├── main.py          # Entry point of the application
│   ├── vlc_player.py    # Manages video playback using VLC
│   ├── csv_logger.py     # Handles logging functionality
│   └── gui.py           # Defines the GUI layout and interactions
├── requirements.txt      # Lists project dependencies
└── README.md             # Documentation for the project
```

## Setup Instructions
1. **Clone the repository:**
   ```
   git clone <repository-url>
   cd vlc-video-logger
   ```

2. **Install dependencies:**
   Ensure you have Python installed, then run:
   ```
   pip install -r requirements.txt
   ```

3. **Run the application:**
   Execute the following command to start the application:
   ```
   python src/main.py
   ```

## Packaging as a Standalone Executable (Windows)

To distribute the application as a single executable file, you can use [PyInstaller](https://pyinstaller.org/):

1. **Install PyInstaller:**
   ```
   pip install pyinstaller
   ```

2. **Build the executable:**
   Run this command from the project root:
   ```
   pyinstaller --onefile --noconsole --add-data "src;src" src/main.py
   ```
   - `--onefile`: Creates a single executable file.
   - `--noconsole`: Hides the console window (for GUI apps).
   - `--add-data "src;src"`: Includes your `src` folder and its files.

3. **Find your executable:**
   The resulting `.exe` will be in the `dist` folder as `main_gui.exe`.

**Note:**
- The user must have VLC installed on their system for video playback to work.
- You may need to adjust the `--add-data` path format if using a different OS (see PyInstaller docs).

## Usage
- Open a video file using the GUI.
- Use the playback controls to play, pause, skip, or log events.
- The application logs playback events to a CSV file automatically stored and saved in the same folder as the video.

## Dependencies
- VLC Python bindings
- Other necessary libraries as specified in `requirements.txt`

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for details.