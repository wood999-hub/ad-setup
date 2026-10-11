"""광고 자동화 - 더블클릭으로 여는 프로그램 창.

버튼을 누르면 main.py 의 기능을 보이지 않게 실행하고 결과를 창 안에 보여준다.
(검은 명령창 없음. 로그인할 때만 브라우저 창이 뜬다)
"""
import os
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

ROOT = Path(__file__).resolve().parent
PY = sys.executable.replace("pythonw.exe", "python.exe")
ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # 검은 창 숨김 (Windows)

# ---- 디자인 ----
BG = "#F4F6FA"
CARD = "#FFFFFF"
LINE = "#E3E7EF"
NAVY = "#1B2440"
BLUE = "#2F6BFF"
BLUE_DARK = "#1E54D6"
BLUE_SOFT = "#EAF0FF"
TEXT = "#1B2440"
MUTED = "#7A8499"
GREEN = "#13A35B"
RED = "#E5484D"
FONT = "Malgun Gothic"


def font(size=10, bold=False):
    return (FONT, size, "bold" if bold else "normal")


class FlatButton(tk.Label):
    """마우스를 올리면 색이 바뀌는 납작한 버튼."""

    def __init__(self, master, text, command, primary=False, small=False, **kw):
        self.colors = (BLUE, BLUE_DARK, "white") if primary else (BLUE_SOFT, "#DCE6FF", BLUE)
        if small:
            self.colors = (BG, LINE, MUTED)
        super().__init__(master, text=text, bg=self.colors[0], fg=self.colors[2], cursor="hand2",
                         font=font(9 if small else 10, not small), padx=10 if small else 14,
                         pady=4 if small else 9, **kw)
        self.command = command
        self.bind("<Enter>", lambda e: self.config(bg=self.colors[1]))
        self.bind("<Leave>", lambda e: self.config(bg=self.colors[0]))
        self.bind("<Button-1>", lambda e: self.command())


class App:
    STEPS = [
        ("1", "가져오기", "광고센터의 지금 입찰가를\n엑셀 파일로 가져옵니다", "가져오기", "pull"),
        ("2", "엑셀에서 수정", "bid 칸의 숫자를 고치고\n저장 후 닫습니다", "엑셀 열기", "excel"),
        ("3", "미리보기", "무엇이 바뀌는지\n먼저 확인합니다", "미리보기", "preview"),
        ("4", "반영하기", "광고센터에 입력하고\n제대로 들어갔는지 확인", "반영하기", "apply"),
        ("5", "확인 · 성과", "입찰가 일치 여부와\n오늘 성과를 봅니다", "확인하기", "check"),
    ]

    def __init__(self, root: tk.Tk):
        self.root, self.busy, self.proc = root, False, None
        root.title("광고 자동화")
        root.geometry("980x660")
        root.minsize(900, 560)
        root.configure(bg=BG)

        self._header()
        self._steps()
        self._footer()   # 아래쪽에 먼저 고정
        self._log()
        self.write("안녕하세요! 왼쪽부터 순서대로 버튼을 누르면 됩니다.\n", "info")
        self.write("처음 쓰거나 '로그인' 관련 오류가 나오면 오른쪽 위 [로그인] 을 먼저 눌러 주세요.\n\n", "muted")

    # ---------- 화면 구성 ----------
    def _header(self):
        head = tk.Frame(self.root, bg=NAVY, height=78)
        head.pack(fill="x")
        head.pack_propagate(False)
        left = tk.Frame(head, bg=NAVY)
        left.pack(side="left", padx=24)
        tk.Label(left, text="광고 자동화", bg=NAVY, fg="white", font=font(17, True)).pack(anchor="w", pady=(14, 0))
        tk.Label(left, text="G마켓 광고센터 · 키워드 입찰가 세팅 / 확인", bg=NAVY, fg="#AEB8D3",
                 font=font(9)).pack(anchor="w")
        right = tk.Frame(head, bg=NAVY)
        right.pack(side="right", padx=24)
        self.pill = tk.Label(right, text="● 준비됨", bg="#25315A", fg="#7EE2A8", font=font(9, True), padx=12, pady=5)
        self.pill.pack(side="right", padx=(10, 0))
        FlatButton(right, "로그인", self.login).pack(side="right")

    def _steps(self):
        row = tk.Frame(self.root, bg=BG)
        row.pack(fill="x", padx=18, pady=(18, 8))
        actions = {"pull": lambda: self.run("pull"), "excel": self.open_csv, "preview": lambda: self.run("setup"),
                   "apply": self.apply, "check": lambda: self.run("check")}
        for i, (num, title, desc, label, key) in enumerate(self.STEPS):
            row.columnconfigure(i, weight=1, uniform="step")
            card = tk.Frame(row, bg=CARD, highlightbackground=LINE, highlightthickness=1)
            card.grid(row=0, column=i, sticky="nsew", padx=6)
            top = tk.Frame(card, bg=CARD)
            top.pack(fill="x", padx=14, pady=(14, 4))
            tk.Label(top, text=num, bg=BLUE if key == "apply" else BLUE_SOFT, fg="white" if key == "apply" else BLUE,
                     font=font(10, True), width=2).pack(side="left")
            tk.Label(top, text=title, bg=CARD, fg=TEXT, font=font(11, True)).pack(side="left", padx=8)
            tk.Label(card, text=desc, bg=CARD, fg=MUTED, font=font(9), justify="left").pack(anchor="w", padx=14)
            FlatButton(card, label, actions[key], primary=(key == "apply")).pack(fill="x", padx=14, pady=14)

    def _log(self):
        wrap = tk.Frame(self.root, bg=CARD, highlightbackground=LINE, highlightthickness=1)
        wrap.pack(fill="both", expand=True, padx=24, pady=(6, 6))
        bar = tk.Frame(wrap, bg=CARD)
        bar.pack(fill="x", padx=16, pady=(12, 0))
        tk.Label(bar, text="진행 상황", bg=CARD, fg=TEXT, font=font(11, True)).pack(side="left")
        FlatButton(bar, "지우기", lambda: self.out.delete("1.0", "end"), small=True).pack(side="right")
        body = tk.Frame(wrap, bg=CARD)
        body.pack(fill="both", expand=True, padx=16, pady=12)
        sb = tk.Scrollbar(body)
        sb.pack(side="right", fill="y")
        self.out = tk.Text(body, bg=CARD, fg=TEXT, font=font(10), relief="flat", bd=0, highlightthickness=0,
                           wrap="word", height=10,
                           yscrollcommand=sb.set, padx=4, pady=4, spacing1=2, spacing3=2)
        self.out.pack(fill="both", expand=True)
        sb.config(command=self.out.yview)
        for tag, color, bold in [("ok", GREEN, True), ("err", RED, True), ("chg", BLUE, True),
                                 ("cmd", NAVY, True), ("muted", MUTED, False), ("info", TEXT, True)]:
            self.out.tag_config(tag, foreground=color, font=font(10, bold))

    def _footer(self):
        foot = tk.Frame(self.root, bg=BG)
        foot.pack(side="bottom", fill="x", padx=24, pady=(0, 12))
        for text, cmd in [("사용설명서", self.open_manual), ("변경 기록", self.open_log),
                          ("프로그램 업데이트", self.update)]:
            FlatButton(foot, text, cmd, small=True).pack(side="left", padx=(0, 6))
        tk.Label(foot, text="반영 전에는 항상 미리보기로 확인하세요", bg=BG, fg=MUTED, font=font(9)).pack(side="right")

    # ---------- 출력 ----------
    # 명령어 안내 문구를 버튼 안내로 바꿔서 보여준다
    PLAIN = {
        "(미리보기) 실제 반영하려면 --apply 를 붙이세요.": "(미리보기) 이대로 괜찮으면 [4. 반영하기] 를 누르세요.",
        "→ 엑셀로 열어 bid 칸을 고친 뒤 'setup' 으로 미리보기, 'setup --apply' 로 반영": "→ [2. 엑셀 열기] 에서 bid 칸을 고친 뒤 [3. 미리보기] 를 누르세요.",
        "'python main.py inspect' 로 다시 로그인한 뒤 q 로 끝내세요.": "오른쪽 위 [로그인] 을 눌러 다시 로그인하세요.",
        "먼저 'pull' 을 실행하세요.": "먼저 [1. 가져오기] 를 누르세요.",
    }

    def write(self, text: str, tag: str | None = None):
        for old, new in self.PLAIN.items():
            text = text.replace(old, new)
        if tag is None:
            t = text.strip()
            tag = ("ok" if t.startswith("✓") or t.startswith("✔") else
                   "err" if t.startswith(("✗", "✖", "[오류]", "Traceback", "중단")) or "Error" in t else
                   "chg" if t.startswith("[변경]") else
                   "muted" if t.startswith(("(", "저장:", "→")) else None)
        self.out.insert("end", text, tag or ())
        self.out.see("end")

    def set_busy(self, busy: bool, label: str = ""):
        self.busy = busy
        if busy:
            self.pill.config(text=f"● {label} 중…", fg="#FFD37A")
        else:
            self.pill.config(text="● 준비됨", fg="#7EE2A8")

    # ---------- 실행 ----------
    NAMES = {"pull": "가져오는", "setup": "미리보기", "check": "확인하는", "login": "로그인", "git": "업데이트"}

    def run(self, *args, cmd: list[str] | None = None):
        if self.busy:
            messagebox.showinfo("광고 자동화", "앞의 작업이 끝날 때까지 잠시만 기다려 주세요.")
            return
        if cmd is None:
            cmd = [PY, "main.py", *args]
            if args[0] != "login":
                cmd.append("--headless")  # 브라우저 창 없이 조용히 실행
        name = "반영하는" if "--apply" in args else self.NAMES.get(args[0] if args else cmd[0], "실행")
        self.set_busy(True, name)
        self.write(f"\n▶ {name.rstrip('는')} 시작\n", "cmd")

        def work():
            self.proc = subprocess.Popen(cmd, cwd=ROOT, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                         stdin=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
                                         creationflags=NO_WINDOW)
            for line in self.proc.stdout:
                self.root.after(0, self.write, line)
            code = self.proc.wait()
            if code == 0:
                self.root.after(0, self.write, "✔ 완료\n")
            else:
                self.root.after(0, self.write, "✖ 오류로 멈췄습니다. 위 내용을 캡처해서 Claude 에게 보여주세요.\n")
            self.root.after(0, self.set_busy, False)

        threading.Thread(target=work, daemon=True).start()

    def login(self):
        self.run("login")
        messagebox.showinfo("로그인", "새로 뜬 브라우저 창에서 로그인하세요.\n\n"
                                    "로그인이 끝나 광고센터 화면이 보이면\n이 창의 [확인] 을 누르세요.")
        try:
            self.proc.stdin.write("\n")
            self.proc.stdin.flush()
        except Exception:
            pass

    def apply(self):
        if messagebox.askyesno("반영하기", "엑셀에 적은 입찰가를 실제 광고센터에 반영할까요?\n\n"
                                         "(먼저 3. 미리보기로 확인하는 것을 권장합니다)"):
            self.run("setup", "--apply")

    def update(self):
        self.run(cmd=["git", "pull"])

    def _open(self, path: Path, missing: str):
        if not path.exists():
            messagebox.showinfo("광고 자동화", missing)
            return False
        if hasattr(os, "startfile"):
            os.startfile(path)
        return True

    def open_csv(self):
        if self._open(ROOT / "config" / "keywords.csv", "아직 파일이 없습니다. 1. 가져오기를 먼저 눌러 주세요."):
            self.write("\n엑셀에서 bid 칸을 고친 뒤 저장(Ctrl+S)하고 엑셀을 닫아 주세요.\n"
                       "저장할 때 '형식을 유지할까요?' 라고 물으면 [예] 를 누르면 됩니다.\n", "muted")

    def open_log(self):
        self._open(ROOT / "data" / "changes.csv", "아직 변경 기록이 없습니다.")

    def open_manual(self):
        self._open(ROOT / "사용설명서.txt", "사용설명서 파일을 찾을 수 없습니다.")


if __name__ == "__main__":
    try:  # 고해상도 화면에서 글자가 흐릿하지 않게 (Windows)
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    App(root)
    root.mainloop()
