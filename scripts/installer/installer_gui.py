"""Installer GUI — tkinter-based desktop installer for CowAgent."""

import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, ttk
from pathlib import Path

from .install_engine import InstallEngine


class InstallerApp:
    """Tkinter application with 3 pages: Welcome, Progress, Done."""

    WINDOW_WIDTH = 520
    WINDOW_HEIGHT = 400

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("CowAgent Installer")
        self.root.resizable(False, False)
        self._center_window()

        self.install_dir = tk.StringVar(value=InstallEngine.get_default_install_dir())
        self.status_text = tk.StringVar(value="")
        self.progress_var = tk.IntVar(value=0)

        self._build_ui()
        self._show_page("welcome")

    def run(self):
        self.root.mainloop()

    # ── UI construction ──────────────────────────────────────────────────

    def _build_ui(self):
        self.root.configure(bg="#f5f5f5")
        style = ttk.Style(self.root)
        style.theme_use("clam")

        # Pages container
        self.pages = {}
        for name in ("welcome", "progress", "done"):
            frame = ttk.Frame(self.root, padding=30)
            frame.place(x=0, y=0, width=self.WINDOW_WIDTH, height=self.WINDOW_HEIGHT)
            self.pages[name] = frame

        self._build_welcome_page()
        self._build_progress_page()
        self._build_done_page()

    def _build_welcome_page(self):
        frame = self.pages["welcome"]
        content = ttk.Frame(frame)
        content.pack(expand=True)

        # Emoji
        ttk.Label(content, text="🐄", font=("Segoe UI Emoji", 40)).pack(pady=(10, 15))

        # Title
        ttk.Label(content, text="CowAgent", font=("Segoe UI", 16, "bold")).pack()

        # Install path
        ttk.Label(content, text="Installation path:", font=("Segoe UI", 10)).pack(pady=(20, 5), anchor="w")

        path_frame = ttk.Frame(content)
        path_frame.pack(fill="x")
        entry = ttk.Entry(path_frame, textvariable=self.install_dir, font=("Segoe UI", 9))
        entry.pack(side="left", fill="x", expand=True)
        ttk.Button(path_frame, text="Browse...", command=self._browse_path).pack(side="left", padx=(6, 0))

        # Space info
        ttk.Label(content, text="Required space: ~1.2 GB", font=("Segoe UI", 8), foreground="#888").pack(pady=(8, 20))

        # Install button
        btn = ttk.Button(content, text="Install", command=self._start_install)
        btn.pack(ipadx=40, ipady=4)

    def _build_progress_page(self):
        frame = self.pages["progress"]
        content = ttk.Frame(frame)
        content.pack(expand=True, fill="x")

        ttk.Label(content, text="🐄", font=("Segoe UI Emoji", 40)).pack(pady=(10, 15))
        ttk.Label(content, text="Installing...", font=("Segoe UI", 14, "bold")).pack(pady=(0, 20))

        self.progress_bar = ttk.Progressbar(content, variable=self.progress_var, maximum=100, length=380)
        self.progress_bar.pack(pady=(0, 10))

        self.step_label = ttk.Label(content, textvariable=self.status_text, font=("Segoe UI", 9), foreground="#555")
        self.step_label.pack()

    def _build_done_page(self):
        frame = self.pages["done"]
        content = ttk.Frame(frame)
        content.pack(expand=True)

        ttk.Label(content, text="✅", font=("Segoe UI Emoji", 40)).pack(pady=(10, 15))
        ttk.Label(content, text="Installation Complete!", font=("Segoe UI", 14, "bold")).pack(pady=(0, 5))

        self.done_path_label = ttk.Label(content, text="", font=("Segoe UI", 9), foreground="#555")
        self.done_path_label.pack(pady=(0, 20))

        btn_frame = ttk.Frame(content)
        btn_frame.pack()
        ttk.Button(btn_frame, text="Launch CowAgent", command=self._launch).pack(side="left", ipadx=12, ipady=4, padx=(0, 10))
        ttk.Button(btn_frame, text="Close", command=self.root.destroy).pack(side="left", ipadx=12, ipady=4)

    # ── page navigation ──────────────────────────────────────────────────

    def _show_page(self, name):
        for key, frame in self.pages.items():
            frame.place_forget()
        self.pages[name].place(x=0, y=0, width=self.WINDOW_WIDTH, height=self.WINDOW_HEIGHT)
        self.root.update_idletasks()

    # ── actions ──────────────────────────────────────────────────────────

    def _browse_path(self):
        path = filedialog.askdirectory(title="Select installation folder")
        if path:
            self.install_dir.set(path)

    def _start_install(self):
        path = self.install_dir.get()
        engine = InstallEngine(path, None)
        valid, msg = engine.validate_path(path)
        if not valid:
            from tkinter import messagebox
            messagebox.showerror("Invalid Path", msg)
            return

        if os.path.exists(path) and os.listdir(path):
            from tkinter import messagebox
            if not messagebox.askyesno("Directory Exists",
                                       f"Directory already exists:\n{path}\n\nContinue installing into this directory?"):
                return

        self._show_page("progress")
        self._install_queue = queue.Queue()
        engine = InstallEngine(path, self._install_queue)
        t = threading.Thread(target=self._install_thread, args=(engine,), daemon=True)
        t.start()
        self.root.after(100, self._poll_progress)

    def _install_thread(self, engine):
        try:
            engine.run()
        except Exception as e:
            self._install_queue.put((-1, f"Error: {e}"))

    def _poll_progress(self):
        try:
            while True:
                percent, text = self._install_queue.get_nowait()
                if percent == -1:
                    from tkinter import messagebox
                    messagebox.showerror("Installation Failed", text)
                    self.root.destroy()
                    return
                self.progress_var.set(percent)
                self.status_text.set(text)
                if percent >= 100:
                    self._on_done()
                    return
        except queue.Empty:
            pass
        self.root.after(100, self._poll_progress)

    def _on_done(self):
        self.done_path_label.config(text=f"Location: {self.install_dir.get()}")
        self._show_page("done")

    def _launch(self):
        import subprocess
        install_dir = self.install_dir.get()
        python_path = os.path.join(install_dir, "python", "python.exe") if sys.platform == "win32" else os.path.join(install_dir, "python", "bin", "python3")
        app_py = os.path.join(install_dir, "cowagent", "app.py")
        if sys.platform == "win32":
            subprocess.Popen([python_path, app_py], cwd=os.path.join(install_dir, "cowagent"), creationflags=0x00000008)
        else:
            subprocess.Popen([python_path, app_py], cwd=os.path.join(install_dir, "cowagent"))
        import webbrowser
        import time
        time.sleep(2)
        webbrowser.open("http://localhost:9899/chat")
        self.root.destroy()

    def _center_window(self):
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - self.WINDOW_WIDTH) // 2
        y = (screen_h - self.WINDOW_HEIGHT) // 2
        self.root.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}+{x}+{y}")


def main():
    app = InstallerApp()
    app.run()


if __name__ == "__main__":
    main()
