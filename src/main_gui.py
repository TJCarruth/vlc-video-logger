import os
import threading
from tkinter import Tk, Button, Label, Entry, filedialog, StringVar, Frame, Text, Scrollbar, RIGHT, Y, LEFT, BOTH, simpledialog, messagebox, Toplevel
import vlc
from csv_logger import CSVLogger
from datetime import timedelta
from PIL import Image, ImageTk

class CarCounterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Car Counter")
        # On Windows, initialize COM for audio output (prevents mmdevice errors)
        if os.name == 'nt':
            try:
                import ctypes
                ctypes.windll.ole32.CoInitialize(None)
            except Exception:
                pass
        self.paused = True
        self.speed = 1.0
        self.start_offset = timedelta()
        self.logger = None
        self.video_path = ""
        self.undo_stack = []
        self.redo_stack = []
        self.vlc_instance = vlc.Instance()
        self.player = None

        # --- GUI Layout ---
        main_frame = Frame(root)
        main_frame.pack(fill=BOTH, expand=True)

        # Log display (right side)
        log_frame = Frame(main_frame)
        # Keep log_frame a fixed-width column on the right so headers fit on one line;
        # video_frame will expand when the main window is resized.
        log_frame.pack(side=RIGHT, fill=Y, padx=10, pady=10)
        # Allow horizontal scrolling and disable wrapping so headers show on one line
        self.log_text = Text(log_frame, width=80, height=25, state='disabled', wrap='none')
        self.log_text.pack(side=LEFT, fill=Y)
        v_scrollbar = Scrollbar(log_frame, command=self.log_text.yview)
        v_scrollbar.pack(side=RIGHT, fill=Y)
        self.log_text['yscrollcommand'] = v_scrollbar.set
        h_scrollbar = Scrollbar(log_frame, command=self.log_text.xview, orient='horizontal')
        h_scrollbar.pack(side='bottom', fill='x')
        self.log_text['xscrollcommand'] = h_scrollbar.set
        # bind click handler so clicking entries selects and seeks
        self.log_text.bind('<Button-1>', self.on_log_click)

        # Video display (left side)
        self.frame_width = 640
        self.frame_height = 480
        self.video_frame = Frame(main_frame, bg='black', width=self.frame_width, height=self.frame_height)
        self.video_frame.pack_propagate(False)
        # Let the video_frame take available space when window is resized
        self.video_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=10, pady=10)

        # Controls container (vertical stack of buttons and controls)
        controls_container = Frame(main_frame)
        controls_container.pack(side=LEFT, fill=Y, padx=5, pady=10)
        controls_container.pack(fill='y', expand=True)

        # --- Control Buttons ---
        self.open_btn = Button(controls_container, text="Open Video", command=self.open_video)
        self.open_btn.pack(side='top', pady=(0, 16), fill='x')
        # Frame rate entry. Used to calculate frame-by-frame stepping.
        fr_label = Label(controls_container, text="Frame Rate (fps):")
        fr_label.pack(side='top', pady=(0, 2), fill='x')
        self.fps_var = StringVar(value="24")
        self.fps_entry = Entry(controls_container, textvariable=self.fps_var, width=8)
        self.fps_entry.pack(side='top', pady=(0, 8), fill='x')

        # Keybindings info label (replaces playback buttons)
        keybinds_text = (
            "Video Controls:\n"
            "  Space  : Play/Pause\n"
            "  = / -  : Speed Up / Down\n"
            "  , / .  : Prev / Next Frame\n"
            "  ; / '  : Skip -5s / +5s\n"
            "  [ / ]  : Skip -5min / +5min\n"
            "  { / }  : Skip -1hr / +1hr\n"
            "\nLog Controls:\n"
            "  Backspace       : Delete Last Entry\n"
            "  Ctrl+Z / Ctrl+Y : Undo / Redo\n"
            "  Ctrl+f          : Search Log\n"
            "  jkl             : passenger, truck, motorcycle\n"
            "  d, f            : brake before/after TPRS\n"
            "  b               : erratic behavior\n"
            "  y               : TPRS movement\n"
        )

        self.status_label = Label(controls_container, text=keybinds_text, anchor='w', justify='left', font=("Courier", 10))
        self.status_label.pack(side='top', pady=(8, 8), fill='x')

        # Separate label to display current playback speed (updates when speed changes)
        self.playback_speed_label = Label(controls_container, text=f"Speed: x{self.speed:.1f}", anchor='w', justify='left', font=("Courier", 10, 'bold'))
        self.playback_speed_label.pack(side='top', pady=(2, 8), fill='x')

        # Notes label and editable text field
        notes_label = Label(controls_container, text="Notes:")
        notes_label.pack(side='top', anchor='w', padx=2)
        self.notes_text = Text(controls_container, height=1, width=24, wrap='word')
        self.notes_text.pack(side='top', fill='x', padx=2, pady=(0, 8))
        # Pre-fill with a legend for classification and flags
        legend_text = (
            "- classification -\n"
            "j : passenger vehicle\n"
            "k : large truck\n"
            "l : motorcycles\n"
            "\n"
            "- flags -\n"
            "d : brake lights on before TPRS\n"
            "f : brake lights on after TPRS\n"
            "b : erratic behavior"
        )
 #       self.notes_text.insert('1.0', legend_text)

        def _auto_resize_notes(event=None):
            lines = int(self.notes_text.index('end-1c').split('.')[0])
            self.notes_text.config(height=lines)

        self.notes_text.bind('<KeyRelease>', _auto_resize_notes)
        # Initial resize to fit pre-filled text
        _auto_resize_notes()

        log_btn_frame = Frame(controls_container)
        log_btn_frame.pack(side='top', pady=(40, 16), fill='x')
        # self.export_btn = Button(log_btn_frame, text="Export Log", command=lambda: self.logger.export_log(self) if self.logger else None)
        # self.export_btn.pack(side='top', pady=2, fill='x')
        # self.clear_btn = Button(log_btn_frame, text="Clear Log", command=lambda: self.logger.clear_log(self) if self.logger else None)
        # self.clear_btn.pack(side='top', pady=2, fill='x')
        # undo_frame = Frame(log_btn_frame)
        # undo_frame.pack(fill='x', pady=1)
        # Button(undo_frame, text="Undo", command=lambda: self.logger.restore_last_undo(self) if self.logger else None).pack(side='left', expand=True, fill='x')
        # Button(undo_frame, text="Redo", command=lambda: self.logger.redo(self) if self.logger else None).pack(side='left', expand=True, fill='x')
        # Button(log_btn_frame, text="Search Log", command=self.prompt_search_log).pack(side='top', pady=2, fill='x')
        # Button(log_btn_frame, text="Delete Entry", command=lambda: self.logger.undo(self) if self.logger else None).pack(side='bottom', pady=2, fill='x')

        Button(controls_container, text="Save and Quit", command=self.root.quit).pack(side='bottom', pady=16, fill='x')

        self.root.update_idletasks()
        # allow resizing; set a reasonable minimum size
        try:
            self.root.minsize(800, 480)
        except Exception:
            pass
        self.root.resizable(True, True)

        # --- Keyboard Shortcuts ---
        self.root.bind('<Control-f>', lambda e: self.prompt_search_log())
        self.root.bind('<space>', lambda e: self.toggle_play())
        self.root.bind('<KeyPress-equal>', lambda e: self.speed_up())
        self.root.bind('<KeyPress-minus>', lambda e: self.slow_down())
        self.root.bind('<comma>', lambda e: self.prev_frame())
        self.root.bind('<period>', lambda e: self.next_frame())
        self.root.bind('<semicolon>', lambda e: self.skip_seconds(-5))
        self.root.bind("'", lambda e: self.skip_seconds(5))
        self.root.bind('[', lambda e: self.skip_seconds(-300))
        self.root.bind(']', lambda e: self.skip_seconds(300))
        self.root.bind('{', lambda e: self.skip_seconds(-3600))
        self.root.bind('}', lambda e: self.skip_seconds(3600))
        self.root.bind('<Escape>', lambda e: self.root.quit())

        # --- Global key bindings for logging and undo/redo (use bind_all so keys are captured regardless of focus)
        for char in 'jkldbfy':
            self.root.bind_all(f'<KeyPress-{char}>', self.log_key_event)
            self.root.bind_all(f'<KeyPress-{char.upper()}>', self.log_key_event)
        for digit in '0123456789':
            self.root.bind_all(f'<KeyPress-{digit}>', self.log_key_event)
        self.root.bind_all('<BackSpace>', lambda e: self.logger.undo(self) if self.logger else None)
        self.root.bind_all('<Control-z>', lambda e: self.logger.restore_last_undo(self) if self.logger else None)
        self.root.bind_all('<Control-y>', lambda e: self.logger.redo(self) if self.logger else None)
        
    def next_frame(self):
        """
        Advances the video by one frame using VLC's next_frame().
        """
        if self.player:
            self.player.next_frame()
            self.paused = True

    def prev_frame(self):
        """
        Seeks back by one frame's worth of ms, then steps forward to the next frame for best accuracy.
        """
        if not self.player:
            return
        try:
            fps = float(self.fps_var.get())
            if fps <= 0:
                fps = 24.0
        except Exception:
            fps = 24.0
        ms_per_frame = int(1000 / fps)
        cur_ms = self.player.get_time()
        # Seek back 1.5 frames to ensure we land before the previous frame
        seek_ms = max(0, cur_ms - int(ms_per_frame * 1.5))
        self.player.set_time(seek_ms)
        self.player.next_frame()
        self.paused = True
        self.log_text.bind('<Button-1>', self.on_log_click)

## GUI Functions ##########################################################

    def open_video(self, event=None):
        """
        Opens a file dialog for the user to select a video file. Initializes VLC player and logger,
        prompts for the video start time, and prepares the player.
        """
        path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.avi *.mov")])
        if path:
            self.video_path = path
            if self.player:
                self.player.stop()
            self.player = self.vlc_instance.media_player_new()
            media = self.vlc_instance.media_new(path)
            self.player.set_media(media)
            # Set the video output to the Tkinter Frame's window handle (platform-specific)
            self.root.update_idletasks()
            handle = self.video_frame.winfo_id()
            if os.name == "nt":
                self.player.set_hwnd(handle)
            else:
                self.player.set_xwindow(handle)
            csv_path = os.path.splitext(path)[0] + ".csv"
            self.logger = CSVLogger(csv_path)
            self.paused = True
            self.update_log_display()
            # Prompt for start time
            video_basename = os.path.splitext(os.path.basename(path))[0]
            prompt = "Enter the video start time (HH:MM:SS):"
            start_time_str = simpledialog.askstring("Start Time", prompt, initialvalue="00:00:00", parent=self.root)
            offset = self.parse_start_time(start_time_str) if start_time_str else None
            self.start_offset = offset if offset is not None else timedelta()
            # update only the playback speed label (do not overwrite legend/status text)
            try:
                self.playback_speed_label.config(text=f"Speed: x{self.speed:.1f}")
            except Exception:
                pass
            # Start playback to force video output, then pause if needed
            self.player.play()
            self.root.after(200, self.player.pause)

    def update_log_display(self, highlight_line=None, highlight_lines=None):
        """
        Updates the log display area with the contents of the log file. Optionally highlights a specific line or lines.
        """
        # Read CSV rows (skip header) and filter out invalid/placeholder rows
        displayed_rows = []
        if self.logger:
            try:
                header, rows = self.logger._read_header_and_rows()
                for r in rows:
                    # skip rows with negative or placeholder timestamps like '-1:59:59:999'
                    parts = r.split(',')
                    if not parts:
                        continue
                    ts = parts[0].strip()
                    if ts.startswith('-'):
                        continue
                    displayed_rows.append(r)
            except Exception:
                displayed_rows = []

        # Build content from displayed rows only (no header)
        if displayed_rows:
            content = '\n'.join(displayed_rows)
        else:
            content = ''

        # adjust width to fit first data row; shrink height to show a single data row
        try:
            first_line = displayed_rows[0] if displayed_rows else ''
            needed_chars = max(40, len(first_line) + 2)
            needed_chars = min(160, needed_chars)
            self.log_text.config(width=needed_chars, height=1)
        except Exception:
            pass

        self.log_text.config(state='normal')
        self.log_text.delete(1.0, 'end')
        if content:
            self.log_text.insert('end', content)
        self.log_text.tag_remove('highlight', '1.0', 'end')

        # If highlight_lines is provided, highlight those data rows (display lines equal data indices)
        if highlight_lines:
            for line_num in highlight_lines:
                self.log_text.tag_add('highlight', f'{line_num}.0', f'{line_num}.end')
            self.log_text.tag_configure('highlight', background='yellow')
            self.log_text.see(f'{highlight_lines[0]}.0')
        elif highlight_line is not None:
            self.log_text.tag_add('highlight', f'{highlight_line}.0', f'{highlight_line}.end')
            self.log_text.tag_configure('highlight', background='yellow')
            self.log_text.see(f'{highlight_line}.0')

        self.log_text.config(state='disabled')

    def on_log_click(self, event):
        """
        Handles clicks on the log display. Highlights the clicked line and seeks the video to the corresponding timestamp.
        """
        self.log_text.tag_remove('highlight', '1.0', 'end')
        index = self.log_text.index(f'@{event.x},{event.y}')
        line_number = int(index.split('.')[0])
        # Since the viewer shows only data rows (no header) and each displayed row maps to
        # a data row index starting at 1, the clicked line_number directly corresponds to data row.
        data_row = line_number
        if data_row < 1:
            return
        self.log_text.tag_add('highlight', f'{data_row}.0', f'{data_row}.end')
        self.log_text.tag_configure('highlight', background='yellow')
        line_content = self.log_text.get(f'{data_row}.0', f'{data_row}.end').strip()
        if ',' in line_content:
            timestamp_str = line_content.split(',')[0].strip()
        elif ':' in line_content:
            timestamp_str = line_content.split(':', 1)[1].strip()
        else:
            return
        try:
            parts = timestamp_str.split(':')
            if len(parts) >= 3:
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = int(parts[2])
                ms = int(parts[3]) if len(parts) > 3 else 0
                total_seconds = hours * 3600 + minutes * 60 + seconds + ms / 1000.0
                offset_seconds = self.start_offset.total_seconds() if self.start_offset else 0
                video_seconds = max(0, total_seconds - offset_seconds)
                if self.player:
                    self.player.set_time(int(video_seconds * 1000))
                    self.paused = True
        except Exception:
            pass

    def log_key_event(self, event):
        """
        Handles key press events for logging. Logs the key and current timestamp to the CSV, updates the log display,
        and highlights the new entry.
        """
        key = event.char
        if not key:
            return
        ms = self.player.get_time() if self.player else 0
        timestamp_str = self.format_timestamp(ms, self.start_offset)
        if self.logger:
            # Logger expects key then timestamp order in previous implementation; new CSVLogger.signature is (key, timestamp)
            # Our CSVLogger will place the letter in its column or the digit into numbers column
            self.logger.log_entry(key, timestamp_str)
            self.logger.sort_log_file()
            highlight_line = None
            try:
                header, rows = self.logger._read_header_and_rows()
                for idx, row in enumerate(rows, 1):
                    parts = [p.strip() for p in row.split(',')]
                    if not parts:
                        continue
                    ts = parts[0]
                    if ts == timestamp_str:
                        # highlight the first matching timestamp
                        highlight_line = idx
                        break
            except Exception:
                highlight_line = None
            self.update_log_display(highlight_line=highlight_line)
    def toggle_play(self):
        if not self.player:
            return
        if self.player.is_playing():
            self.player.pause()
            self.paused = True
        else:
            self.player.play()
            self.paused = False

    def speed_up(self):
        if not self.player:
            return
        self.speed = min(self.speed + 0.25, 4.0)
        self.player.set_rate(self.speed)
        # update the separate playback speed label
        self.playback_speed_label.config(text=f"Speed: x{self.speed:.1f}")

    def slow_down(self):
        if not self.player:
            return
        self.speed = max(self.speed - 0.25, 0.25)
        self.player.set_rate(self.speed)
        # update the separate playback speed label
        self.playback_speed_label.config(text=f"Speed: x{self.speed:.1f}")

    def skip_seconds(self, seconds):
        if not self.player:
            return
        cur_ms = self.player.get_time()
        new_ms = max(0, cur_ms + int(seconds * 1000))
        self.player.set_time(new_ms)

    @staticmethod
    def parse_start_time(time_str):
        try:
            parts = [int(p) for p in time_str.strip().split(":")]
            if len(parts) == 3:
                return timedelta(hours=parts[0], minutes=parts[1], seconds=parts[2])
            elif len(parts) == 2:
                return timedelta(minutes=parts[0], seconds=parts[1])
            elif len(parts) == 1:
                return timedelta(seconds=parts[0])
        except Exception:
            return timedelta()
        return timedelta()

    @staticmethod
    def format_timestamp(ms, offset):
        total_ms = int(ms)
        if offset:
            total_ms += int(offset.total_seconds() * 1000)
        hours = total_ms // 3600000
        minutes = (total_ms % 3600000) // 60000
        seconds = (total_ms % 60000) // 1000
        ms_part = total_ms % 1000
        return f"{hours:02}:{minutes:02}:{seconds:02}:{ms_part:03}"

    def prompt_search_log(self):
        """
        Prompts the user for a search term and highlights all matching entries in the log display.
        This, and the .search_entries method in CSVLogger, are very basic. Use excel or similar for more advanced searching.
        """
        search_term = simpledialog.askstring("Search Log", "Enter search term:", parent=self.root)
        if search_term and self.logger:
            self.logger.search_entries(search_term, self)

    def show_instructions(self):
        """
        Opens a new window and displays the contents of README.md as instructions for the user.
        """
        instructions_win = Toplevel(self.root)
        instructions_win.title("Instructions")
        instructions_win.geometry("700x600")
        text_widget = Text(instructions_win, wrap='word')
        text_widget.pack(fill='both', expand=True)
        scrollbar = Scrollbar(text_widget, command=text_widget.yview)
        text_widget['yscrollcommand'] = scrollbar.set
        scrollbar.pack(side=RIGHT, fill=Y)
        try:
            with open("README.md", "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            content = f"Could not load instructions: {e}"
        text_widget.insert('1.0', content)
        text_widget.config(state='disabled')

if __name__ == "__main__":
    root = Tk()
    app = CarCounterGUI(root)
    root.mainloop()

    