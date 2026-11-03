# Task 1: Rule-Based Chatbot
# Task 1: Rule-Based Chatbot

A chatbot (Cody) that replies using regex pattern matching. Built in Python for the CodSoft AI internship.

## Features
- 60+ rules: greetings, small talk, time and date, jokes, facts, quotes
- Answers tech questions (AI, ML, NLP, minimax, Python and more)
- Safe calculator: `12 x 7`, `what is 100 / 8`
- Typo tolerance with fuzzy matching (`helo`, `joek`)
- Remembers your name during the chat
- Tkinter GUI with chat bubbles, quick-reply buttons and dark/light theme

## How it works
1. Clean the text (lowercase, no punctuation)
2. Try the calculator
3. Check the rules top to bottom, first regex match wins
4. If nothing matches, try fuzzy matching, then a fallback reply

## Run
python chatbot.py        # terminal version
python chatbot_gui.py    # GUI version

No extra libraries needed, only Python 3.
