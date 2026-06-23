"""
Music Player — Python (Local Version)
--------------------------------------
این فایل نسخه لوکال موزیک پلیره که با pygame و tkinter کار می‌کنه.
برای اجرا:
    pip install pygame
    python player.py
"""

import os
import time
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import pygame
    pygame.mixer.init()
    PYGAME_OK = True
except ImportError:
    PYGAME_OK = False


class MusicPlayer:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Music Player")
        self.root.resizable(False, False)
        self.root.configure(bg="#0d0d0f")

        self.file_path: str = ""
        self.is_playing: bool = False
        self.is_paused: bool = False
        self.is_repeat: bool = False
        self.duration: float = 0.0
        self._progress_job = None

        if not PYGAME_OK:
            messagebox.showerror(
                "pygame پیدا نشد",
                "لطفاً pygame را نصب کنید:\n\n  pip install pygame",
            )
            root.destroy()
            return

        self._build_ui()
        self._check_end_loop()

    # ------------------------------------------------------------------ UI --

    def _build_ui(self):
        BG      = "#0d0d0f"
        SURFACE = "#16161a"
        CARD    = "#1e1e24"
        ACCENT  = "#7c6af7"
        TEXT    = "#e8e8f0"
        SUB     = "#8888a0"

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Dark.TButton",
            background=CARD, foreground=TEXT,
            borderwidth=1, relief="flat",
            font=("Segoe UI", 10),
            padding=8,
        )
        style.map("Dark.TButton",
                  background=[("active", ACCENT)],
                  foreground=[("active", "#ffffff")])

        style.configure(
            "Accent.TButton",
            background=ACCENT, foreground="#ffffff",
            borderwidth=0, relief="flat",
            font=("Segoe UI", 11, "bold"),
            padding=12,
        )
        style.map("Accent.TButton", background=[("active", "#a78bfa")])

        # ---- outer frame ----
        outer = tk.Frame(self.root, bg=SURFACE, padx=24, pady=20)
        outer.pack(fill="both", expand=True)

        # ---- title ----
        tk.Label(
            outer, text="MUSIC PLAYER",
            bg=SURFACE, fg=ACCENT,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w")

        # ---- file name display ----
        self.lbl_track = tk.Label(
            outer, text="هیچ فایلی انتخاب نشده",
            bg=SURFACE, fg=TEXT,
            font=("Segoe UI", 13, "bold"),
            wraplength=340, justify="right",
        )
        self.lbl_track.pack(pady=(14, 2))

        self.lbl_sub = tk.Label(
            outer, text="فایل صوتی را انتخاب کنید",
            bg=SURFACE, fg=SUB,
            font=("Segoe UI", 9),
        )
        self.lbl_sub.pack()

        # ---- progress bar ----
        prog_frame = tk.Frame(outer, bg=SURFACE)
        prog_frame.pack(fill="x", pady=(16, 4))

        self.progress_var = tk.DoubleVar()
        self.progress_scale = tk.Scale(
            prog_frame,
            variable=self.progress_var,
            from_=0, to=100,
            orient="horizontal",
            showvalue=False,
            bg=SURFACE, fg=ACCENT,
            troughcolor="#2a2a32",
            highlightthickness=0,
            sliderrelief="flat",
            command=self._on_seek,
        )
        self.progress_scale.pack(fill="x")

        time_row = tk.Frame(prog_frame, bg=SURFACE)
        time_row.pack(fill="x")
        self.lbl_current = tk.Label(time_row, text="0:00", bg=SURFACE, fg=SUB, font=("Segoe UI", 9))
        self.lbl_current.pack(side="left")
        self.lbl_duration = tk.Label(time_row, text="0:00", bg=SURFACE, fg=SUB, font=("Segoe UI", 9))
        self.lbl_duration.pack(side="right")

        # ---- main controls ----
        ctrl = tk.Frame(outer, bg=SURFACE)
        ctrl.pack(pady=(12, 0))

        btn_cfg = [
            ("⏮",  self.rewind,       "Dark.TButton"),
            ("⏹",  self.stop,         "Dark.TButton"),
            ("▶ / ⏸", self.toggle_play, "Accent.TButton"),
            ("⏭",  self.fast_forward, "Dark.TButton"),
            ("🔁",  self.toggle_repeat,"Dark.TButton"),
        ]

        self.btn_repeat_widget = None
        for i, (label, cmd, style_name) in enumerate(btn_cfg):
            b = ttk.Button(ctrl, text=label, command=cmd, style=style_name, width=8)
            b.grid(row=0, column=i, padx=4, pady=4)
            if label == "🔁":
                self.btn_repeat_widget = b

        # ---- select file ----
        ttk.Button(
            outer,
            text="📂  انتخاب فایل صوتی",
            command=self.select_file,
            style="Dark.TButton",
            width=36,
        ).pack(pady=(14, 0), fill="x")

        # ---- status ----
        self.lbl_status = tk.Label(
            outer, text="منتظر فایل...",
            bg=SURFACE, fg=SUB,
            font=("Segoe UI", 9),
        )
        self.lbl_status.pack(pady=(8, 0))

    # ----------------------------------------------------------- helpers --

    def _fmt(self, seconds: float) -> str:
        if seconds < 0 or seconds != seconds:   # nan guard
            return "0:00"
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m}:{s:02d}"

    def _set_status(self, msg: str, color: str = "#8888a0"):
        self.lbl_status.configure(text=msg, fg=color)

    def _update_progress(self):
        if self.is_playing and not self.is_paused:
            pos_ms = pygame.mixer.music.get_pos()
            if pos_ms >= 0:
                pos_s = pos_ms / 1000
                self.lbl_current.configure(text=self._fmt(pos_s))
                if self.duration > 0:
                    pct = min((pos_s / self.duration) * 100, 100)
                    self.progress_var.set(pct)
        self._progress_job = self.root.after(500, self._update_progress)

    def _check_end_loop(self):
        """Poll to detect when a non-looping track finishes."""
        if self.is_playing and not self.is_paused and not self.is_repeat:
            if not pygame.mixer.music.get_busy():
                self.is_playing = False
                self.progress_var.set(0)
                self.lbl_current.configure(text="0:00")
                self._set_status("پخش تمام شد")
        self.root.after(400, self._check_end_loop)

    def _on_seek(self, val):
        if self.duration > 0 and self.file_path:
            target = (float(val) / 100) * self.duration
            try:
                pygame.mixer.music.set_pos(target)
            except Exception:
                pass

    # ----------------------------------------------------------- actions --

    def select_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("Audio Files", "*.mp3 *.wav *.ogg *.flac *.m4a")]
        )
        if path:
            self.file_path = path
            self._load_and_play(path)

    def _load_and_play(self, path: str):
        try:
            pygame.mixer.music.load(path)
            # Try to get duration via pygame Sound (works for wav/ogg, not always mp3)
            try:
                snd = pygame.mixer.Sound(path)
                self.duration = snd.get_length()
                del snd
            except Exception:
                self.duration = 0.0
            self.lbl_duration.configure(text=self._fmt(self.duration))

            name = os.path.splitext(os.path.basename(path))[0]
            self.lbl_track.configure(text=name)
            self.lbl_sub.configure(text=os.path.basename(path))

            pygame.mixer.music.play(-1 if self.is_repeat else 0)
            self.is_playing = True
            self.is_paused = False
            self._set_status("در حال پخش", "#4ade80")
            self._update_progress()
        except Exception as e:
            self._set_status(f"خطا: {e}", "#f87171")

    def toggle_play(self):
        if not self.file_path:
            self._set_status("ابتدا یک فایل انتخاب کنید", "#f87171")
            return
        if self.is_playing and not self.is_paused:
            pygame.mixer.music.pause()
            self.is_paused = True
            self._set_status("توقف موقت", "#facc15")
        elif self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
            self._set_status("در حال پخش", "#4ade80")
        else:
            self._load_and_play(self.file_path)

    def stop(self):
        pygame.mixer.music.stop()
        self.is_playing = False
        self.is_paused = False
        self.progress_var.set(0)
        self.lbl_current.configure(text="0:00")
        self._set_status("متوقف شد")

    def rewind(self):
        pygame.mixer.music.rewind()
        self.progress_var.set(0)
        self.lbl_current.configure(text="0:00")
        self._set_status("برگشت به ابتدا")

    def fast_forward(self):
        if not self.file_path:
            return
        pos_ms = pygame.mixer.music.get_pos()
        new_pos = (pos_ms / 1000) + 10
        try:
            pygame.mixer.music.set_pos(new_pos)
            self._set_status("جلو رفت ۱۰ ثانیه")
        except Exception:
            self._set_status("Fast forward پشتیبانی نمیشه برای این فرمت", "#f87171")

    def toggle_repeat(self):
        self.is_repeat = not self.is_repeat
        if self.is_playing:
            pygame.mixer.music.play(-1 if self.is_repeat else 0)
        if self.btn_repeat_widget:
            self.btn_repeat_widget.configure(
                style="Accent.TButton" if self.is_repeat else "Dark.TButton"
            )
        self._set_status("تکرار فعال ✓" if self.is_repeat else "تکرار غیرفعال")


def main():
    root = tk.Tk()
    root.geometry("420x340")
    app = MusicPlayer(root)
    root.mainloop()
    if PYGAME_OK:
        pygame.mixer.quit()


if __name__ == "__main__":
    main()
