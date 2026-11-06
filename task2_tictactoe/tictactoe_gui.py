"""
CodSoft AI Internship - Task 2: Tic-Tac-Toe AI GUI (Tkinter)

Play against an AI that uses Minimax with Alpha-Beta pruning.
Features: 3 difficulty levels, scoreboard, hover highlight, winning-line highlight,
choose who starts, and a live "positions looked at" counter (toggle pruning to compare!).

Keep this file in the same folder as tictactoe_ai.py
Run:  python tictactoe_gui.py
"""

import tkinter as tk

from tictactoe_ai import EMPTY, check_winner, choose_move, is_full, winning_line

C = dict(
    bg="#0b1220", panel="#111a2e", card="#1e293b", text="#e2e8f0", muted="#94a3b8",
    grid="#334155", hover="#1e293b", x="#38bdf8", o="#f472b6", win="#facc15",
    good="#4ade80", bad="#f87171", accent="#22d3ee",
)
FONT = "Segoe UI"
LEVELS = {"Easy": "easy", "Medium": "medium", "Hard (unbeatable)": "hard"}
STARTS = ["You start", "AI starts", "Alternate"]


class TicTacToeApp:
    CELL = 120
    SIZE = CELL * 3

    def __init__(self, root):
        self.root = root
        root.title("Tic-Tac-Toe AI · Minimax")
        root.configure(bg=C["bg"])
        root.resizable(False, False)

        self.score = {"you": 0, "draw": 0, "ai": 0}
        self.board = [EMPTY] * 9
        self.human, self.ai = "X", "O"
        self.human_turn = True
        self.game_over = False
        self.win_cells = None
        self.hover = None
        self.next_starter = "you"
        self.ai_job = None

        self.build_ui()
        self.new_game()

    # ------------------------------------------------------------------ UI
    def build_ui(self):
        tk.Label(self.root, text="❌⭕  Tic-Tac-Toe AI", font=(FONT, 18, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(pady=(14, 0))
        tk.Label(self.root, text="Minimax + Alpha-Beta Pruning", font=(FONT, 10),
                 bg=C["bg"], fg=C["muted"]).pack()

        # Scoreboard
        board_row = tk.Frame(self.root, bg=C["bg"])
        board_row.pack(pady=12)
        self.score_labels = {}
        for key, title, color in (("you", "You", C["x"]), ("draw", "Draws", C["muted"]), ("ai", "AI", C["o"])):
            card = tk.Frame(board_row, bg=C["card"], padx=22, pady=6)
            card.pack(side="left", padx=6)
            tk.Label(card, text=title, font=(FONT, 9), bg=C["card"], fg=C["muted"]).pack()
            lbl = tk.Label(card, text="0", font=(FONT, 18, "bold"), bg=C["card"], fg=color)
            lbl.pack()
            self.score_labels[key] = lbl

        self.status = tk.Label(self.root, text="", font=(FONT, 13, "bold"), bg=C["bg"], fg=C["text"])
        self.status.pack(pady=(0, 8))

        # Board
        self.canvas = tk.Canvas(self.root, width=self.SIZE, height=self.SIZE, bg=C["panel"],
                                highlightthickness=0, cursor="hand2")
        self.canvas.pack(padx=20)
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<Leave>", self.on_leave)

        self.info = tk.Label(self.root, text="", font=(FONT, 10), bg=C["bg"], fg=C["muted"])
        self.info.pack(pady=(10, 4))

        # Settings
        settings = tk.Frame(self.root, bg=C["bg"])
        settings.pack(pady=6)
        self.level_var = tk.StringVar(value="Hard (unbeatable)")
        self.start_var = tk.StringVar(value=STARTS[0])
        self.prune_var = tk.BooleanVar(value=True)
        self.make_menu(settings, "Level", self.level_var, list(LEVELS)).grid(row=0, column=0, padx=6)
        self.make_menu(settings, "Start", self.start_var, STARTS).grid(row=0, column=1, padx=6)
        tk.Checkbutton(
            self.root, text="Alpha-Beta pruning ON", variable=self.prune_var, bg=C["bg"], fg=C["text"],
            selectcolor=C["card"], activebackground=C["bg"], activeforeground=C["text"], font=(FONT, 10),
            bd=0, highlightthickness=0, cursor="hand2",
        ).pack()

        # Buttons
        buttons = tk.Frame(self.root, bg=C["bg"])
        buttons.pack(pady=(10, 16))
        self.make_button(buttons, "New game", self.new_game, C["accent"], "#0b1220").pack(side="left", padx=6)
        self.make_button(buttons, "Reset score", self.reset_score, C["card"], C["text"]).pack(side="left", padx=6)

    def make_menu(self, parent, label, var, options):
        frame = tk.Frame(parent, bg=C["bg"])
        tk.Label(frame, text=label, font=(FONT, 9), bg=C["bg"], fg=C["muted"]).pack(anchor="w")
        menu = tk.OptionMenu(frame, var, *options)
        menu.config(bg=C["card"], fg=C["text"], activebackground=C["grid"], activeforeground=C["text"],
                    bd=0, highlightthickness=0, font=(FONT, 10), width=16, cursor="hand2")
        menu["menu"].config(bg=C["card"], fg=C["text"], font=(FONT, 10))
        menu.pack()
        return frame

    def make_button(self, parent, text, command, bg, fg):
        return tk.Button(parent, text=text, command=command, bg=bg, fg=fg, bd=0, font=(FONT, 11, "bold"),
                         padx=16, pady=7, cursor="hand2", activebackground=bg, activeforeground=fg)

    # ------------------------------------------------------------- drawing
    def draw(self):
        c, S, CELL = self.canvas, self.SIZE, self.CELL
        c.delete("all")

        if (self.hover is not None and self.human_turn and not self.game_over
                and self.board[self.hover] == EMPTY):
            r, col = divmod(self.hover, 3)
            c.create_rectangle(col * CELL + 6, r * CELL + 6, (col + 1) * CELL - 6, (r + 1) * CELL - 6,
                               fill=C["hover"], outline="")

        for i in (1, 2):
            c.create_line(i * CELL, 14, i * CELL, S - 14, fill=C["grid"], width=4, capstyle="round")
            c.create_line(14, i * CELL, S - 14, i * CELL, fill=C["grid"], width=4, capstyle="round")

        for i, mark in enumerate(self.board):
            if mark != EMPTY:
                self.draw_mark(i, mark)

        if self.win_cells:
            (r1, c1), (r2, c2) = divmod(self.win_cells[0], 3), divmod(self.win_cells[2], 3)
            c.create_line(c1 * CELL + CELL / 2, r1 * CELL + CELL / 2,
                          c2 * CELL + CELL / 2, r2 * CELL + CELL / 2,
                          fill=C["win"], width=7, capstyle="round")

    def draw_mark(self, index, mark):
        c, CELL, pad = self.canvas, self.CELL, 32
        r, col = divmod(index, 3)
        x0, y0 = col * CELL, r * CELL
        x1, y1 = x0 + CELL, y0 + CELL
        if mark == "X":
            c.create_line(x0 + pad, y0 + pad, x1 - pad, y1 - pad, fill=C["x"], width=11, capstyle="round")
            c.create_line(x0 + pad, y1 - pad, x1 - pad, y0 + pad, fill=C["x"], width=11, capstyle="round")
        else:
            c.create_oval(x0 + pad - 2, y0 + pad - 2, x1 - pad + 2, y1 - pad + 2, outline=C["o"], width=11)

    # -------------------------------------------------------------- events
    def cell_at(self, x, y):
        if 0 <= x < self.SIZE and 0 <= y < self.SIZE:
            return (y // self.CELL) * 3 + (x // self.CELL)
        return None

    def on_motion(self, event):
        cell = self.cell_at(event.x, event.y)
        if cell != self.hover:
            self.hover = cell
            self.draw()

    def on_leave(self, event):
        self.hover = None
        self.draw()

    def on_click(self, event):
        if self.game_over or not self.human_turn:
            return
        cell = self.cell_at(event.x, event.y)
        if cell is None or self.board[cell] != EMPTY:
            return

        self.board[cell] = self.human
        self.human_turn = False
        if self.check_end():
            return
        self.set_status("AI is thinking…", C["muted"])
        self.draw()
        self.ai_job = self.root.after(450, self.ai_move)

    # ---------------------------------------------------------------- game
    def ai_move(self):
        self.ai_job = None
        if self.game_over:
            return
        level = LEVELS[self.level_var.get()]
        use_pruning = self.prune_var.get()
        move, nodes = choose_move(self.board, self.ai, self.human, level, use_pruning)
        self.board[move] = self.ai

        if nodes:
            mode = "alpha-beta ON" if use_pruning else "pruning OFF"
            self.info.config(text=f"🧠 AI looked at {nodes:,} positions  ({mode})")
        else:
            self.info.config(text="🎲 AI played a random move")

        if self.check_end():
            return
        self.human_turn = True
        self.set_status(f"Your turn ({self.human})", C["text"])
        self.draw()

    def check_end(self):
        winner = check_winner(self.board)
        if winner:
            self.win_cells = winning_line(self.board)
            if winner == self.human:
                self.score["you"] += 1
                self.set_status("You win! 🎉", C["good"])
            else:
                self.score["ai"] += 1
                self.set_status("AI wins 🤖", C["bad"])
        elif is_full(self.board):
            self.score["draw"] += 1
            self.set_status("It's a draw 🤝", C["win"])
        else:
            return False
        self.game_over = True
        self.update_score()
        self.draw()
        return True

    def new_game(self):
        if self.ai_job:
            self.root.after_cancel(self.ai_job)
            self.ai_job = None
        self.board = [EMPTY] * 9
        self.game_over = False
        self.win_cells = None
        self.hover = None

        choice = self.start_var.get()
        if choice == "Alternate":
            starter, self.next_starter = self.next_starter, ("ai" if self.next_starter == "you" else "you")
        else:
            starter = "you" if choice == "You start" else "ai"

        if starter == "you":                      # whoever starts plays X
            self.human, self.ai = "X", "O"
            self.human_turn = True
            self.set_status("Your turn (X)", C["text"])
            self.info.config(text="Pick a square to start")
        else:
            self.human, self.ai = "O", "X"
            self.human_turn = False
            self.set_status("AI is thinking…", C["muted"])
            self.info.config(text="The AI starts this round")
            self.ai_job = self.root.after(500, self.ai_move)
        self.update_score()
        self.draw()

    def reset_score(self):
        self.score = {"you": 0, "draw": 0, "ai": 0}
        self.update_score()

    def update_score(self):
        for key, label in self.score_labels.items():
            label.config(text=str(self.score[key]))

    def set_status(self, text, color):
        self.status.config(text=text, fg=color)


if __name__ == "__main__":
    root = tk.Tk()
    TicTacToeApp(root)
    root.mainloop()
