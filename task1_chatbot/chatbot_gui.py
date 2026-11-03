"""
CodSoft AI Internship - Task 1: Chatbot GUI (v2, Tkinter)

Features: chat bubbles, timestamps, typing animation, quick-reply buttons,
dark/light theme, save chat to a file, clear chat.

Keep this file in the same folder as chatbot.py
Run:  python chatbot_gui.py
"""

import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox

from chatbot import BOT_NAME, EXIT, SUGGESTIONS, Chatbot

THEMES = {
    "dark": dict(
        bg="#0b1220", panel="#111a2e", user_bg="#2563eb", user_fg="#ffffff", user_time="#bfdbfe",
        bot_bg="#1e293b", bot_fg="#e2e8f0", time_fg="#94a3b8", accent="#22d3ee",
        entry_bg="#1e293b", entry_fg="#e2e8f0", chip_bg="#1e293b", chip_fg="#cbd5e1",
        chip_hover="#334155", status="#4ade80",
    ),
    "light": dict(
        bg="#f1f5f9", panel="#ffffff", user_bg="#2563eb", user_fg="#ffffff", user_time="#dbeafe",
        bot_bg="#e2e8f0", bot_fg="#0f172a", time_fg="#64748b", accent="#0284c7",
        entry_bg="#ffffff", entry_fg="#0f172a", chip_bg="#e2e8f0", chip_fg="#334155",
        chip_hover="#cbd5e1", status="#16a34a",
    ),
}

FONT = "Segoe UI"
EMOJI_FONT = "Segoe UI Emoji"
GREETING = f"Hi! I'm {BOT_NAME} 👋 Tap a button below or just type. Say 'help' to see everything I can do."


class ChatApp:
    def __init__(self, root):
        self.root = root
        self.bot = Chatbot()
        self.theme = "dark"
        self.messages = []      # (sender, text, time)
        self.bubbles = []       # bubble widgets, so we can destroy them cleanly
        self.busy = False
        self.typing_job = None
        self.resize_job = None
        self.wrap = 330

        root.title(f"{BOT_NAME} · Rule-Based Chatbot")
        root.geometry("480x700")
        root.minsize(380, 520)

        self.build_ui()
        self.add_message("bot", GREETING)
        root.bind("<Configure>", self.on_resize)

    # ------------------------------------------------------------------ UI
    def build_ui(self):
        t = THEMES[self.theme]
        self.root.configure(bg=t["bg"])

        # Header
        header = tk.Frame(self.root, bg=t["panel"], padx=14, pady=10)
        header.pack(fill="x")
        tk.Label(header, text="🤖", font=(EMOJI_FONT, 22), bg=t["panel"], fg=t["accent"]).pack(side="left")
        info = tk.Frame(header, bg=t["panel"])
        info.pack(side="left", padx=10)
        tk.Label(info, text=BOT_NAME, font=(FONT, 13, "bold"), bg=t["panel"], fg=t["bot_fg"]).pack(anchor="w")
        self.status = tk.Label(info, text="● online", font=(FONT, 9), bg=t["panel"], fg=t["status"])
        self.status.pack(anchor="w")

        theme_icon = "🌙" if self.theme == "dark" else "☀️"
        for icon, cmd in ((theme_icon, self.toggle_theme), ("💾", self.save_chat), ("🗑", self.clear_chat)):
            tk.Button(
                header, text=icon, command=cmd, bg=t["panel"], fg=t["bot_fg"], bd=0, relief="flat", padx=6,
                activebackground=t["chip_hover"], font=(EMOJI_FONT, 13), cursor="hand2",
            ).pack(side="right")

        # Chat area
        body = tk.Frame(self.root, bg=t["bg"])
        body.pack(fill="both", expand=True)
        self.chat = tk.Text(
            body, wrap="word", state="disabled", bg=t["bg"], bd=0, highlightthickness=0,
            padx=8, pady=8, cursor="arrow", spacing1=2,
        )
        scroll = tk.Scrollbar(body, command=self.chat.yview)
        self.chat.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.chat.pack(side="left", fill="both", expand=True)
        self.chat.tag_config("user_line", justify="right")
        self.chat.tag_config("bot_line", justify="left")

        # Quick-reply buttons
        chips = tk.Frame(self.root, bg=t["bg"], padx=10)
        chips.pack(fill="x", pady=(4, 0))
        for i, (label, message) in enumerate(SUGGESTIONS):
            b = tk.Button(
                chips, text=label, bg=t["chip_bg"], fg=t["chip_fg"], bd=0, padx=8, pady=6,
                font=(FONT, 9), cursor="hand2", activebackground=t["chip_hover"],
                command=lambda m=message: self.send(preset=m),
            )
            b.grid(row=i // 3, column=i % 3, padx=3, pady=3, sticky="ew")
            b.bind("<Enter>", lambda e, w=b: w.config(bg=t["chip_hover"]))
            b.bind("<Leave>", lambda e, w=b: w.config(bg=t["chip_bg"]))
        for c in range(3):
            chips.grid_columnconfigure(c, weight=1)

        # Input row
        row = tk.Frame(self.root, bg=t["bg"], padx=10, pady=10)
        row.pack(fill="x")
        self.entry = tk.Entry(
            row, font=(FONT, 12), bg=t["entry_bg"], fg=t["entry_fg"], insertbackground=t["entry_fg"],
            bd=0, highlightthickness=1, highlightbackground=t["chip_hover"], highlightcolor=t["accent"],
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=9, padx=(0, 8))
        self.entry.bind("<Return>", self.send)
        tk.Button(
            row, text="Send ➤", command=self.send, bg=t["accent"], fg="#0b1220", bd=0,
            font=(FONT, 11, "bold"), padx=14, pady=7, cursor="hand2", activebackground=t["accent"],
        ).pack(side="right")
        self.entry.focus()

    # ------------------------------------------------------------- bubbles
    def add_message(self, sender, text):
        stamp = datetime.now().strftime("%I:%M %p").lstrip("0")
        self.messages.append((sender, text, stamp))
        self.draw_bubble(sender, text, stamp)
        self.scroll_to_end()

    def draw_bubble(self, sender, text, stamp):
        t = THEMES[self.theme]
        is_user = sender == "user"
        bg = t["user_bg"] if is_user else t["bot_bg"]
        fg = t["user_fg"] if is_user else t["bot_fg"]
        time_fg = t["user_time"] if is_user else t["time_fg"]

        bubble = tk.Frame(self.chat, bg=bg, padx=12, pady=7)
        msg = tk.Label(bubble, text=text, bg=bg, fg=fg, font=(FONT, 11), wraplength=self.wrap, justify="left")
        msg.pack(anchor="w")
        when = tk.Label(bubble, text=stamp, bg=bg, fg=time_fg, font=(FONT, 8))
        when.pack(anchor="e")
        for w in (bubble, msg, when):          # let the mouse wheel scroll over bubbles too
            w.bind("<MouseWheel>", self.on_wheel)

        self.chat.config(state="normal")
        start = self.chat.index("end-1c")
        self.chat.window_create("end", window=bubble, padx=6, pady=4)
        self.chat.insert("end", "\n")
        self.chat.tag_add("user_line" if is_user else "bot_line", start, "end-1c")
        self.chat.config(state="disabled")
        self.bubbles.append(bubble)

    def render_all(self):
        for b in self.bubbles:
            b.destroy()
        self.bubbles.clear()
        self.chat.config(state="normal")
        self.chat.delete("1.0", "end")
        self.chat.config(state="disabled")
        for sender, text, stamp in self.messages:
            self.draw_bubble(sender, text, stamp)
        self.scroll_to_end()

    def scroll_to_end(self):
        self.chat.update_idletasks()      # let Tk finish layout first, then jump to the bottom
        self.chat.yview_moveto(1.0)

    def on_wheel(self, event):
        self.chat.yview_scroll(-1 if event.delta > 0 else 1, "units")

    def on_resize(self, event):
        if event.widget is not self.root:
            return
        try:
            width = self.chat.winfo_width()
        except tk.TclError:
            return
        if width < 100:
            return
        new_wrap = max(200, int(width * 0.68))
        if abs(new_wrap - self.wrap) < 30:
            return
        self.wrap = new_wrap
        if self.resize_job:
            self.root.after_cancel(self.resize_job)
        self.resize_job = self.root.after(200, self.render_all)

    # ------------------------------------------------------------ chatting
    def send(self, event=None, preset=None):
        if self.busy:
            return "break"
        text = (preset or self.entry.get()).strip()
        if not text:
            return "break"
        self.entry.delete(0, "end")
        self.add_message("user", text)

        reply = self.bot.respond(text)
        self.busy = True
        self.start_typing()
        delay = min(1300, 450 + len(reply) * 9)     # longer replies "take longer to type"
        self.root.after(delay, lambda: self.finish_reply(reply))
        return "break"

    def finish_reply(self, reply):
        self.stop_typing()
        if reply == EXIT:
            self.add_message("bot", "Bye! Take care 👋")
            self.root.after(1400, self.root.destroy)
            return
        self.add_message("bot", reply)
        self.busy = False

    def start_typing(self, n=0):
        self.status.config(text=f"{BOT_NAME} is typing" + "." * (n % 4), fg=THEMES[self.theme]["accent"])
        self.typing_job = self.root.after(300, lambda: self.start_typing(n + 1))

    def stop_typing(self):
        if self.typing_job:
            self.root.after_cancel(self.typing_job)
            self.typing_job = None
        self.status.config(text="● online", fg=THEMES[self.theme]["status"])

    # ------------------------------------------------------------- buttons
    def toggle_theme(self):
        if self.busy:
            return
        self.theme = "light" if self.theme == "dark" else "dark"
        for w in self.root.winfo_children():
            w.destroy()
        self.bubbles.clear()
        self.build_ui()
        self.render_all()

    def clear_chat(self):
        if self.busy:
            return
        self.bot = Chatbot()
        self.messages.clear()
        self.render_all()
        self.add_message("bot", GREETING)

    def save_chat(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("Text file", "*.txt")], initialfile="chat_history.txt",
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            for sender, text, stamp in self.messages:
                who = "You" if sender == "user" else BOT_NAME
                f.write(f"[{stamp}] {who}: {text}\n")
        messagebox.showinfo("Saved", "Chat saved!")


if __name__ == "__main__":
    root = tk.Tk()
    ChatApp(root)
    root.mainloop()
