An unbeatable Tic-Tac-Toe player using **Minimax with Alpha-Beta pruning**. Built in Python for the CodSoft AI internship.

## Features
- Minimax AI that never loses (verified against every possible game)
- Alpha-Beta pruning toggle: about 94% fewer positions searched on the opening move
- 3 difficulty levels: Easy, Medium, Hard
- Tkinter GUI with scoreboard, hover highlight and winning line
- Terminal version too

## How it works
1. The AI tries every possible move and plays out the rest of the game
2. It assumes the human always plays their best move
3. Wins score +10, losses -10, draws 0 (faster wins score higher)
4. Alpha-Beta skips branches that cannot change the result

## Run
python tictactoe_gui.py   # GUI version
python tictactoe_ai.py    # terminal version

Only Python 3 is needed.
