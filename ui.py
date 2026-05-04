# =============================================================================
# ui.py -- all terminal display logic for your AI File Agent
# =============================================================================
# This file is intentionally separated from agent.py so that the "what things
# look like" (UI) stays completely separate from the "what things do" (logic).
# This pattern is called Separation of Concerns -- a core software design idea.
#
# Everything here is pure display: colors, layouts, log messages, menus.
# No AI calls, no file operations -- just printing things nicely.
# =============================================================================

import os
import shutil

# =============================================================================
# ANSI COLOR CODES
# =============================================================================
# ANSI escape codes are special character sequences that terminals interpret as
# formatting instructions. The format is: \033[<code>m
#   \033 = ESC character (octal 33)
#   [    = opening bracket
#   code = number for the color/style
#   m    = end of sequence
#
# When Python prints these, the terminal swaps them for actual colors.
# They're invisible characters -- they take up no space in the text itself.
# Tip: always end colored text with R (reset) or the color bleeds to next line.
# =============================================================================

R  = "\033[0m"    # reset -- go back to default terminal color
G  = "\033[92m"   # bright green  -- used for: success messages, folders created
B  = "\033[94m"   # bright blue   -- used for: step counters, info labels
Y  = "\033[93m"   # bright yellow -- used for: warnings, echoed content, dirs
C  = "\033[96m"   # bright cyan   -- used for: file paths and filenames
M  = "\033[95m"   # bright magenta -- used for: AI messages, system events
D  = "\033[90m"   # dark gray (dim) -- used for: separators, muted details
W  = "\033[97m"   # bright white  -- used for: important text, AI explanations
BG = "\033[1m"    # bold          -- combined with colors for emphasis


def _width() -> int:
    # shutil.get_terminal_size() asks the OS how wide the terminal currently is.
    # We cap at 72 so things don't stretch too wide on large monitors.
    # The (72, 20) tuple is a fallback if the terminal size can't be detected.
    return min(shutil.get_terminal_size((72, 20)).columns, 72)


def sep() -> None:
    # Prints a full-width horizontal line using the box-drawing character.
    # Used between major sections to visually break up the output.
    print(f"\n{D}{'─' * _width()}{R}\n")


def banner() -> None:
    # The welcome banner shown once when the agent starts.
    # Uses '=' characters to draw a box, then centers the title and subtitle.
    # The math: pad = (total_width - text_length) // 2 gives left padding for centering.
    w = _width()
    print(f"\n{M}{BG}{'=' * w}{R}")
    title = "PaulJohn's AI File Agent"
    pad   = (w - len(title)) // 2
    print(f"{M}{BG}{' ' * pad}{title}{R}")
    sub  = "powered by Ollama llama3  |  type a command or pick a preset"
    pad2 = (w - len(sub)) // 2
    print(f"{D}{' ' * pad2}{sub}{R}")
    print(f"{M}{BG}{'=' * w}{R}\n")


def show_presets(presets: list) -> None:
    # Iterates over the PRESETS list from prompts.py and prints each one
    # with a number, icon, and label. enumerate(presets, 1) starts counting at 1.
    print(f"{B}{BG}  Quick Presets{R}")
    print(f"{D}  {'─' * 40}{R}")
    for idx, p in enumerate(presets, 1):
        icon  = p.get("icon", ">")
        label = p.get("label", "")
        print(f"  {Y}{BG}[{idx}]{R}  {icon}  {W}{label}{R}")
    print(f"\n  {D}Enter a number to load a preset, or type your own command.{R}")
    print(f"  {D}Type {W}exit{D} to quit.{R}\n")


def prompt_input(presets: list) -> str:
    # This function handles the interactive shell prompt loop.
    # It shows a fake "shell" prompt (paul@HelloWorld:~/ai-agent(AI)$) for style,
    # then reads whatever the user types.
    #
    # If they type a number (e.g. "2"), we look up that preset and return its
    # full prompt text instead -- so the user never has to retype long commands.
    #
    # KeyboardInterrupt = user pressed Ctrl+C
    # EOFError          = user pressed Ctrl+D (end of input)
    # Both are treated as "exit" so the program closes cleanly.

    example = 'e.g. Read bio.txt then append "I love coding" to it'
    print(f"{D}  {example}{R}")

    try:
        raw = input(f"\n{G}paul@HelloWorld{R}:{B}~/ai-agent{R}{M}(AI){R}$ ").strip()
    except (KeyboardInterrupt, EOFError):
        return "exit"

    # If input is purely numeric, treat it as a preset selection
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(presets):
            chosen = presets[idx]["prompt"]
            print(f"\n  {D}> loaded: {W}{presets[idx]['label']}{R}")
            print(f"  {D}  {chosen}{R}\n")
            return chosen
        else:
            print(f"  {Y}[!]{R}  No preset #{raw}. Try 1-{len(presets)}.")
            return ""   # returning empty string causes main.py to loop again

    return raw


# =============================================================================
# LOGGING HELPERS
# =============================================================================
# Each function below is responsible for ONE specific type of log message.
# Keeping them as separate functions means:
#   - agent.py just calls ui.log_folder(path) -- it doesn't care about colors
#   - if you want to change how something looks, you only change it here
#   - easy to add new log types without touching agent.py
# =============================================================================

def log_ai_raw(response: str) -> None:
    # Shows the raw text llama3 sent back, dimmed so it's clearly "background info"
    # and not confused with actual actions being taken. The dots border is a visual
    # container to group the AI's response together.
    print(f"\n{M}[AI]{R}  Response received.\n")
    print(f"{D}{'.' * 32}{R}")
    for line in response.strip().splitlines():
        print(f"  {D}{line}{R}")
    print(f"{D}{'.' * 32}{R}\n")


def log_plan(count: int) -> None:
    # Shown right before we start executing actions.
    # Gives the user a heads-up of how many steps are about to run.
    print(f"{M}[PLAN]{R}  {count} action(s) queued\n")


def log_step(idx: int, total: int, action: str) -> None:
    # Shows "  [1/3] create_file" style progress for each action.
    # idx/total gives the user a sense of how far along we are.
    print(f"  {B}[{idx}/{total}]{R} {M}{action}{R}")


def log_folder(path: str) -> None:
    # "mkdir -p" is the Unix command equivalent -- shown for familiarity
    print(f"  {G}+{R}  mkdir  {C}{path}{R}")


def log_file_created(path: str) -> None:
    print(f"  {G}+{R}  created  {C}{path}{R}")


def log_file_read(path: str, content: str) -> None:
    # Shows a preview of the file contents (first 6 lines max) right in the terminal
    # so you can see what the AI is working with before it explains it.
    preview_lines = content.strip().splitlines()[:6]
    print(f"  {B}>{R}  reading  {C}{path}{R}")
    for line in preview_lines:
        print(f"  {D}    {line}{R}")
    total = len(content.strip().splitlines())
    if total > 6:
        print(f"  {D}    ... ({total} lines total){R}")


def log_file_explanation(path: str, explanation: str) -> None:
    # Displays the AI's natural-language explanation of the file contents.
    # This output comes from the SECOND llm.invoke() call inside read_file().
    # The box styling separates it visually from the raw file preview above.
    print(f"\n  {M}{BG}AI says:{R}")
    print(f"  {D}{'─' * 50}{R}")
    for line in explanation.strip().splitlines():
        print(f"  {W}  {line}{R}")
    print(f"  {D}{'─' * 50}{R}\n")


def log_grammar_start(path: str, original: str) -> None:
    # Shown at the start of a grammar fix, before the LLM call.
    # Shows a preview of the original text so the user knows what's being sent.
    print(f"  {M}~{R}  grammar  {C}{path}{R}  {D}(sending to AI...){R}")
    preview = original[:80] + ("..." if len(original) > 80 else "")
    print(f"  {D}  before: {preview}{R}")


def log_grammar_done(path: str, original: str, corrected: str) -> None:
    # Uses Python's built-in difflib module to compare the original and corrected
    # text word by word and highlight exactly what changed.
    #
    # SequenceMatcher works by finding the longest common subsequences between
    # two lists. get_opcodes() returns a list of change instructions:
    #   "equal"   -- this chunk is the same in both (we skip these)
    #   "replace" -- these words changed (show old in yellow, new in green)
    #   "insert"  -- new words were added (show in green)
    #   "delete"  -- old words were removed (show in yellow)
    import difflib

    orig_words = original.split()
    corr_words = corrected.split()
    matcher    = difflib.SequenceMatcher(None, orig_words, corr_words)

    print(f"  {G}~{R}  grammar done  {C}{path}{R}\n")
    print(f"  {D}{'─' * 50}{R}")

    has_changes = False
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "replace":
            has_changes = True
            before = " ".join(orig_words[i1:i2])
            after  = " ".join(corr_words[j1:j2])
            print(f"  {D}--{R}  {Y}{before}{R}")   # removed/changed (yellow)
            print(f"  {D}++{R}  {G}{after}{R}")    # replacement (green)
        elif tag in ("insert", "delete"):
            has_changes = True
            if tag == "delete":
                print(f"  {D}--{R}  {Y}{' '.join(orig_words[i1:i2])}{R}")
            else:
                print(f"  {D}++{R}  {G}{' '.join(corr_words[j1:j2])}{R}")

    if not has_changes:
        print(f"  {D}  (no changes -- text was already correct){R}")

    print(f"  {D}{'─' * 50}{R}\n")
    preview = corrected[:80] + ("..." if len(corrected) > 80 else "")
    print(f"  {G}  after: {preview}{R}\n")


def log_file_appended(path: str, content: str) -> None:
    preview = content[:60] + ("..." if len(content) > 60 else "")
    print(f"  {G}+{R}  appended  {C}{path}{R}")
    print(f"  {Y}    added: \"{preview}\"{R}")


def log_echo(content: str, path: str) -> None:
    # Shown when a file is created WITH content -- previews what was written
    preview = content[:60] + ("..." if len(content) > 60 else "")
    print(f"  {Y}  content: \"{preview}\"{R}  ->  {C}{path}{R}")


def log_parent(path: str) -> None:
    # Shown when we auto-create a parent folder to hold the new file
    print(f"  {D}  (created parent folder: {path}){R}")


def log_cmd(command: str) -> None:
    # The $ prefix mimics a Unix shell prompt -- makes command lines recognizable
    print(f"  {B}${R}  {command}")


def log_cmd_out(line: str) -> None:
    # Output lines from the shell command, indented and dimmed
    print(f"      {D}{line}{R}")


def log_cmd_err(msg: str) -> None:
    print(f"  {Y}[ERR]{R} {msg}")


def log_done(count: int) -> None:
    print(f"\n  {G}done -- {count} action(s) complete.{R}")


def log_warn(msg: str) -> None:
    print(f"\n{Y}[!]{R}  {msg}")


def log_sys(msg: str, ok: bool = True) -> None:
    # System-level messages (startup, model ready, etc.)
    # ok=True shows green [SYS], ok=False shows yellow to signal a problem
    tag = f"{G}[sys]{R}" if ok else f"{Y}[sys]{R}"
    print(f"{tag}  {msg}")


# =============================================================================
# SUMMARY REPORT
# =============================================================================
# Printed after every run. Groups actions by type so you get a clean overview
# of everything that happened -- especially useful when multiple actions ran.
#
# The ai_explanation string comes from the "explanation" action in the AI's JSON.
# It's the model's own summary of what it did and why -- in plain English.
# =============================================================================

def print_summary(actions: list, ai_explanation: str = "") -> None:
    w = 56
    print(f"\n{M}{'=' * w}{R}")
    print(f"{M}{BG}  Summary{R}")
    print(f"{M}{'=' * w}{R}\n")

    # Show the AI's self-written explanation if it provided one
    if ai_explanation:
        print(f"  {W}{BG}What happened:{R}")
        for line in ai_explanation.strip().splitlines():
            print(f"  {D}{line.strip()}{R}")
        print()

    # Group actions by type using list comprehensions -- clean and readable
    folders  = [a for a in actions if a.get("action") == "create_folder"]
    files    = [a for a in actions if a.get("action") == "create_file"]
    reads    = [a for a in actions if a.get("action") == "read_file"]
    appends  = [a for a in actions if a.get("action") == "append_to_file"]
    grammars = [a for a in actions if a.get("action") == "fix_grammar"]
    commands = [a for a in actions if a.get("action") == "run_command"]

    if reads:
        print(f"  {B}{BG}Read  ({len(reads)}){R}")
        for a in reads:
            print(f"  {D}  {C}{a.get('args','')}{R}")
        print()

    if folders:
        print(f"  {Y}{BG}Folders created  ({len(folders)}){R}")
        for a in folders:
            path = a.get("args", "").split(",")[0].strip()
            print(f"  {D}  {C}{path}{R}")
        print()

    if files:
        print(f"  {G}{BG}Files created  ({len(files)}){R}")
        for a in files:
            args    = a.get("args", "")
            path    = args.split(",")[0].strip() if "," in args else args.strip()
            content = args.split(",", 1)[1].strip() if "," in args else ""
            print(f"  {D}  {C}{path}{R}")
            if content:
                preview = content[:55] + ("..." if len(content) > 55 else "")
                print(f"  {D}    content: \"{preview}\"{R}")
        print()

    if appends:
        print(f"  {G}{BG}Files appended  ({len(appends)}){R}")
        for a in appends:
            args    = a.get("args", "")
            path    = args.split(",")[0].strip() if "," in args else args.strip()
            content = args.split(",", 1)[1].strip() if "," in args else ""
            print(f"  {D}  {C}{path}{R}")
            if content:
                preview = content[:55] + ("..." if len(content) > 55 else "")
                print(f"  {D}    added: \"{preview}\"{R}")
        print()

    if grammars:
        print(f"  {M}{BG}Grammar fixed  ({len(grammars)}){R}")
        for a in grammars:
            print(f"  {D}  {C}{a.get('args','')}{R}")
        print()

    if commands:
        print(f"  {B}{BG}Commands run  ({len(commands)}){R}")
        for a in commands:
            print(f"  {D}  $ {a.get('args','')}{R}")
        print()

    total = len(actions)
    print(f"  {G}{BG}  {total} action(s) completed.{R}")
    print(f"{M}{'=' * w}{R}\n")


# =============================================================================
# FILE TREE (kept available but not called automatically)
# =============================================================================
# Walks the directory and prints a visual tree. Not called after every action
# anymore (removed for cleaner output), but you can still trigger it manually
# by calling ui.print_file_tree() anywhere in agent.py if you want it back.
# =============================================================================

TREE_SKIP = {"venv", "__pycache__", ".git", ".mypy_cache", "node_modules"}

def print_file_tree(base: str = ".") -> None:
    print(f"\n{D}  file tree{R}")
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in sorted(dirs) if d not in TREE_SKIP]
        level   = root.replace(base, "").count(os.sep)
        indent  = "    " + "    " * level
        rel     = os.path.relpath(root, base)
        label   = "." if rel == "." else os.path.basename(root)
        print(f"  {indent}{Y}{label}/{R}")
        sub = "    " + "    " * (level + 1)
        for fname in sorted(files):
            fpath = os.path.join(root, fname)
            size  = os.path.getsize(fpath)
            print(f"  {sub}{C}{fname}{R}  {D}({size}B){R}")
    print()