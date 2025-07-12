class VLCPlayer:
    def __init__(self, logger):
        import vlc
        self.logger = logger
        self.player = vlc.MediaPlayer()
        self.is_playing = False

    def load_video(self, path):
        self.player.set_media(vlc.Media(path))

    def play(self):
        if not self.is_playing:
            self.player.play()
            self.is_playing = True
            self.logger.log_entry("Play", self.get_current_timestamp())

    def pause(self):
        if self.is_playing:
            self.player.pause()
            self.is_playing = False
            self.logger.log_entry("Pause", self.get_current_timestamp())

    def stop(self):
        if self.is_playing:
            self.player.stop()
            self.is_playing = False
            self.logger.log_entry("Stop", self.get_current_timestamp())

    def skip_forward(self, seconds):
        self.player.set_time(self.player.get_time() + seconds * 1000)
        self.logger.log_entry(f"Skipped forward {seconds} seconds", self.get_current_timestamp())

    def skip_back(self, seconds):
        self.player.set_time(max(0, self.player.get_time() - seconds * 1000))
        self.logger.log_entry(f"Skipped back {seconds} seconds", self.get_current_timestamp())

    def get_current_timestamp(self):
        import datetime
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")