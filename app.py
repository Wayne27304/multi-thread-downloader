import os
import queue
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk


USER_AGENT = "SimpleParallelDownloader/1.0"
BLOCK_SIZE = 64 * 1024


class DownloadJob:
    def __init__(self, url, destination, connection_count, events):
        self.url = url
        self.destination = Path(destination)
        self.connection_count = connection_count
        self.events = events
        self.cancel_event = threading.Event()
        self.lock = threading.Lock()
        self.downloaded = 0
        self.total_size = 0

    def _request(self, headers=None):
        request = urllib.request.Request(
            self.url,
            headers={"User-Agent": USER_AGENT, **(headers or {})},
        )
        return urllib.request.urlopen(request, timeout=30)

    def _probe_ranges(self):
        try:
            response = self._request({"Range": "bytes=0-0"})
        except (urllib.error.URLError, ValueError):
            return None

        with response:
            if response.status != 206:
                return None
            match = re.fullmatch(
                r"bytes 0-0/(\d+)", response.headers.get("Content-Range", "")
            )
            if match:
                return int(match.group(1))
        return None

    def _write_block(self, output, position, data):
        with self.lock:
            output.seek(position)
            output.write(data)
            self.downloaded += len(data)

    def _download_part(self, output, start, end):
        response = self._request({"Range": f"bytes={start}-{end}"})
        with response:
            if response.status != 206:
                raise RuntimeError("伺服器未依要求提供分段資料。")
            position = start
            while position <= end:
                if self.cancel_event.is_set():
                    return
                data = response.read(min(BLOCK_SIZE, end - position + 1))
                if not data:
                    raise RuntimeError("下載資料提前結束，請重新下載。")
                self._write_block(output, position, data)
                position += len(data)

    def _download_parallel(self, temporary_path, total_size):
        worker_count = min(self.connection_count, total_size)
        errors = []
        with temporary_path.open("wb") as output:
            output.truncate(total_size)
            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                futures = []
                for index in range(worker_count):
                    start = total_size * index // worker_count
                    end = total_size * (index + 1) // worker_count - 1
                    futures.append(executor.submit(self._download_part, output, start, end))
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as error:
                        self.cancel_event.set()
                        errors.append(error)
        if errors:
            raise errors[0]

    def _download_single(self, temporary_path):
        response = self._request()
        with response, temporary_path.open("wb") as output:
            length = response.headers.get("Content-Length")
            if length and length.isdigit():
                with self.lock:
                    self.total_size = int(length)
            while not self.cancel_event.is_set():
                data = response.read(BLOCK_SIZE)
                if not data:
                    break
                output.write(data)
                with self.lock:
                    self.downloaded += len(data)

    def run(self):
        temporary_path = Path(f"{self.destination}.part")
        try:
            self.destination.parent.mkdir(parents=True, exist_ok=True)
            range_size = self._probe_ranges()
            if self.cancel_event.is_set():
                self.events.put(("cancelled", None))
                return
            if range_size and self.connection_count > 1:
                self.total_size = range_size
                self.events.put(("status", f"正在使用 {min(self.connection_count, range_size)} 條連線下載"))
                self._download_parallel(temporary_path, range_size)
            else:
                if self.connection_count > 1 and range_size is None:
                    self.events.put(("status", "伺服器不支援分段下載，改用單一連線"))
                else:
                    self.events.put(("status", "正在下載"))
                self._download_single(temporary_path)

            if self.cancel_event.is_set():
                self.events.put(("cancelled", str(temporary_path)))
                return
            os.replace(temporary_path, self.destination)
            self.events.put(("complete", str(self.destination)))
        except Exception as error:
            self.events.put(("error", str(error)))


class DownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("多線程下載器")
        self.root.geometry("640x470")
        self.root.configure(background="#edf1ed")
        self.events = queue.Queue()
        self.job = None
        self.worker = None

        self.url_var = tk.StringVar()
        self.destination_var = tk.StringVar()
        self.connection_var = tk.IntVar(value=8)
        self.status_var = tk.StringVar(value="等待下載")
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_percent_var = tk.StringVar(value="0.0%")
        self._shown_progress = 0.0

        self._configure_styles()
        self._build_ui()
        self._fit_window_to_content()
        self.root.after(100, self._ask_initial_details)
        self.root.after(150, self._poll_events)

    def _fit_window_to_content(self):
        self.root.update_idletasks()
        content = self.root.winfo_children()[0]
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        max_width = max(1, screen_width - 48)
        max_height = max(1, screen_height - 80)
        width = min(max(640, content.winfo_reqwidth()), max_width)
        height = min(max(470, content.winfo_reqheight()), max_height)
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(width, height)

    def _configure_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("App.TFrame", background="#edf1ed")
        style.configure("Panel.TFrame", background="#ffffff")
        style.configure(
            "Field.TLabel",
            background="#ffffff",
            foreground="#52615a",
            font=("Microsoft JhengHei UI", 10, "bold"),
        )
        style.configure(
            "Meta.TLabel",
            background="#ffffff",
            foreground="#718078",
            font=("Microsoft JhengHei UI", 9),
        )
        style.configure(
            "Status.TLabel",
            background="#edf1ed",
            foreground="#42534b",
            font=("Microsoft JhengHei UI", 9),
        )
        style.configure(
            "ProgressTitle.TLabel",
            background="#edf1ed",
            foreground="#42534b",
            font=("Microsoft JhengHei UI", 9, "bold"),
        )
        style.configure(
            "ProgressValue.TLabel",
            background="#edf1ed",
            foreground="#176b56",
            font=("Cascadia Code", 10, "bold"),
        )
        style.configure(
            "TEntry",
            fieldbackground="#f7f9f7",
            foreground="#1c2b25",
            bordercolor="#d7e0d9",
            lightcolor="#d7e0d9",
            darkcolor="#d7e0d9",
            insertcolor="#176b56",
            padding=(10, 9),
        )
        style.map(
            "TEntry",
            bordercolor=[("focus", "#176b56")],
            lightcolor=[("focus", "#176b56")],
            darkcolor=[("focus", "#176b56")],
        )
        style.configure(
            "TSpinbox",
            fieldbackground="#f7f9f7",
            foreground="#1c2b25",
            bordercolor="#d7e0d9",
            padding=(8, 6),
        )
        style.configure(
            "Primary.TButton",
            background="#176b56",
            foreground="#ffffff",
            borderwidth=0,
            padding=(18, 10),
            font=("Microsoft JhengHei UI", 10, "bold"),
        )
        style.map(
            "Primary.TButton",
            background=[("disabled", "#aab9b0"), ("active", "#10513f")],
            foreground=[("disabled", "#eaf0ec")],
        )
        style.configure(
            "Quiet.TButton",
            background="#e8eeea",
            foreground="#33483e",
            borderwidth=0,
            padding=(13, 9),
            font=("Microsoft JhengHei UI", 9, "bold"),
        )
        style.map("Quiet.TButton", background=[("active", "#dbe5de")])
        style.configure(
            "Cancel.TButton",
            background="#ffffff",
            foreground="#8d453d",
            bordercolor="#e5d4d1",
            padding=(14, 9),
            font=("Microsoft JhengHei UI", 9, "bold"),
        )
        style.map("Cancel.TButton", background=[("active", "#fbf3f1")])
        style.configure(
            "Download.Horizontal.TProgressbar",
            troughcolor="#dfe8e1",
            background="#32a27c",
            bordercolor="#dfe8e1",
            lightcolor="#32a27c",
            darkcolor="#32a27c",
            thickness=12,
        )

    def _build_ui(self):
        frame = ttk.Frame(self.root, style="App.TFrame", padding=22)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)

        header = tk.Frame(frame, background="#18392f", padx=24, pady=21)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        header.columnconfigure(0, weight=1)
        tk.Label(
            header,
            text="多線程下載器",
            background="#18392f",
            foreground="#ffffff",
            font=("Microsoft JhengHei UI", 22, "bold"),
        ).grid(row=1, column=0, sticky="w", pady=(5, 0))

        panel = ttk.Frame(frame, style="Panel.TFrame", padding=(22, 20))
        panel.grid(row=1, column=0, sticky="ew")
        panel.columnconfigure(0, weight=1)

        ttk.Label(panel, text="下載網址", style="Field.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 7)
        )
        self.url_entry = ttk.Entry(panel, textvariable=self.url_var)
        self.url_entry.grid(row=1, column=0, sticky="ew", pady=(0, 16))

        ttk.Label(panel, text="儲存位置", style="Field.TLabel").grid(
            row=2, column=0, sticky="w", pady=(0, 7)
        )
        destination_row = ttk.Frame(panel, style="Panel.TFrame")
        destination_row.grid(row=3, column=0, sticky="ew")
        destination_row.columnconfigure(0, weight=1)
        self.destination_entry = ttk.Entry(destination_row, textvariable=self.destination_var)
        self.destination_entry.grid(row=0, column=0, sticky="ew")
        self.browse_button = ttk.Button(
            destination_row,
            text="瀏覽…",
            style="Quiet.TButton",
            command=self._choose_destination,
        )
        self.browse_button.grid(row=0, column=1, padx=(9, 0))

        settings = ttk.Frame(panel, style="Panel.TFrame")
        settings.grid(row=4, column=0, sticky="ew", pady=(18, 0))
        ttk.Label(settings, text="連線數 (最高100)", style="Field.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 12)
        )
        self.connection_spinbox = ttk.Spinbox(
            settings, from_=1, to=100, width=6, textvariable=self.connection_var
        )
        self.connection_spinbox.grid(row=0, column=1, sticky="w")
        ttk.Label(settings, text="條", style="Meta.TLabel").grid(
            row=0, column=2, sticky="w", padx=(8, 0)
        )

        progress_heading = ttk.Frame(frame, style="App.TFrame")
        progress_heading.grid(row=2, column=0, sticky="ew", pady=(20, 0))
        progress_heading.columnconfigure(0, weight=1)
        ttk.Label(
            progress_heading, text="總下載進度", style="ProgressTitle.TLabel"
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            progress_heading, textvariable=self.progress_percent_var, style="ProgressValue.TLabel"
        ).grid(row=0, column=1, sticky="e")

        self.progress = ttk.Progressbar(
            frame,
            variable=self.progress_var,
            maximum=100,
            mode="determinate",
            style="Download.Horizontal.TProgressbar",
        )
        self.progress.grid(row=3, column=0, sticky="ew", pady=(7, 8))
        ttk.Label(frame, textvariable=self.status_var, style="Status.TLabel").grid(
            row=4, column=0, sticky="w", pady=(0, 17)
        )

        actions = ttk.Frame(frame, style="App.TFrame")
        actions.grid(row=5, column=0, sticky="e")
        self.start_button = ttk.Button(
            actions,
            text="開始下載",
            style="Primary.TButton",
            command=self._start_download,
        )
        self.start_button.grid(row=0, column=1, sticky="e")
        self.cancel_button = ttk.Button(
            actions,
            text="取消",
            style="Cancel.TButton",
            command=self._cancel_download,
            state="disabled",
        )
        self.cancel_button.grid(row=0, column=2, sticky="e", padx=(9, 0))
        self.root.bind("<Return>", lambda _event: self._start_download())

    def _ask_initial_details(self):
        url = simpledialog.askstring("新增下載", "請輸入下載連結：", parent=self.root)
        if url:
            self.url_var.set(url.strip())
            self._choose_destination()
        self.root.deiconify()
        self.url_entry.focus_set()

    def _choose_destination(self):
        url = self.url_var.get().strip()
        default_name = Path(urllib.parse.unquote(urllib.parse.urlparse(url).path)).name
        if not default_name:
            default_name = "download.bin"
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="選擇下載位置",
            initialfile=default_name,
        )
        if path:
            self.destination_var.set(path)

    def _start_download(self):
        url = self.url_var.get().strip()
        destination = self.destination_var.get().strip()
        try:
            connection_count = int(self.connection_var.get())
        except (tk.TclError, ValueError):
            messagebox.showerror("連線數錯誤", "連線數請設定為 1 到 100。", parent=self.root)
            return

        if not url.lower().startswith(("http://", "https://")):
            messagebox.showerror("網址錯誤", "請輸入有效的 HTTP 或 HTTPS 下載連結。", parent=self.root)
            return
        if not 1 <= connection_count <= 100:
            messagebox.showerror("連線數錯誤", "連線數請設定為 1 到 100。", parent=self.root)
            return
        if not destination:
            self._choose_destination()
            destination = self.destination_var.get().strip()
            if not destination:
                return
        if Path(destination).exists() and not messagebox.askyesno(
            "確認覆寫", "檔案已存在，要覆寫嗎？", parent=self.root
        ):
            return

        self.progress_var.set(0)
        self.progress_percent_var.set("0.0%")
        self._shown_progress = 0.0
        self.status_var.set("正在連線…")
        self.progress.configure(mode="determinate")
        self.start_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self._set_inputs_state("disabled")
        self.job = DownloadJob(url, destination, connection_count, self.events)
        self.worker = threading.Thread(target=self.job.run, daemon=True)
        self.worker.start()

    def _set_inputs_state(self, state):
        self.url_entry.configure(state=state)
        self.destination_entry.configure(state=state)
        self.connection_spinbox.configure(state=state)
        self.browse_button.configure(state=state)

    def _cancel_download(self):
        if self.job:
            self.job.cancel_event.set()
            self.status_var.set("正在取消下載…")
            self.cancel_button.configure(state="disabled")

    def _finish(self):
        self.start_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")
        self._set_inputs_state("normal")

    @staticmethod
    def _format_size(size):
        if size < 1024:
            return f"{size} B"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        if size < 1024 * 1024 * 1024:
            return f"{size / 1024 / 1024:.2f} MB"
        return f"{size / 1024 / 1024 / 1024:.2f} GB"

    def _poll_events(self):
        while True:
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "status":
                self.status_var.set(value)
            elif kind == "complete":
                self.progress_var.set(100)
                self.progress_percent_var.set("100.0%")
                self._shown_progress = 100.0
                self.status_var.set(f"下載完成：{value}")
                self._finish()
            elif kind == "cancelled":
                detail = f"部分檔案保留於：{value}" if value else ""
                self.status_var.set(f"已取消。{detail}")
                self._finish()
            elif kind == "error":
                self.status_var.set("下載失敗")
                self._finish()
                messagebox.showerror("下載失敗", value, parent=self.root)

        if self.job and self.start_button.instate(["disabled"]):
            with self.job.lock:
                downloaded = self.job.downloaded
                total_size = self.job.total_size
            if total_size:
                if self.progress.cget("mode") == "indeterminate":
                    self.progress.stop()
                self.progress.configure(mode="determinate")
                total_progress = min(100.0, downloaded * 100 / total_size)
                self._shown_progress = max(self._shown_progress, total_progress)
                self.progress_var.set(self._shown_progress)
                self.progress_percent_var.set(f"{self._shown_progress:.1f}%")
                self.status_var.set(
                    f"{self.status_var.get().split(' | ')[0]} | "
                    f"{self._format_size(downloaded)} / {self._format_size(total_size)}"
                )
            else:
                self.progress_percent_var.set("—")
                if self.progress.cget("mode") != "indeterminate":
                    self.progress.configure(mode="indeterminate")
                    self.progress.start(12)
                self.status_var.set(
                    f"{self.status_var.get().split(' | ')[0]} | "
                    f"已下載 {self._format_size(downloaded)}（總大小未知）"
                )
        elif self.progress.cget("mode") == "indeterminate":
            self.progress.stop()
            self.progress.configure(mode="determinate")
        self.root.after(150, self._poll_events)


def main():
    root = tk.Tk()
    DownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
