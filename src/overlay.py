import os
import json
import time
from tkinter import Toplevel, Canvas, Label, Frame, Scale, HORIZONTAL, Button
from PIL import Image, ImageTk


class Overlay:
    """A transparent top-level overlay that displays a PNG over a video Frame.

    Features:
    - Toggle visibility
    - Opacity control (0.0..1.0)
    - Four draggable corner handles to freely warp the image (perspective)
    - Debounced rendering during dragging
    - Save/load corners+opacity to JSON
    """

    def __init__(self, root, video_frame, image_path, config_path=None):
        self.root = root
        self.video_frame = video_frame
        self.image_path = image_path
        self.overlay_toplevel = None
        self.canvas = None
        self.image_orig = None
        self.image_tk = None
        self.visible = False
        self.opacity = 0.6
        self.corners = None
        self._drag_idx = None
        self._corner_radius = 10
        self._render_after_id = None
        self.ctrl_frame = None
        self._ctrl_scale = None
        # allow per-video config path; fall back to workspace-level config
        if config_path:
            self._config_path = config_path
        else:
            self._config_path = os.path.join(os.path.dirname(__file__), 'overlay_config.json')
        self._load_image()
        self._load_config()

    def _load_image(self):
        try:
            if not os.path.exists(self.image_path):
                return
            self.image_orig = Image.open(self.image_path).convert('RGBA')
        except Exception:
            # failed to load image
            self.image_orig = None

    def toggle(self):
        if self.visible:
            self.hide()
        else:
            self.show()

    def show(self):
        if not self.image_orig:
            return
        if self.overlay_toplevel and self.overlay_toplevel.winfo_exists():
            self.visible = True
            self.overlay_toplevel.deiconify()
            self._render()
            return
        # create toplevel overlay
        top = Toplevel(self.root)
        top.overrideredirect(True)
        top.attributes('-topmost', True)
        # Transparent background trick (Windows): pick an unused color as transparent
        TRANSPARENT_COLOR = self._pick_transparent_color()
        canvas = Canvas(top, bg=TRANSPARENT_COLOR, highlightthickness=0)
        canvas.pack(fill='both', expand=True)
        # bind events
        canvas.bind('<ButtonPress-1>', self._on_press)
        canvas.bind('<B1-Motion>', self._on_motion)
        canvas.bind('<ButtonRelease-1>', self._on_release)
        canvas.bind('<Configure>', self._on_configure)

        self.overlay_toplevel = top
        self.canvas = canvas
        # no in-overlay controls by default (slider and Reset removed)
        self.ctrl_frame = None
        self._ctrl_scale = None
        try:
            top.attributes('-transparentcolor', TRANSPARENT_COLOR)
        except Exception:
            pass
        self.visible = True
        self._position()
        self._render()

    def hide(self):
        if self.overlay_toplevel and self.overlay_toplevel.winfo_exists():
            try:
                self.overlay_toplevel.withdraw()
            except Exception:
                pass
        self.visible = False

    def increase_opacity(self, delta=0.1):
        self.opacity = min(1.0, self.opacity + delta)
        self._render()
        self._save_config()

    def decrease_opacity(self, delta=0.1):
        self.opacity = max(0.0, self.opacity - delta)
        self._render()
        self._save_config()

    def _position(self):
        if not self.overlay_toplevel or not self.video_frame:
            return
        try:
            x = self.video_frame.winfo_rootx()
            y = self.video_frame.winfo_rooty()
            w = self.video_frame.winfo_width()
            h = self.video_frame.winfo_height()
            self.overlay_toplevel.geometry(f"{w}x{h}+{x}+{y}")
            if self.canvas:
                try:
                    self.canvas.config(width=w, height=h)
                except Exception:
                    pass
        except Exception:
            pass

    def _on_configure(self, event):
        # initialize corners if needed
        try:
            w = event.width
            h = event.height
            # if we have loaded corners but they look like they were saved for a different size
            # (e.g., coordinates outside the current canvas), discard them so we re-init
            if self.corners:
                out_of_bounds = False
                for (cx, cy) in self.corners:
                    if cx < -10 or cy < -10 or cx > w + 10 or cy > h + 10:
                        out_of_bounds = True
                        break
                if out_of_bounds:
                    # force reinitialize below
                    self.corners = None

            if not self.corners:
                # initialize corners so the PNG appears centered and not stretched to full canvas
                if self.image_orig:
                    img_w, img_h = self.image_orig.size
                    # fit image inside canvas preserving aspect ratio
                    scale = min(max(1e-6, w / img_w), max(1e-6, h / img_h))
                    disp_w = img_w * scale
                    disp_h = img_h * scale
                    left = (w - disp_w) / 2.0
                    top = (h - disp_h) / 2.0
                    self.corners = [
                        (left, top),
                        (left + disp_w, top),
                        (left + disp_w, top + disp_h),
                        (left, top + disp_h)
                    ]
                else:
                    self.corners = [(0, 0), (w, 0), (w, h), (0, h)]
            self._render_debounced()
        except Exception:
            pass

    def _on_press(self, event):
        if not self.corners:
            return
        x, y = event.x, event.y
        for i, (cx, cy) in enumerate(self.corners):
            # use corner radius for hit test (squared distance)
            if (x - cx) ** 2 + (y - cy) ** 2 <= (self._corner_radius) ** 2:
                self._drag_idx = i
                return

    def _on_motion(self, event):
        if self._drag_idx is None:
            return
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        nx = min(max(0, event.x), w)
        ny = min(max(0, event.y), h)
        self.corners[self._drag_idx] = (nx, ny)
        self._render_debounced()

    def _on_release(self, event):
        self._drag_idx = None
        # ensure final high-quality render
        self._render()
        self._save_config()

    def _render_debounced(self, delay=50):
        try:
            if self._render_after_id:
                try:
                    self.canvas.after_cancel(self._render_after_id)
                except Exception:
                    pass
            self._render_after_id = self.canvas.after(delay, lambda: (self._clear_render_id(), self._render()))
        except Exception:
            pass

    def _clear_render_id(self):
        self._render_after_id = None

    def _render(self):
        try:
            if not self.canvas or not self.image_orig or not self.corners:
                return
            cw = max(1, self.canvas.winfo_width())
            ch = max(1, self.canvas.winfo_height())
            # build source quad (full image) and destination quad (user corners)
            src_w, src_h = self.image_orig.size
            src_quad = [(0, 0), (src_w, 0), (src_w, src_h), (0, src_h)]
            dst_quad = self.corners
            # compute bounding box of destination quad so we transform only that region
            xs = [p[0] for p in dst_quad]
            ys = [p[1] for p in dst_quad]
            minx = int(min(xs))
            miny = int(min(ys))
            maxx = int(max(xs))
            maxy = int(max(ys))
            dst_w = max(1, maxx - minx)
            dst_h = max(1, maxy - miny)

            # If the bbox is the full canvas (or degenerate), fallback to previous behavior
            if dst_w >= cw and dst_h >= ch:
                coeffs = self._find_perspective_coeffs(src_quad, dst_quad)
                transformed = self.image_orig.transform((cw, ch), Image.PERSPECTIVE, coeffs, Image.BICUBIC)
                paste_x, paste_y = 0, 0
            else:
                # translate destination quad into bbox-local coordinates and transform into bbox size
                dst_local = [(x - minx, y - miny) for (x, y) in dst_quad]
                coeffs = self._find_perspective_coeffs(src_quad, dst_local)
                transformed = self.image_orig.transform((dst_w, dst_h), Image.PERSPECTIVE, coeffs, Image.BICUBIC)
                paste_x, paste_y = minx, miny

            # apply opacity to the transformed patch
            if 0.0 <= self.opacity < 1.0:
                alpha = transformed.split()[3].point(lambda p: int(p * self.opacity))
                transformed.putalpha(alpha)

            self.image_tk = ImageTk.PhotoImage(transformed)
            self.canvas.delete('overlay_image')
            # create_image at the bbox position so handles move the image as expected
            self.canvas.create_image(paste_x, paste_y, image=self.image_tk, anchor='nw', tags='overlay_image')
            # draw polygon (trapezoid) connecting the corners
            try:
                self.canvas.delete('overlay_poly')
                pts = []
                for (cx, cy) in self.corners:
                    pts.extend((cx, cy))
                # outline only, no fill so the PNG shows through
                self.canvas.create_polygon(*pts, outline='cyan', width=2, tags='overlay_poly')
            except Exception:
                pass
            # draw handles
            self.canvas.delete('overlay_handles')
            for idx, (cx, cy) in enumerate(self.corners):
                self.canvas.create_oval(cx - self._corner_radius, cy - self._corner_radius,
                                        cx + self._corner_radius, cy + self._corner_radius,
                                        fill='red', outline='black', tags=('overlay_handles', f'corner_{idx}'))
            # position control frame (if present) at top-right
            try:
                if self.ctrl_frame and self.ctrl_frame.winfo_exists():
                    w = self.canvas.winfo_width()
                    # put the control 10px from the top-right corner
                    cw = self.ctrl_frame.winfo_reqwidth()
                    ch = self.ctrl_frame.winfo_reqheight()
                    # place relative to the toplevel
                    # no control frame to place
            except Exception:
                pass
        except Exception:
            pass

    def _on_opacity_change(self, value):
        try:
            v = float(value)
            self.opacity = max(0.0, min(1.0, v / 100.0))
            # immediate low-cost render
            self._render_debounced(delay=10)
            self._save_config()
        except Exception:
            pass

    def _pick_transparent_color(self):
        """Pick a background color not present in the PNG so we can use it as the transparentcolor."""
        # candidates (RGB tuples) - magenta is common so try a few others first
        candidates = [(1, 1, 1), (2, 3, 5), (3, 127, 14), (250, 250, 250), (254, 1, 254), (255, 0, 255)]
        try:
            if not self.image_orig:
                return '#ff00ff'
            # collect present opaque colors (sample up to N pixels)
            data = self.image_orig.getdata()
            present = set()
            max_check = 20000
            cnt = 0
            for px in data:
                if cnt > max_check:
                    break
                cnt += 1
                if len(px) >= 4 and px[3] == 0:
                    continue
                present.add((px[0], px[1], px[2]))
            for r, g, b in candidates:
                if (r, g, b) not in present:
                    return f'#{r:02x}{g:02x}{b:02x}'
        except Exception:
            pass
        return '#ff00ff'

    def _reset(self):
        # reset corners to image-fit defaults and re-render
        try:
            if not self.overlay_toplevel or not self.canvas or not self.image_orig:
                return
            w = self.canvas.winfo_width()
            h = self.canvas.winfo_height()
            img_w, img_h = self.image_orig.size
            scale = min(max(1e-6, w / img_w), max(1e-6, h / img_h))
            disp_w = img_w * scale
            disp_h = img_h * scale
            left = (w - disp_w) / 2.0
            top = (h - disp_h) / 2.0
            self.corners = [
                (left, top),
                (left + disp_w, top),
                (left + disp_w, top + disp_h),
                (left, top + disp_h)
            ]
            # update slider position if present
            try:
                if self._ctrl_scale and self._ctrl_scale.winfo_exists():
                    self._ctrl_scale.set(int(self.opacity * 100))
            except Exception:
                pass
            self._render()
            self._save_config()
        except Exception:
            pass

    def _find_perspective_coeffs(self, src_pts, dst_pts):
        # same solver as earlier (8x8 gaussian elimination)
        try:
            matrix = []
            bx = []
            for (x_src, y_src), (x_dst, y_dst) in zip(src_pts, dst_pts):
                matrix.append([x_src, y_src, 1, 0, 0, 0, -x_dst * x_src, -x_dst * y_src])
                bx.append(x_dst)
                matrix.append([0, 0, 0, x_src, y_src, 1, -y_dst * x_src, -y_dst * y_src])
                bx.append(y_dst)
            M = [list(map(float, row)) for row in matrix]
            B = list(map(float, bx))
            n = 8
            for i in range(n):
                pivot = i
                for r in range(i, n):
                    if abs(M[r][i]) > abs(M[pivot][i]):
                        pivot = r
                if abs(M[pivot][i]) < 1e-12:
                    continue
                if pivot != i:
                    M[i], M[pivot] = M[pivot], M[i]
                    B[i], B[pivot] = B[pivot], B[i]
                div = M[i][i]
                M[i] = [mij / div for mij in M[i]]
                B[i] = B[i] / div
                for r in range(n):
                    if r == i:
                        continue
                    factor = M[r][i]
                    if abs(factor) < 1e-15:
                        continue
                    M[r] = [M[r][c] - factor * M[i][c] for c in range(n)]
                    B[r] = B[r] - factor * B[i]
            return tuple(B)
        except Exception:
            return (1, 0, 0, 0, 1, 0, 0, 0)

    def _save_config(self):
        try:
            data = {'corners': self.corners, 'opacity': self.opacity}
            with open(self._config_path, 'w', encoding='utf-8') as fh:
                json.dump(data, fh)
        except Exception:
            pass

    def _load_config(self):
        try:
            if not os.path.exists(self._config_path):
                return
            with open(self._config_path, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
            corners = data.get('corners')
            opacity = data.get('opacity')
            if corners and isinstance(corners, list) and len(corners) == 4:
                try:
                    self.corners = [tuple(map(float, c)) for c in corners]
                except Exception:
                    self.corners = None
            if opacity is not None:
                try:
                    self.opacity = float(opacity)
                except Exception:
                    pass
        except Exception:
            pass

