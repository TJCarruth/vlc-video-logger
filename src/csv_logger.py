class CSVLogger:
    def __init__(self, filename):
        self.filename = filename

    def log_entry(self, key, timestamp):
        """
        Append a new log entry with the given key and timestamp to the CSV file.
        """
        with open(self.filename, 'a') as file:
            file.write(f"{timestamp}, {key}\n")

    def sort_log_file(self):
        """
        Sort the log file entries by timestamp in ascending order.
        """
        import re
        try:
            with open(self.filename, 'r') as f:
                lines = [line for line in f if line.strip()]
            def parse_ts(line):
                if ',' in line:
                    ts = line.split(',')[0].strip()
                elif ':' in line:
                    ts = line.split(':', 1)[1].strip()
                else:
                    return float('inf')
                parts = re.split(r'[:]', ts)
                try:
                    h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
                    ms = int(parts[3]) if len(parts) > 3 else 0
                    return h * 3600 + m * 60 + s + ms / 1000.0
                except Exception:
                    return float('inf')
            lines.sort(key=parse_ts)
            with open(self.filename, 'w') as f:
                f.writelines(lines)
        except Exception:
            pass

    def export_log(self, gui):
        """
        Export the current log file to a user-selected location using a file dialog.
        """
        import os
        from tkinter import filedialog
        if not self.filename:
            return
        if hasattr(gui, 'video_path') and gui.video_path:
            base = os.path.splitext(os.path.basename(gui.video_path))[0]
            suggested_name = base + ".csv"
        else:
            suggested_name = "log.csv"
        export_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=suggested_name
        )
        if export_path:
            try:
                with open(self.filename, 'r') as src, open(export_path, 'w') as dst:
                    dst.write(src.read())
            except Exception:
                pass

    def clear_log(self, gui):
        """
        Clear all entries from the log file after user confirmation, and update the GUI log display.
        """
        from tkinter import messagebox
        if not self.filename:
            return
        confirm = messagebox.askyesno("Clear Log", "Are you sure you want to clear the log? This cannot be undone.")
        if confirm:
            try:
                with open(self.filename, 'w') as f:
                    f.write("")
                gui.update_log_display()
            except Exception:
                pass

    def undo(self, gui):
        """
        Undo the last log entry (or highlighted entry) in the GUI, supporting undo/redo stacks.
        """
        highlight_next = None
        try:
            ranges = gui.log_text.tag_ranges('highlight')
            if ranges:
                start = ranges[0]
                line_number = int(str(start).split('.')[0])
                with open(self.filename, 'r') as f:
                    lines = [line for line in f if line.strip()]
                if 1 <= line_number <= len(lines):
                    removed_entry = lines[line_number - 1]
                    removed_index = line_number - 1
                    gui.undo_stack.append((removed_entry, removed_index))
                    gui.redo_stack.clear()
                    del lines[line_number - 1]
                    with open(self.filename, 'w') as f:
                        f.writelines(lines)
                    self.sort_log_file()
                    if line_number > 1:
                        highlight_next = line_number - 1
                    elif lines:
                        highlight_next = 1
                    else:
                        highlight_next = None
            else:
                with open(self.filename, 'r') as f:
                    lines = [line for line in f if line.strip()]
                if lines:
                    removed_entry = lines[-1]
                    removed_index = len(lines) - 1
                    gui.undo_stack.append((removed_entry, removed_index))
                    gui.redo_stack.clear()
                self.undo_last_entry()
                self.sort_log_file()
        except Exception:
            pass
        gui.paused = True
        gui.update_log_display(highlight_line=highlight_next)

    def restore_last_undo(self, gui):
        """
        Restore the last undone log entry from the undo stack and update the GUI log display.
        """
        if gui.undo_stack:
            try:
                entry, index = gui.undo_stack.pop()
                with open(self.filename, 'r') as f:
                    lines = [line for line in f if line.strip()]
                insert_at = min(index, len(lines))
                lines.insert(insert_at, entry)
                with open(self.filename, 'w') as f:
                    f.writelines(lines)
                self.sort_log_file()
                with open(self.filename, 'r') as f:
                    sorted_lines = [line for line in f if line.strip()]
                highlight_line = None
                for idx, line in enumerate(sorted_lines, 1):
                    if line.strip() == entry.strip():
                        highlight_line = idx
                        break
                gui.redo_stack.append((entry, index))
                gui.update_log_display(highlight_line=highlight_line)
            except Exception:
                pass

    def redo(self, gui):
        """
        Redo the last undone log entry from the redo stack and update the GUI log display.
        """
        if gui.redo_stack:
            try:
                entry, index = gui.redo_stack.pop()
                with open(self.filename, 'r') as f:
                    lines = [line for line in f if line.strip()]
                for i, line in enumerate(lines):
                    if line.strip() == entry.strip():
                        del lines[i]
                        break
                with open(self.filename, 'w') as f:
                    f.writelines(lines)
                self.sort_log_file()
                gui.undo_stack.append((entry, index))
                highlight_line = index if index > 0 else 1
                gui.update_log_display(highlight_line=highlight_line)
            except Exception:
                pass

    def search_entries(self, search_term, gui):
        """
        Highlight all log entries containing the search_term (case-insensitive) in the GUI log display.
        """
        if not os.path.exists(self.filename):
            print("No log file found.")
            return
        highlight_lines = []
        with open(self.filename, 'r') as f:
            for idx, line in enumerate(f, 1):
                if search_term.lower() in line.lower():
                    highlight_lines.append(idx)
        gui.update_log_display(highlight_lines=highlight_lines)
        if not highlight_lines:
            print(f"No entries found containing: {search_term}")