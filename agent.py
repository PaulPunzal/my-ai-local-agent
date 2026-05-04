# agent.py — backend: AI model, tools, parser
# UI lives in ui.py  |  entry point is main.py

import os
import subprocess
import time
from langchain_ollama import OllamaLLM

import ui

# ─── Model ────────────────────────────────────────────────────────────────────

ui.log_sys("Connecting to Ollama llama3...")
llm = OllamaLLM(model="llama3")
ui.log_sys("Model ready.")

# ─── Tools ────────────────────────────────────────────────────────────────────

def create_folder(path: str) -> str:
    path = path.strip().strip('"').strip("'")
    os.makedirs(path, exist_ok=True)
    ui.log_folder(path)
    return f"Folder created: {path}"


def create_file(path: str, content: str = "") -> str:
    path    = path.strip().strip('"').strip("'")
    content = content.strip().strip('"').strip("'")

    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
        ui.log_parent(parent)

    with open(path, "w") as f:
        f.write(content)

    ui.log_file_created(path)
    if content:
        ui.log_echo(content, path)

    return f"File created: {path}"


def read_file(path: str) -> str:
    """Read and return the contents of an existing file."""
    path = path.strip().strip('"').strip("'")
    if not os.path.exists(path):
        ui.log_warn(f"read_file: file not found → {path}")
        return f"[ERROR] File not found: {path}"
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    ui.log_file_read(path, content)
    return content


def append_to_file(path: str, content: str) -> str:
    """Append content to an existing file (or create it if missing)."""
    path    = path.strip().strip('"').strip("'")
    content = content.strip().strip('"').strip("'")

    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open(path, "a", encoding="utf-8") as f:
        f.write("\n" + content)

    ui.log_file_appended(path, content)
    return f"Appended to: {path}"


def fix_grammar(path: str) -> str:
    """Read a file, fix grammar via a dedicated LLM call, overwrite, and show a diff."""
    path = path.strip().strip('"').strip("'")
    if not os.path.exists(path):
        ui.log_warn(f"fix_grammar: file not found → {path}")
        return f"[ERROR] File not found: {path}"

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        original = f.read()

    ui.log_grammar_start(path, original)

    grammar_prompt = (
        "You are a grammar and spelling corrector.\n"
        "Fix ALL grammar, spelling, punctuation, and capitalization errors in the text below.\n"
        "Rules:\n"
        "- Preserve the original meaning and tone exactly\n"
        "- Do NOT add new sentences or extra information\n"
        "- Do NOT remove any sentences\n"
        "- Return ONLY the corrected text — no explanations, no labels, no quotes\n\n"
        f"Text to fix:\n{original}"
    )

    corrected = llm.invoke(grammar_prompt).strip()

    # safety: if AI returned nothing or something way too different, bail
    if not corrected or len(corrected) < len(original) * 0.4:
        ui.log_warn("fix_grammar: AI response looked wrong — file not changed.")
        return "[SKIPPED] Grammar fix response looked unsafe."

    with open(path, "w", encoding="utf-8") as f:
        f.write(corrected)

    ui.log_grammar_done(path, original, corrected)
    return corrected


def run_command(command: str) -> str:
    command = command.strip().strip('"').strip("'")
    ui.log_cmd(command)
    try:
        result = subprocess.check_output(command, shell=True, text=True, stderr=subprocess.STDOUT)
        for line in result.strip().splitlines():
            ui.log_cmd_out(line)
        return result
    except subprocess.CalledProcessError as e:
        ui.log_cmd_err(str(e.output))
        return str(e)

# ─── Snapshot with file previews ──────────────────────────────────────────────

def _snapshot() -> str:
    """
    Return a compact view of the current working directory.
    For small text files (≤ 2 KB), include their full contents so the AI
    can read → understand → append without a separate round-trip.
    """
    lines = []
    skip  = {"venv", "__pycache__", ".git", ".mypy_cache", "node_modules",
              "agent.py", "main.py", "ui.py", "prompts.py"}
    TEXT_EXTS = {".txt", ".md", ".py", ".json", ".csv", ".env", ".yaml", ".yml", ".toml", ".ini", ".cfg"}
    MAX_PREVIEW = 2048  # bytes

    for root, dirs, files in os.walk("."):
        dirs[:] = sorted(d for d in dirs if d not in skip)
        rel = os.path.relpath(root, ".")
        if rel == ".":
            continue
        lines.append(rel + "/")
        for fname in sorted(files):
            fpath = os.path.join(root, fname)
            rel_fpath = os.path.join(rel, fname)
            size = os.path.getsize(fpath)
            ext  = os.path.splitext(fname)[1].lower()

            if ext in TEXT_EXTS and size <= MAX_PREVIEW:
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        contents = f.read().strip()
                    lines.append(f"  {rel_fpath}  ({size}B)")
                    lines.append(f"  <<<")
                    for line in contents.splitlines():
                        lines.append(f"    {line}")
                    lines.append(f"  >>>")
                except Exception:
                    lines.append(f"  {rel_fpath}  ({size}B) [unreadable]")
            else:
                lines.append(f"  {rel_fpath}  ({size}B)")

    return "\n".join(lines) if lines else "(empty — no folders or files yet)"

# ─── Action runner ────────────────────────────────────────────────────────────

def run_actions(actions: list, explanation: str = "") -> None:
    ui.log_plan(len(actions))

    for i, a in enumerate(actions, 1):
        atype = a.get("action", "")
        args  = a.get("args", "")
        ui.log_step(i, len(actions), atype)

        if atype == "create_folder":
            create_folder(args)

        elif atype == "create_file":
            if "," in args:
                path, content = args.split(",", 1)
            else:
                path, content = args, ""
            path = path.strip()
            if not path:
                ui.log_warn("create_file skipped — no path was parsed.")
                continue
            create_file(path, content.strip())

        elif atype == "read_file":
            read_file(args)

        elif atype == "fix_grammar":
            fix_grammar(args)

        elif atype == "append_to_file":
            if "," in args:
                path, content = args.split(",", 1)
            else:
                ui.log_warn("append_to_file skipped — no content provided.")
                continue
            append_to_file(path.strip(), content.strip())

        elif atype == "run_command":
            run_command(args)

        else:
            ui.log_warn(f"Unknown action: {atype!r}")

        time.sleep(0.05)

    ui.log_done(len(actions))
    ui.print_file_tree()
    ui.print_summary(actions, explanation)

# ─── System prompt ────────────────────────────────────────────────────────────

SYSTEM = """You are a file-system assistant. Extract the user's intent and return a JSON array.

Each item in the array must have:
  "action"  : one of create_folder | create_file | read_file | append_to_file | fix_grammar | run_command
  "path"    : full relative path
  "content" : file content string (for create_file and append_to_file; empty string otherwise)

Optionally add ONE extra item at the END of the array with:
  "action": "explanation"
  "path": ""
  "content": "A short 1-2 sentence plain-English summary of what you did and why."

Action guide:
  create_folder    → make a new directory
  create_file      → make a NEW file or OVERWRITE an existing one (use only when asked to replace)
  read_file        → read and understand an existing file's contents (path only, no content needed)
  append_to_file   → ADD new content to the END of an existing file WITHOUT overwriting it
  fix_grammar      → read a file, fix all grammar/spelling/punctuation, and save it back (path only)
  run_command      → run a shell command

IMPORTANT RULES:
- If the user says "fix grammar", "correct", "proofread", "check spelling", "clean up" a file → use fix_grammar
- If the user says "add to", "append", "insert into", or "don't overwrite" → use append_to_file
- If the user says "read", "explain", "what's in", "summarize" a file → use read_file
- The snapshot already contains file contents between <<< and >>> — use this to understand what's already there
- NEVER use create_file when the intent is to add to or fix an existing file
- NEVER use run_command to write file content — use create_file or append_to_file instead
- Output raw JSON only — no markdown fences, no extra commentary outside the array

Example snapshot:
  Introduction/
  Introduction/About/
    Introduction/About/bio.txt  (27B)
    <<<
      My name is PaulJohn Punzal
    >>>

Example — user says "fix the grammar in bio.txt":
[
  {"action": "fix_grammar", "path": "Introduction/About/bio.txt", "content": ""},
  {"action": "explanation", "path": "", "content": "Fixed all grammar and spelling errors in bio.txt and saved the corrected version."}
]

Example — user says "read bio.txt and add a line about my hobby":
[
  {"action": "read_file",      "path": "Introduction/About/bio.txt", "content": ""},
  {"action": "append_to_file", "path": "Introduction/About/bio.txt", "content": "I love building AI agents."},
  {"action": "explanation",    "path": "", "content": "Read bio.txt which already had your name, then appended your hobby without overwriting."}
]

Example — user says "overwrite bio.txt with new content":
[
  {"action": "create_file", "path": "Introduction/About/bio.txt", "content": "New content here."},
  {"action": "explanation", "path": "", "content": "Overwrote bio.txt with the new content you specified."}
]
"""

# ─── Public API ───────────────────────────────────────────────────────────────

def process(user_input: str) -> None:
    """Full pipeline: send to AI → parse → execute. Called by main.py."""
    import json, re

    snapshot = _snapshot()
    prompt   = (
        f"{SYSTEM}\n\n"
        f"Current filesystem snapshot (file contents included between <<< and >>>):\n{snapshot}\n\n"
        f"User request: {user_input}"
    )
    response = llm.invoke(prompt)
    ui.log_ai_raw(response)

    # ── extract JSON from response (handles markdown fences) ──────────────────
    raw = response.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]+?)```", raw)
    if fence:
        raw = fence.group(1).strip()
    bracket = re.search(r"(\[\s*\{[\s\S]+?\])", raw)
    if bracket:
        raw = bracket.group(1)

    try:
        items = json.loads(raw)
    except Exception:
        ui.log_warn("Could not parse AI response as JSON. Try rephrasing.")
        return

    # ── convert JSON items → internal action dicts ────────────────────────────
    actions     = []
    explanation = ""

    for item in items:
        action  = str(item.get("action", "")).strip()
        path    = str(item.get("path",   "")).strip().strip('"').strip("'")
        content = str(item.get("content","")).strip().strip('"').strip("'")
        if not explanation and item.get("explanation"):
            explanation = str(item["explanation"]).strip()

        if action == "create_folder":
            actions.append({"action": "create_folder", "args": path})
        elif action == "create_file":
            args = f"{path}, {content}" if content else path
            actions.append({"action": "create_file", "args": args})
        elif action == "read_file":
            actions.append({"action": "read_file", "args": path})
        elif action == "fix_grammar":
            actions.append({"action": "fix_grammar", "args": path})
        elif action == "append_to_file":
            actions.append({"action": "append_to_file", "args": f"{path}, {content}"})
        elif action == "run_command":
            actions.append({"action": "run_command", "args": path or content})
        elif action == "explanation":
            explanation = path or content

    if not actions:
        ui.log_warn("No valid actions found. Try rephrasing your command.")
        return

    run_actions(actions, explanation)