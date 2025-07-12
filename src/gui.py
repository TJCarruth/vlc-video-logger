from tkinter import Tk, Frame, Button, Label, Text, Scrollbar, END, messagebox
import vlc
from csv_logger import CSVLogger

class VideoLoggerGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("VLC Video Logger")
        
        self.video_frame = Frame(master)
        self.video_frame.pack()

        self.play_button = Button(self.video_frame, text="Play", command=self.play_video)
        self.play_button.pack(side="left")

        self.pause_button = Button(self.video_frame, text="Pause", command=self.pause_video)
        self.pause_button.pack(side="left")

        self.skip_button = Button(self.video_frame, text="Skip 5s", command=self.skip_video)
        self.skip_button.pack(side="left")

        self.log_display = Text(master, height=10, width=50)
        self.log_display.pack()

        self.scrollbar = Scrollbar(master, command=self.log_display.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.log_display.config(yscrollcommand=self.scrollbar.set)

        self.logger = CSVLogger("video_log.csv")

        self.player = vlc.MediaPlayer()

    def play_video(self):
        self.player.play()
        self.logger.log_entry("Play", self.get_current_time())

    def pause_video(self):
        self.player.pause()
        self.logger.log_entry("Pause", self.get_current_time())

    def skip_video(self):
        self.player.set_time(self.player.get_time() + 5000)  # Skip forward 5 seconds
        self.logger.log_entry("Skip 5s", self.get_current_time())

    def get_current_time(self):
        return self.player.get_time()  # Returns time in milliseconds

    def update_log_display(self):
        self.log_display.delete(1.0, END)
        try:
            with open(self.logger.filename, 'r') as f:
                for line in f:
                    self.log_display.insert(END, line)
        except FileNotFoundError:
            messagebox.showerror("Error", "Log file not found.")

if __name__ == "__main__":
    root = Tk()
    app = VideoLoggerGUI(root)
    root.mainloop()