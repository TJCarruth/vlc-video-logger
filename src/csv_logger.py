class CSVLogger:
    # New column layout per user request
    DEFAULT_COLUMNS = ["timestamp", "class", "brake", "avoidance", "displacement", "state"]

    def __init__(self, filename, columns=None):
        self.filename = filename
        self.columns = columns or list(self.DEFAULT_COLUMNS)
        # Ensure file exists with header
        try:
            import os
            if not os.path.exists(self.filename):
                with open(self.filename, 'w') as f:
                    f.write(','.join(self.columns) + '\n')
        except Exception:
            pass

    def log_entry(self, key, timestamp):
        """
        Append a new log entry with the given key and timestamp to the CSV file.
        The CSV has a column for each of the tracked letters and a single 'numbers' column.
        Only recognized keys will be recorded; others are ignored.
        """
        try:
            header, rows = self._read_header_and_rows()
            rows = rows or []

            # mapping of input keys to columns
            key_map = {
                'j': 'class', 'k': 'class', 'l': 'class',
                'd': 'brake', 'f': 'brake',
                'b': 'avoidance',
                'y': 'displacement'
            }

            # find existing row with same timestamp
            found = False
            for i, row in enumerate(rows):
                parts = [p for p in row.split(',')]
                if not parts:
                    continue
                existing_ts = parts[0].strip()
                if existing_ts == timestamp:
                    found = True
                    while len(parts) < len(self.columns):
                        parts.append('')
                    if key.isdigit():
                        parts[self.columns.index('state')] = key
                    else:
                        k = key.lower()
                        if k in key_map:
                            col = key_map[k]
                            idx = self.columns.index(col)
                            cur = parts[idx].strip()
                            # toggle: if same letter present, remove it; otherwise set to new letter
                            if cur == k:
                                parts[idx] = ''
                            else:
                                parts[idx] = k
                    rows[i] = ','.join([p for p in parts])
                    break

            if not found:
                row = {col: '' for col in self.columns}
                row['timestamp'] = timestamp
                if key.isdigit():
                    row['state'] = key
                else:
                    k = key.lower()
                    if k in key_map:
                        col = key_map[k]
                        row[col] = k
                    else:
                        return
                values = [row.get(col, '') for col in self.columns]
                rows.append(','.join(values))

            # write back header + rows
            with open(self.filename, 'w') as f:
                if header:
                    f.write(header + '\n')
                else:
                    f.write(','.join(self.columns) + '\n')
                for r in rows:
                    f.write(r + '\n')
        except Exception:
            pass

    def _read_header_and_rows(self):
        import os
        if not os.path.exists(self.filename):
            return None, []
        with open(self.filename, 'r') as f:
            lines = [line.rstrip('\n') for line in f if line.strip()]
        if not lines:
            return None, []
        header = lines[0]
        rows = lines[1:]
        return header, rows

    def sort_log_file(self):
        """
        Sort the CSV data rows by timestamp (first column) while preserving the header.
        """
        import re
        try:
            header, rows = self._read_header_and_rows()
            def parse_ts(row):
                parts = row.split(',')
                if not parts:
                    return float('inf')
                ts = parts[0].strip()
                # Timestamp format: HH:MM:SS:ms or similar
                parts_ts = re.split(r'[:]', ts)
                try:
                    h = int(parts_ts[0])
                    m = int(parts_ts[1])
                    s = int(parts_ts[2])
                    ms = int(parts_ts[3]) if len(parts_ts) > 3 else 0
                    return h * 3600 + m * 60 + s + ms / 1000.0
                except Exception:
                    return float('inf')
            rows.sort(key=parse_ts)
            with open(self.filename, 'w') as f:
                if header:
                    f.write(header + '\n')
                for r in rows:
                    f.write(r + '\n')
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
                # reset file to header only
                with open(self.filename, 'w') as f:
                    f.write(','.join(self.columns) + '\n')
                gui.update_log_display()
            except Exception:
                pass

    def undo(self, gui):
        """
        Undo the last log entry (or highlighted entry) in the GUI, supporting undo/redo stacks.
        """
        highlight_next = None
        try:
            header, rows = self._read_header_and_rows()
            # rows correspond to GUI lines (we display rows without header)
            if not rows:
                gui.update_log_display(highlight_line=None)
                return
            ranges = gui.log_text.tag_ranges('highlight')
            if ranges:
                start = ranges[0]
                line_number = int(str(start).split('.')[0])
                if 1 <= line_number <= len(rows):
                    removed_entry = rows.pop(line_number - 1)
                    removed_index = line_number - 1
                    gui.undo_stack.append((removed_entry + '\n', removed_index))
                    gui.redo_stack.clear()
                    # write back header + rows
                    with open(self.filename, 'w') as f:
                        if header:
                            f.write(header + '\n')
                        for r in rows:
                            f.write(r + '\n')
                    self.sort_log_file()
                    if line_number > 1:
                        highlight_next = line_number - 1
                    elif rows:
                        highlight_next = 1
                    else:
                        highlight_next = None
            else:
                # remove last data row
                removed_entry = rows.pop(-1)
                removed_index = len(rows)
                gui.undo_stack.append((removed_entry + '\n', removed_index))
                gui.redo_stack.clear()
                with open(self.filename, 'w') as f:
                    if header:
                        f.write(header + '\n')
                    for r in rows:
                        f.write(r + '\n')
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
                # entry contains trailing newline from undo stack
                entry = entry.rstrip('\n')
                header, rows = self._read_header_and_rows()
                insert_at = min(index, len(rows))
                rows.insert(insert_at, entry)
                with open(self.filename, 'w') as f:
                    if header:
                        f.write(header + '\n')
                    for r in rows:
                        f.write(r + '\n')
                self.sort_log_file()
                # find highlight line in data rows
                highlight_line = None
                for idx, line in enumerate(rows, 1):
                    if line.strip() == entry.strip():
                        highlight_line = idx
                        break
                gui.redo_stack.append((entry + '\n', index))
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
                entry = entry.rstrip('\n')
                header, rows = self._read_header_and_rows()
                for i, line in enumerate(rows):
                    if line.strip() == entry.strip():
                        del rows[i]
                        break
                with open(self.filename, 'w') as f:
                    if header:
                        f.write(header + '\n')
                    for r in rows:
                        f.write(r + '\n')
                self.sort_log_file()
                gui.undo_stack.append((entry + '\n', index))
                highlight_line = index if index > 0 else 1
                gui.update_log_display(highlight_line=highlight_line)
            except Exception:
                pass

    def search_entries(self, search_term, gui):
        """
        Highlight all log entries containing the search_term (case-insensitive) in the GUI log display.
        """
        import os
        if not os.path.exists(self.filename):
            print("No log file found.")
            return
        highlight_lines = []
        header, rows = self._read_header_and_rows()
        for idx, line in enumerate(rows, 1):
            if search_term.lower() in line.lower():
                highlight_lines.append(idx)
        gui.update_log_display(highlight_lines=highlight_lines)
        if not highlight_lines:
            print(f"No entries found containing: {search_term}")