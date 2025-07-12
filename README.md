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

## Usage
- Open a video file using the GUI.
- Use the playback controls to play, pause, skip, or log events.
- The application logs playback events to a CSV file, which can be exported or cleared through the GUI.

## Dependencies
- VLC Python bindings
- Other necessary libraries as specified in `requirements.txt`

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for details.