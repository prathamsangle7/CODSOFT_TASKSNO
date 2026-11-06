"""
CodSoft AI Internship - Task 2: Tic-Tac-Toe AI (Minimax + Alpha-Beta Pruning)

The board is a list of 9 cells:   0 | 1 | 2
                                  3 | 4 | 5
                                  6 | 7 | 8
Each cell is "X", "O" or " " (empty).

Run in terminal:   python tictactoe_ai.py
Run with a window: python tictactoe_gui.py
"""

import random
from typing import List, Optional, Tuple

EMPTY = " "
INF = float("inf")

WIN_LINES = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),      # rows
    (0, 3, 6), (1, 4, 7), (2, 5, 8),      # columns
    (0, 4, 8), (2, 4, 6),                 # diagonals
]


# --------------------------------------------------------------------------
# Game helpers
# --------------------------------------------------------------------------

def winning_line(board: List[str]) -> Optional[Tuple[int, int, int]]:
    """Return the three winning cells, or None."""
    for a, b, c in WIN_LINES:
        if board[a] != EMPTY and board[a] == board[b] == board[c]:
            return (a, b, c)
    return None


def check_winner(board: List[str]) -> Optional[str]:
    line = winning_line(board)
    return board[line[0]] if line else None


def is_full(board: List[str]) -> bool:
    return EMPTY not in board


def available_moves(board: List[str]) -> List[int]:
    return [i for i, cell in enumerate(board) if cell == EMPTY]


# --------------------------------------------------------------------------
# Minimax with optional Alpha-Beta pruning
# --------------------------------------------------------------------------

def minimax(board, depth, is_maximizing, ai, human, alpha, beta, use_pruning, counter):
    """
    Returns a score for this position:
      +10 - depth  -> AI wins (faster wins score higher)
      depth - 10   -> human wins (slower losses score higher)
      0            -> draw
    counter[0] counts how many positions were looked at.
    """
    counter[0] += 1

    winner = check_winner(board)
    if winner == ai:
        return 10 - depth
    if winner == human:
        return depth - 10
    if is_full(board):
        return 0

    if is_maximizing:                       # AI's turn: pick the highest score
        best = -INF
        for move in available_moves(board):
            board[move] = ai
            score = minimax(board, depth + 1, False, ai, human, alpha, beta, use_pruning, counter)
            board[move] = EMPTY
            best = max(best, score)
            if use_pruning:
                alpha = max(alpha, best)
                if beta <= alpha:           # the human would never allow this branch
                    break
        return best

    best = INF                              # human's turn: assume they pick the lowest score
    for move in available_moves(board):
        board[move] = human
        score = minimax(board, depth + 1, True, ai, human, alpha, beta, use_pruning, counter)
        board[move] = EMPTY
        best = min(best, score)
        if use_pruning:
            beta = min(beta, best)
            if beta <= alpha:
                break
    return best


def best_move(board, ai, human, use_pruning=True) -> Tuple[int, int]:
    """Return (best cell, positions looked at). Ties are broken randomly."""
    counter = [0]
    best_score = -INF
    best_cells = []
    for move in available_moves(board):
        board[move] = ai
        score = minimax(board, 1, False, ai, human, -INF, INF, use_pruning, counter)
        board[move] = EMPTY
        if score > best_score:
            best_score, best_cells = score, [move]
        elif score == best_score:
            best_cells.append(move)
    return random.choice(best_cells), counter[0]


def choose_move(board, ai, human, difficulty="hard", use_pruning=True) -> Tuple[int, int]:
    """Pick a move for the given difficulty: easy, medium or hard (unbeatable)."""
    moves = available_moves(board)
    if difficulty == "easy":
        return random.choice(moves), 0
    if difficulty == "medium" and random.random() < 0.4:
        return random.choice(moves), 0       # 40% of the time, play randomly
    return best_move(board, ai, human, use_pruning)


# --------------------------------------------------------------------------
# Terminal game
# --------------------------------------------------------------------------

def print_board(board):
    rows = []
    for r in range(3):
        cells = [board[r * 3 + c] if board[r * 3 + c] != EMPTY else str(r * 3 + c + 1) for c in range(3)]
        rows.append(" " + " | ".join(cells))
    print("\n" + "\n---+---+---\n".join(rows) + "\n")


def main():
    print("Tic-Tac-Toe AI (Minimax + Alpha-Beta). You are X, the AI is O.")
    print("Pick a square with 1-9.\n")
    human, ai = "X", "O"
    board = [EMPTY] * 9
    human_turn = input("Do you want to go first? (y/n): ").strip().lower() != "n"
    if not human_turn:
        human, ai = "O", "X"
        print("OK, the AI goes first and plays X. You are O.")

    while True:
        print_board(board)
        if human_turn:
            try:
                move = int(input(f"Your move ({human}), 1-9: ")) - 1
            except ValueError:
                print("Please type a number from 1 to 9.")
                continue
            if move not in range(9) or board[move] != EMPTY:
                print("That square is not available. Try again.")
                continue
            board[move] = human
        else:
            move, nodes = best_move(board, ai, human)
            board[move] = ai
            print(f"AI plays {move + 1}  (looked at {nodes:,} positions)")

        winner = check_winner(board)
        if winner or is_full(board):
            print_board(board)
            if winner == human:
                print("You win! 🎉  (this should never happen...)")
            elif winner == ai:
                print("The AI wins! 🤖")
            else:
                print("It's a draw! 🤝  (the best you can do against a perfect AI)")
            break
        human_turn = not human_turn


if __name__ == "__main__":
    main()
