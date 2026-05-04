# ui.py — terminal UI helpers: colors, menus, prompts, file tree

import os
import shutil

# ─── ANSI color codes ─────────────────────────────────────────────────────────
R  = "\033[0m"       # reset
G  = "\033[92m"      # green   — success, folders
B  = "\033[94m"      # blue    — info, step numbers
Y  = "\033[93m"      # yellow  — echo writes, warnings, dirs
C  = "\033[96m"      # cyan    — file names
M  = "\033[95m"      # magenta — AI / system messages
D  = "\033[90m"      # dim     — muted / separators
W  = "\033[97m"      # bright white
BG = "\033[1m"       # bold

def _width():
    return min(shutil.get_terminal_size((72, 20)).columns, 72)

def sep():
    print(f"\n{D}{'─' * _width()}{R}\n")

def banner():
    """Print the welcome banner on startup."""
    w = _width()
    print(f"\n{M}{BG}{'═' * w}{R}")
    title = "🤖  PaulJohn's AI File Agent"
    pad   = (w - len(title)) // 2
    print(f"{M}{BG}{' ' * pad}{title}{R}")
    sub   = "powered by Ollama llama3  ·  type a command or pick a preset"
    pad2  = (w - len(sub)) // 2
    print(f"{D}{' ' * pad2}{sub}{R}")
    print(f"{M}{BG}{'═' * w}{R}\n")

def show_presets(presets: list):
    """Print numbered preset menu."""
    print(f"{B}{BG}  Quick Presets{R}")
    print(f"{D}  {'─' * 40}{R}")
    for idx, p in enumerate(presets, 1):
        icon  = p.get("icon", "▸")
        label = p.get("label", "")
        print(f"  {Y}{BG}[{idx}]{R}  {icon}  {W}{label}{R}")
    print(f"\n  {D}Enter a number to load a preset, or just type your own command.{R}")
    print(f"  {D}Type {W}exit{D} to quit.{R}\n")

def prompt_input(presets: list) -> str:
    """
    Show the shell-style prompt. If the user enters a digit matching a
    preset number, expand it to the full prompt text. Otherwise return
    whatever they typed as-is.
    """
    example = 'e.g. Read bio.txt then append "I love coding" to it'
    print(f"{D}  {example}{R}")
    try:
        raw = input(f"\n{G}paul@HelloWorld{R}:{B}~/ai-agent{R}{M}(AI){R}$ ").strip()
    except (KeyboardInterrupt, EOFError):
        return "exit"

    # numeric shortcut → expand preset
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(presets):
            chosen = presets[idx]["prompt"]
            print(f"\n  {D}▸ loaded: {W}{presets[idx]['label']}{R}")
            print(f"  {D}  {chosen}{R}\n")
            return chosen
        else:
            print(f"  {Y}[WARN]{R}  No preset #{raw}. Try 1–{len(presets)}.")
            return ""   # empty → loop again

    return raw

# ─── Logging helpers ──────────────────────────────────────────────────────────

def log_ai_raw(response: str):
    """Print the raw AI response in a dimmed box."""
    print(f"\n{M}[AI]{R}  Response received.\n")
    print(f"{D}{'·' * 32}{R}")
    for line in response.strip().splitlines():
        print(f"  {D}{line}{R}")
    print(f"{D}{'·' * 32}{R}\n")

def log_plan(count: int):
    print(f"{M}[PLAN]{R}  {count} action(s) queued\n")

def log_step(idx: int, total: int, action: str):
    print(f"  {B}[{idx}/{total}]{R} {M}{action}{R}")

def log_folder(path: str):
    print(f"  {G}✔{R}  mkdir -p {C}{path}{R}")

def log_file_created(path: str):
    print(f"  {G}✔{R}  created   {C}{path}{R}")

def log_file_read(path: str, content: str):
    """Show a preview of the file the AI just read."""
    preview_lines = content.strip().splitlines()[:6]
    print(f"  {B}👁{R}  read      {C}{path}{R}")
    for line in preview_lines:
        print(f"  {D}    {line}{R}")
    if len(content.strip().splitlines()) > 6:
        print(f"  {D}    … ({len(content.strip().splitlines())} lines total){R}")

def log_grammar_start(path: str, original: str):
    print(f"  {M}✦{R}  grammar   {C}{path}{R}  {D}(sending to AI...){R}")
    print(f"  {D}  original → {original[:80]}{'…' if len(original) > 80 else ''}{R}")

def log_grammar_done(path: str, original: str, corrected: str):
    """Show a word-level diff between original and corrected text."""
    import difflib
    orig_words = original.split()
    corr_words = corrected.split()
    matcher    = difflib.SequenceMatcher(None, orig_words, corr_words)

    print(f"  {G}✔{R}  grammar fixed  {C}{path}{R}\n")
    print(f"  {D}{'─' * 50}{R}")

    has_changes = False
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "replace":
            has_changes = True
            before = " ".join(orig_words[i1:i2])
            after  = " ".join(corr_words[j1:j2])
            print(f"  {R}  {D}──{R}  {Y}{before}{R}")
            print(f"  {R}  {D}++{R}  {G}{after}{R}")
        elif tag in ("insert", "delete"):
            has_changes = True
            if tag == "delete":
                print(f"  {R}  {D}──{R}  {Y}{' '.join(orig_words[i1:i2])}{R}")
            else:
                print(f"  {R}  {D}++{R}  {G}{' '.join(corr_words[j1:j2])}{R}")

    if not has_changes:
        print(f"  {D}  (no changes — text was already correct!){R}")

    print(f"  {D}{'─' * 50}{R}\n")
    print(f"  {G}  corrected → {corrected[:80]}{'…' if len(corrected) > 80 else ''}{R}\n")

def log_file_appended(path: str, content: str):
    """Show what was appended and to which file."""
    preview = content[:60] + ("…" if len(content) > 60 else "")
    print(f"  {G}✔{R}  appended  {C}{path}{R}")
    print(f"  {Y}  +{R}  {Y}\"{preview}\"{R}")

def log_echo(content: str, path: str):
    preview = content[:60] + ("…" if len(content) > 60 else "")
    print(f"  {Y}✎{R}  echo      {Y}\"{preview}\"{R}  →  {C}{path}{R}")

def log_parent(path: str):
    print(f"  {D}↳  ensured parent: {path}{R}")

def log_cmd(command: str):
    print(f"  {B}${R}  {command}")

def log_cmd_out(line: str):
    print(f"      {D}{line}{R}")

def log_cmd_err(msg: str):
    print(f"  {R}[ERR]{R} {msg}")

def log_done(count: int):
    print(f"\n  {G}✔  Done — {count} action(s) complete.{R}")


def print_summary(actions: list, ai_explanation: str = ""):
    """Print a human-friendly summary report after every run."""
    w = 56

    print(f"\n{M}{'━' * w}{R}")
    print(f"{M}{BG}  📋  Summary Report{R}")
    print(f"{M}{'━' * w}{R}\n")

    # ── AI explanation block ──────────────────────────────────────────────────
    if ai_explanation:
        print(f"  {W}{BG}What the AI did:{R}")
        for line in ai_explanation.strip().splitlines():
            print(f"  {D}{line.strip()}{R}")
        print()

    # ── Action breakdown ──────────────────────────────────────────────────────
    folders   = [a for a in actions if a.get("action") == "create_folder"]
    files     = [a for a in actions if a.get("action") == "create_file"]
    reads     = [a for a in actions if a.get("action") == "read_file"]
    appends   = [a for a in actions if a.get("action") == "append_to_file"]
    grammars  = [a for a in actions if a.get("action") == "fix_grammar"]
    commands  = [a for a in actions if a.get("action") == "run_command"]

    if reads:
        print(f"  {B}{BG}Files read  ({len(reads)}){R}")
        for a in reads:
            print(f"  {D}  👁  {C}{a.get('args','')}{R}")
        print()

    if folders:
        print(f"  {Y}{BG}Folders created  ({len(folders)}){R}")
        for a in folders:
            path = a.get("args", "").split(",")[0].strip()
            print(f"  {D}  📁  {C}{path}{R}")
        print()

    if files:
        print(f"  {G}{BG}Files created / overwritten  ({len(files)}){R}")
        for a in files:
            args    = a.get("args", "")
            path    = args.split(",")[0].strip() if "," in args else args.strip()
            content = args.split(",", 1)[1].strip() if "," in args else ""
            print(f"  {D}  📄  {C}{path}{R}")
            if content:
                preview = content[:55] + ("…" if len(content) > 55 else "")
                print(f"  {D}      content → {Y}\"{preview}\"{R}")
        print()

    if appends:
        print(f"  {G}{BG}Files appended  ({len(appends)}){R}")
        for a in appends:
            args    = a.get("args", "")
            path    = args.split(",")[0].strip() if "," in args else args.strip()
            content = args.split(",", 1)[1].strip() if "," in args else ""
            print(f"  {D}  ✏️  {C}{path}{R}")
            if content:
                preview = content[:55] + ("…" if len(content) > 55 else "")
                print(f"  {D}      added → {Y}\"{preview}\"{R}")
        print()

    if grammars:
        print(f"  {M}{BG}Grammar fixed  ({len(grammars)}){R}")
        for a in grammars:
            print(f"  {D}  ✦   {C}{a.get('args','')}{R}")
        print()

    if commands:
        print(f"  {B}{BG}Commands run  ({len(commands)}){R}")
        for a in commands:
            print(f"  {D}  $   {a.get('args','')}{R}")
        print()

    total = len(actions)
    print(f"  {G}{BG}✔  {total} action(s) completed successfully.{R}")
    print(f"{M}{'━' * w}{R}\n")

def log_warn(msg: str):
    print(f"\n{Y}[WARN]{R}  {msg}")

def log_sys(msg: str, ok: bool = True):
    tag = f"{G}[SYS]{R}" if ok else f"{Y}[SYS]{R}"
    print(f"{tag}  {msg}")

# ─── File tree printer ────────────────────────────────────────────────────────

TREE_SKIP = {"venv", "__pycache__", ".git", ".mypy_cache", "node_modules"}

def print_file_tree(base="."):
    print(f"\n{D}  file tree{R}")
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in sorted(dirs) if d not in TREE_SKIP]
        level   = root.replace(base, "").count(os.sep)
        indent  = "    " + "    " * level
        rel     = os.path.relpath(root, base)
        label   = "." if rel == "." else os.path.basename(root)
        print(f"  {indent}{Y}{label}/{R}")
        sub     = "    " + "    " * (level + 1)
        for fname in sorted(files):
            fpath = os.path.join(root, fname)
            size  = os.path.getsize(fpath)
            print(f"  {sub}{C}{fname}{R}  {D}({size}B){R}")
    print()