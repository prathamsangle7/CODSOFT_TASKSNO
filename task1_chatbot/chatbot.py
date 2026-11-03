"""
CodSoft AI Internship - Task 1: Rule-Based Chatbot (v2)

How it works:
  1. Clean the user's text (lowercase, no punctuation, no stretched letters)
  2. Try the calculator (so "12 * 7" just works)
  3. Check the RULES list top to bottom. First regex match wins.
  4. If no rule matches, try fuzzy matching to catch typos ("helo", "joek")
  5. Still nothing? Use a friendly fallback.

Run in terminal:  python chatbot.py
Run with a window: python chatbot_gui.py
"""

import ast
import difflib
import operator
import random
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, List, Optional

BOT_NAME = "Cody"
EXIT = "__EXIT__"

# (button label, message it sends) - used by the GUI quick-reply buttons
SUGGESTIONS = [
    ("😂 Joke", "tell me a joke"),
    ("⏰ Time", "what time is it"),
    ("💡 Fun fact", "tell me a fun fact"),
    ("🤖 What is AI?", "what is ai"),
    ("🧮 12 x 7", "12 x 7"),
    ("❓ Help", "help"),
]

# --------------------------------------------------------------------------
# Content
# --------------------------------------------------------------------------

JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs. 🐛",
    "There are 10 types of people: those who understand binary and those who don't.",
    "A SQL query walks into a bar, sees two tables and asks: 'Can I join you?'",
    "Why did the developer go broke? He used up all his cache.",
    "I would tell you a UDP joke, but you might not get it.",
    "Why was the computer cold? It left its Windows open. 🪟",
    "How many programmers does it take to change a light bulb? None, that's a hardware problem.",
    "Why do Java developers wear glasses? Because they don't C#.",
    "My code has no bugs, only surprise features. ✨",
    "What's a computer's favourite snack? Microchips. 🍟",
]

FACTS = [
    "The first computer 'bug' was a real moth found in a Harvard Mark II relay in 1947. 🦋",
    "The term 'Artificial Intelligence' was coined by John McCarthy and colleagues in 1955, ahead of the 1956 Dartmouth workshop.",
    "Python is named after the comedy group Monty Python, not the snake. 🐍",
    "IBM's Deep Blue beat world chess champion Garry Kasparov in 1997. ♟️",
    "One of the earliest computer games was a Tic-Tac-Toe program called OXO, written for the EDSAC computer in 1952. ❌⭕",
    "A day on Venus is longer than its year. 🪐",
    "Octopuses have three hearts. 🐙",
    "Botanically, bananas are berries but strawberries are not. 🍌",
]

QUOTES = [
    "Small steps every day beat big plans someday. 🚶",
    "Bugs are just lessons wearing a disguise. Keep debugging! 🔧",
    "You don't have to be great to start, but you have to start to be great. 🚀",
    "Progress, not perfection. Ship it, then improve it. 📦",
    "Every expert was once a beginner who refused to quit. 💪",
    "Consistency beats intensity. Even 30 minutes a day adds up. ⏳",
]

FALLBACKS = [
    "Hmm, I didn't get that. Can you rephrase? 🤔",
    "I'm still learning! Try asking about the time, a joke, or AI.",
    "That's outside my rules for now. Type 'help' to see what I can do.",
    "Not sure what you mean. Maybe ask me for a fun fact? 💡",
]

HELP_TEXT = (
    "Here's what I can do:\n"
    "• Chat: hello, how are you, thanks\n"
    "• Info: time, date, 'what is AI / ML / NLP / Python...'\n"
    "• Fun: jokes, fun facts, quotes, flip a coin, roll a dice\n"
    "• Math: try '25 * 4' or 'what is 100 / 8'\n"
    "• Personal: tell me 'my name is ...' and I'll remember it\n"
    "• Say 'bye' to exit"
)

NOT_NAMES = {"later", "back", "now", "please", "maybe", "when", "if", "tomorrow", "today", "soon", "again"}


# --------------------------------------------------------------------------
# Safe calculator (no eval!)
# --------------------------------------------------------------------------

_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv, ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("power too big")
        return _OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("unsupported")


def try_math(raw: str) -> Optional[str]:
    """Return an answer string if the message is a math expression, else None."""
    t = raw.lower().strip().rstrip("?=!. ")
    t = re.sub(r"^(please |can you |could you )?(calculate|calc|compute|solve|evaluate|what is|whats|what's|tell me)\s*", "", t)
    t = f" {t} "
    words = {
        " to the power of ": " ** ", " multiplied by ": " * ", " divided by ": " / ",
        " plus ": " + ", " minus ": " - ", " times ": " * ", " into ": " * ",
        " over ": " / ", " mod ": " % ",
    }
    for word, symbol in words.items():
        t = t.replace(word, symbol)
    t = t.replace("×", "*").replace("÷", "/").replace("^", "**")
    t = re.sub(r"(?<=\d)\s*x\s*(?=\d)", "*", t).strip()

    if len(t) > 60 or not re.fullmatch(r"[\d\s.+\-*/%()]+", t):
        return None
    if not re.search(r"\d[\s)]*[+\-*/%]+[\s(]*[\d.]", t):
        return None
    try:
        result = _eval(ast.parse(t, mode="eval"))
    except ZeroDivisionError:
        return "I can't divide by zero 😅 (nobody can)."
    except Exception:
        return None
    if isinstance(result, float):
        result = int(result) if result.is_integer() else round(result, 6)
    tokens = re.findall(r"\*\*|\d+\.?\d*|\.\d+|[+\-*/%()]", t)
    shown = " ".join(tokens).replace("( ", "(").replace(" )", ")").replace("**", "^")
    return f"{shown} = {result} 🧮"


# --------------------------------------------------------------------------
# Rules
# --------------------------------------------------------------------------

@dataclass
class Rule:
    name: str
    patterns: List[str]
    replies: List[str] = field(default_factory=list)
    handler: Optional[Callable] = None       # handler(bot, text) -> str
    examples: List[str] = field(default_factory=list)   # used for typo matching
    repeatable: bool = False                  # "another one" can repeat it


# ---- handlers (rules that need code, not just a fixed reply) ----

def h_time(bot, text):
    return f"It's {datetime.now().strftime('%I:%M %p').lstrip('0')} right now. ⏰"


def h_date(bot, text):
    return f"Today is {datetime.now().strftime('%A, %d %B %Y')}. 📅"


def h_set_name(bot, text):
    m = re.search(r"\b(?:my name is|call me|i am called|im called)\s+([a-z]+)", text)
    name = m.group(1) if m else ""
    if not name or name in NOT_NAMES:
        return "Sure! What should I call you? Say 'my name is ...'"
    bot.user_name = name.title()
    return random.choice([
        f"Nice to meet you, {bot.user_name}! 🙂",
        f"Great name, {bot.user_name}! I'll remember it for this chat.",
        f"Hey {bot.user_name}! Good to meet you.",
    ])


def h_get_name(bot, text):
    if bot.user_name:
        return f"You're {bot.user_name}! 😎"
    return "I don't know yet! Tell me with 'my name is ...'"


def h_reset(bot, text):
    bot.user_name = None
    bot.last_rule = None
    return "Done, I've forgotten everything. Fresh start! 🧹"


def h_coin(bot, text):
    return random.choice(["Heads! 🪙", "Tails! 🪙"])


def h_dice(bot, text):
    return f"You rolled a {random.randint(1, 6)}! 🎲"


def h_number(bot, text):
    return f"Your random number is {random.randint(1, 100)}. 🎯"


def h_stats(bot, text):
    return f"We've exchanged {bot.message_count} messages so far. 💬"


def h_greet(bot, text):
    m = re.search(r"\bgood (morning|afternoon|evening)\b", text)
    opener = m.group(0).capitalize() if m else random.choice(["Hey", "Hello", "Hi"])
    return f"{opener}, {bot.display_name}! 👋 What's on your mind?"


def h_another(bot, text):
    if bot.last_rule:
        return bot.reply_for(bot.last_rule, text)
    return "Another what? Ask me for a joke, fact or quote first! 😄"


def h_help(bot, text):
    return HELP_TEXT


def h_bye(bot, text):
    return EXIT


def explain(name: str, term: str, answer: str) -> Rule:
    """Build a 'what is X?' rule."""
    verbs = r"what is|whats|what are|what does|define|explain|tell me about|meaning of|know about|describe"
    return Rule(
        name=name,
        patterns=[rf"\b(?:{verbs})\b.*\b(?:{term})\b", rf"^(?:{term})$"],
        replies=[answer],
    )


RULES: List[Rule] = [
    Rule("bye", [r"\b(bye|goodbye|see you|see ya|good night|quit|exit|cya)\b"],
         handler=h_bye, examples=["goodbye", "bye bye"]),
    Rule("set_name", [r"\b(my name is|call me|i am called|im called)\b"], handler=h_set_name),
    Rule("get_name", [r"\b(what is|whats) my name\b", r"\bdo you (know|remember) my name\b", r"\bwho am i\b"],
         handler=h_get_name),
    Rule("reset", [r"^(reset|forget me|forget my name|start over)$"], handler=h_reset),

    # ---- about the bot ----
    Rule("how_are_you", [r"\bhow are (you|u)\b", r"\bhow is it going\b", r"\bhows it going\b",
                         r"\bhow do you do\b", r"\bhow have you been\b", r"\bwhats up\b", r"\bhow you doing\b"],
         ["Doing great, thanks for asking! How about you, {name}? 😊",
          "All systems running smoothly! 🟢 How are you?",
          "Pretty good for a bunch of if-statements! You?"],
         examples=["how are you", "how are you doing"]),
    Rule("bot_name", [r"\b(what is|whats) your name\b", r"\bwho are you\b", r"\byour name\b",
                      r"\bintroduce yourself\b", r"\babout yourself\b"],
         [f"I'm {BOT_NAME}, a rule-based chatbot. Nice to meet you, {{name}}! 🤖"],
         examples=["what is your name", "who are you"]),
    Rule("creator", [r"\bwho (made|created|built|developed|designed|programmed) you\b",
                     r"\byour (creator|developer|maker)\b"],
         ["I was built in Python as a Task 1 project for the CodSoft AI internship. 🛠️"]),
    Rule("age", [r"\bhow old are you\b", r"\byour age\b"],
         ["I'm brand new, born the day my first line of code ran. 🐣"]),
    Rule("is_human", [r"\bare you (a |an )?(human|real|robot|bot|person|ai|machine|alive|chatbot)\b"],
         ["I'm a chatbot, a rule-based one. No human here, just Python and regex! 🤖"]),
    Rule("location", [r"\bwhere (do you live|are you from|are you)\b"],
         ["I live inside your computer, rent-free! 🏠"]),
    Rule("how_it_works", [r"\bhow do you (work|think|reply|respond|know)\b",
                          r"\bhow were you (made|built|created|programmed)\b"],
         ["Simple! I clean your message, check it against a list of patterns (regex), and reply "
          "from the first rule that matches. If nothing matches, I try fuzzy matching for typos, "
          "and then a fallback."]),
    Rule("feelings", [r"\bdo you (feel|have feelings|have emotions|dream|sleep|eat|get tired)\b"],
         ["Nope! No feelings, no sleep, no snacks, just patterns and replies. Pretty chill life. 😎"]),
    Rule("language", [r"\b(what|which) (programming )?language\b.*\b(you|your)\b", r"\bwritten in\b",
                      r"\bwhat are you coded in\b"],
         ["My brain is Python 🐍 and my chat window is Tkinter."]),

    # ---- tech knowledge ----
    explain("k_ai", r"ai|artificial intelligence",
            "AI (Artificial Intelligence) is about making machines do things that normally need human "
            "intelligence, like understanding language, recognising images, or making decisions."),
    explain("k_ml", r"ml|machine learning",
            "Machine learning is a part of AI where models learn patterns from data instead of being "
            "given every rule by hand."),
    explain("k_dl", r"deep learning|dl",
            "Deep learning is machine learning with neural networks that have many layers. It powers "
            "image recognition, speech assistants and more."),
    explain("k_nn", r"neural networks?|neural nets?",
            "A neural network is a set of connected 'neurons' (small math functions) arranged in layers. "
            "It learns by adjusting the connection weights from examples."),
    explain("k_nlp", r"nlp|natural language processing",
            "NLP (Natural Language Processing) is how computers understand and generate human language. "
            "Chatbots, translation and spam filters all use it."),
    explain("k_cv", r"computer vision",
            "Computer vision teaches computers to understand images and video, like face detection, "
            "object detection, or reading text from photos."),
    explain("k_chatbot", r"chat ?bots?",
            "A chatbot is a program that holds a conversation. I'm a rule-based one: I match your text "
            "against patterns and reply with pre-written answers."),
    explain("k_turing", r"turing test",
            "The Turing Test, proposed by Alan Turing in 1950, asks whether a machine can chat so well "
            "that a human can't tell it's a machine."),
    explain("k_minimax", r"minimax|min max",
            "Minimax is a game algorithm: it looks ahead at every possible move, assumes the opponent plays "
            "perfectly, and picks the move with the best worst-case result. It makes a Tic-Tac-Toe AI unbeatable!"),
    explain("k_python", r"python",
            "Python is a beginner-friendly programming language, hugely popular in AI and data science. "
            "Fun fact: it's named after Monty Python."),
    explain("k_github", r"github|git hub",
            "GitHub is a website for hosting code with Git version control. Think of it as a portfolio "
            "and a time machine for your projects."),
    explain("k_regex", r"regex|regular expressions?",
            "A regex (regular expression) is a pattern for matching text. It's what I use to understand your messages!"),
    explain("k_algo", r"algorithms?",
            "An algorithm is a step-by-step set of instructions to solve a problem, like a recipe for computers."),
    explain("k_ds", r"data science",
            "Data science uses statistics and programming to find useful insights in data."),
    explain("k_llm", r"llms?|large language models?",
            "LLMs (Large Language Models) are AI models trained on huge amounts of text so they can "
            "understand and generate language."),
    explain("k_opencv", r"opencv|open cv",
            "OpenCV is a popular open-source library for computer vision: face detection, image processing and more."),
    Rule("internship", [r"\b(codsoft|internship)\b"],
         ["CodSoft runs virtual tech internships, and I'm a Task 1 project from the AI one: "
          "a chatbot built on rules and pattern matching. 🚀"]),

    # ---- utilities ----
    Rule("time", [r"\bwhat time\b", r"\bcurrent time\b", r"\btell me the time\b", r"\btime now\b",
                  r"\bwhats the time\b", r"^time$"],
         handler=h_time, examples=["what time is it", "current time"]),
    Rule("date", [r"\bwhats the date\b", r"\btodays date\b", r"\bwhat day\b", r"\bcurrent date\b",
                  r"^date$", r"^today$", r"\bwhich day\b", r"\bwhat is today\b"],
         handler=h_date, examples=["what is the date", "what day is it"]),
    Rule("joke", [r"\bjokes?\b", r"\bmake me laugh\b", r"\bsomething funny\b"],
         JOKES, repeatable=True, examples=["tell me a joke", "joke"]),
    Rule("fact", [r"\bfun fact\b", r"\bfacts?\b", r"\bsomething interesting\b", r"\btell me something\b"],
         FACTS, repeatable=True, examples=["fun fact", "tell me a fact"]),
    Rule("quote", [r"\bquotes?\b", r"\bmotivat", r"\binspire\b", r"\bencourage me\b", r"\bcheer me up\b"],
         QUOTES, repeatable=True, examples=["motivate me", "give me a quote"]),
    Rule("coin", [r"\b(flip|toss) (a )?coin\b", r"\bheads or tails\b"], handler=h_coin, repeatable=True),
    Rule("dice", [r"\b(roll|throw) (a )?(dice|die)\b"], handler=h_dice, repeatable=True),
    Rule("number", [r"\brandom number\b"], handler=h_number, repeatable=True),
    Rule("weather", [r"\bweather\b", r"\btemperature\b", r"\braining\b"],
         ["I can't check live weather, I run offline! A weather app will do a better job. ☁️"]),
    Rule("stats", [r"\bhow many (messages|questions)\b", r"^stats$"], handler=h_stats),

    # ---- favourites & opinions ----
    Rule("fav_language", [r"\b(best|favou?rite) (programming )?language\b"],
         ["Python, obviously! 🐍 (Though every language has its fans.)"]),
    Rule("fav_color", [r"\bfavou?rite colou?r\b"], ["Electric blue, obviously. 💙"]),
    Rule("favorite", [r"\bfavou?rite\b"],
         ["I don't eat, watch or play, but I do love clean code and a good regex. 😄"]),

    # ---- moods ----
    Rule("sad", [r"\b(im|i am|feeling|feel) (so |very |really )?(sad|unhappy|upset|lonely|depressed|low|down)\b"],
         ["I'm sorry you're feeling this way, {name}. 💙 Talking to a friend or someone you trust can really "
          "help. I'm just a simple bot, but I'm happy to listen, or cheer you up with a joke if you like."]),
    Rule("happy", [r"\b(im|i am|feeling|feel) (so |very |really )?(happy|great|good|awesome|excited|fine|amazing|fantastic)\b"],
         ["That's awesome, {name}! 🎉 Love the energy.", "Yay! Glad to hear it. 😄"]),
    Rule("bored", [r"\b(im|i am) (so |very |really )?bored\b", r"\bnothing to do\b"],
         ["Bored? Let's fix that: ask me for a joke, a fun fact, flip a coin, or try a math question! 🎲"]),
    Rule("tired", [r"\b(im|i am) (so |very |really )?(tired|sleepy|exhausted|stressed|anxious|overwhelmed)\b"],
         ["That sounds rough, {name}. Take a short break, drink some water, and breathe. You've got this. 💧"]),
    Rule("study", [r"\b(exam|exams|homework|assignment|assignments|college|university|semester|studying|study tips?)\b"],
         ["Study tip: work in 25-minute focus blocks with 5-minute breaks (Pomodoro). You've got this! 📚",
          "Break big assignments into tiny tasks. Starting is the hardest part. 💪"]),

    # ---- politeness & feelings ----
    Rule("thanks", [r"\b(thanks|thank you|thx|ty|thankyou)\b"],
         ["You're welcome, {name}! 😊", "Anytime!", "No problem at all!"], examples=["thank you", "thanks"]),
    Rule("sorry", [r"\b(sorry|my bad|apologies)\b"],
         ["No worries at all! 🙂", "All good, no need to apologise!"]),
    Rule("compliment", [r"\b(you are|youre|ur) (so |very |really )?(smart|good|great|awesome|amazing|cool|nice|best|funny|helpful|cute)\b",
                        r"\bgood bot\b", r"\bwell done\b", r"\bnice work\b"],
         ["Aw, thanks! You're pretty great yourself. 😄", "You're making my circuits blush! 🔥"]),
    Rule("insult", [r"\b(stupid|dumb|idiot|useless|hate you|shut up|worst)\b"],
         ["Ouch! 😅 I'm only a simple rule-based bot, but I'm trying my best. Try 'help' to see what I do well."]),
    Rule("love", [r"\bi love you\b", r"\bdo you love me\b"],
         ["Aww, that's sweet! 💙 I'm just a bot, but I'm glad you like chatting with me."]),

    # ---- context & help ----
    Rule("another", [r"^(another|another one|again|more|one more|next|tell me more)$"], handler=h_another),
    Rule("help", [r"^(help|menu|commands|options)$", r"\bwhat can you do\b", r"\bhow can you help\b",
                  r"\bwhat do you know\b", r"\bneed help\b", r"\bcan you help\b"],
         handler=h_help, examples=["help", "what can you do"]),

    # ---- greetings last, so "hi, what time is it" gets the time ----
    Rule("greeting", [r"\b(hi|hello|hey|hii|yo|hola|namaste|sup|wassup|whatsup)\b", r"\bgood (morning|afternoon|evening)\b"],
         handler=h_greet, examples=["hello", "good morning", "hi there"]),

    # ---- tiny reactions ----
    Rule("ack", [r"^(ok|okay|k|cool|nice|great|alright|hm+|oh|wow|ah+|sure thing)$"],
         ["👍", "Cool!", "Got it!"]),
    Rule("yes", [r"^(yes|yeah|yep|yup|sure)$"], ["Great! 😄 What would you like to do next?"]),
    Rule("no", [r"^(no|nope|nah)$"], ["No problem! Let me know if you change your mind. 🙂"]),
    Rule("laugh", [r"^((ha)+h?|lol|lmao|hehe|rofl)$"], ["😄", "Glad I made you smile!", "😂"]),
]

# phrase -> rule, used for typo matching
_FUZZY = {}
for _rule in RULES:
    for _ex in _rule.examples:
        _FUZZY[_ex] = _rule


# --------------------------------------------------------------------------
# The bot
# --------------------------------------------------------------------------

def clean(text: str) -> str:
    """Lowercase, drop apostrophes/punctuation, squash stretched letters (heyyy -> hey)."""
    text = text.lower().replace("’", "'").replace("'", "")
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"(.)\1{2,}", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


class Chatbot:
    def __init__(self):
        self.user_name: Optional[str] = None
        self.last_rule: Optional[Rule] = None
        self.last_reply = {}
        self.fallback_streak = 0
        self.message_count = 0

    @property
    def display_name(self) -> str:
        return self.user_name or "friend"

    def respond(self, raw: str) -> str:
        self.message_count += 1

        math = try_math(raw)
        if math:
            self.fallback_streak = 0
            return math

        text = clean(raw)
        if not text:
            return "Say something! 😄"

        rule = self._match(text) or self._fuzzy(text)
        if rule is None:
            return self._fallback()

        self.fallback_streak = 0
        reply = self.reply_for(rule, text)
        if rule.repeatable:
            self.last_rule = rule
        return reply

    # ---- internals ----
    def _match(self, text: str) -> Optional[Rule]:
        for rule in RULES:
            if any(re.search(p, text) for p in rule.patterns):
                return rule
        return None

    def _fuzzy(self, text: str) -> Optional[Rule]:
        if len(text) < 4:
            return None
        close = difflib.get_close_matches(text, list(_FUZZY), n=1, cutoff=0.75)
        return _FUZZY[close[0]] if close else None

    def reply_for(self, rule: Rule, text: str) -> str:
        if rule.handler:
            reply = rule.handler(self, text)
        else:
            choices = [r for r in rule.replies if r != self.last_reply.get(rule.name)] or rule.replies
            reply = random.choice(choices)
            self.last_reply[rule.name] = reply
        return reply.replace("{name}", self.display_name)

    def _fallback(self) -> str:
        self.fallback_streak += 1
        if self.fallback_streak >= 2:
            return ("I keep missing what you mean 😅 Try: 'tell me a joke', 'what is AI', "
                    "'what time is it', '12 * 7' or just 'help'.")
        return random.choice(FALLBACKS)


# Backwards-compatible helper
_default_bot = Chatbot()


def get_response(user_input: str) -> str:
    return _default_bot.respond(user_input)


def main():
    bot = Chatbot()
    print(f"{BOT_NAME}: Hi! I'm {BOT_NAME}. Type 'help' to see what I can do, 'bye' to exit.")
    while True:
        try:
            user_input = input("You: ")
        except (EOFError, KeyboardInterrupt):
            print(f"\n{BOT_NAME}: Bye! 👋")
            break
        reply = bot.respond(user_input)
        if reply == EXIT:
            print(f"{BOT_NAME}: Bye! Take care 👋")
            break
        print(f"{BOT_NAME}: {reply}")


if __name__ == "__main__":
    main()
