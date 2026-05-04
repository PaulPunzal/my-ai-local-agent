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

# ─── Action runner ────────────────────────────────────────────────────────────

def run_actions(actions: list) -> None:
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

        elif atype == "run_command":
            run_command(args)

        else:
            ui.log_warn(f"Unknown action: {atype!r}")

        time.sleep(0.05)

    ui.log_done(len(actions))
    ui.print_file_tree()

# ─── System prompt ────────────────────────────────────────────────────────────

SYSTEM = """You are a precise file-system automation assistant.

Given a user request, output ONLY a sequence of ACTION/ARGS pairs — nothing else.
No explanation. No commentary. No numbering. No blank lines between pairs.

Available actions:
  create_folder   ARGS: <relative/path>
  create_file     ARGS: <relative/path>, <file content>
  run_command     ARGS: <shell command>

Rules:
- Use forward slashes for nested paths: Introduction/About/bio.txt
- For create_file, ALWAYS put the content after the comma on the SAME ARGS line
- Do NOT wrap values in quotes
- Do NOT use run_command echo to write file content — use create_file with content
- Output ONLY the ACTION/ARGS blocks, nothing else

Example input:  Create folder Hello with subfolder World, inside World create hi.txt with content Greetings
Example output:
ACTION: create_folder
ARGS: Hello
ACTION: create_folder
ARGS: Hello/World
ACTION: create_file
ARGS: Hello/World/hi.txt, Greetings
"""

# ─── Parser ───────────────────────────────────────────────────────────────────

KNOWN_ACTIONS = {"create_folder", "create_file", "run_command"}

def parse_response(response: str) -> list:
    """
    Single unified pass — handles Format A (ACTION:/ARGS:) and Format B (raw
    inline) mixed together in any order, which is exactly what llama3 does.
    Post-pass absorbs orphan echo commands into empty create_file args.
    """
    actions = []
    lines   = [l.strip() for l in response.strip().splitlines() if l.strip()]

    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith("#") or line.startswith("//"):
            i += 1
            continue

        # Format A: ACTION: ... + optional ARGS: on next line
        if line.upper().startswith("ACTION:"):
            action = line.split(":", 1)[1].strip()
            args   = ""
            if i + 1 < len(lines) and lines[i + 1].upper().startswith("ARGS:"):
                args = lines[i + 1].split(":", 1)[1].strip()
                i += 1
            if action:
                actions.append({"action": action, "args": args})
            i += 1
            continue

        # skip orphan ARGS: lines
        if line.upper().startswith("ARGS:"):
            i += 1
            continue

        # Format B: raw "create_folder Introduction/About" on one line
        parts     = line.split(None, 1)
        candidate = parts[0].lower().rstrip(":") if parts else ""
        if candidate in KNOWN_ACTIONS:
            args = parts[1].strip() if len(parts) > 1 else ""
            # llama3 sometimes writes "create_folder ARGS: path" on one line
            if args.upper().startswith("ARGS:"):
                args = args.split(":", 1)[1].strip()
            args = args.strip('"').strip("'")
            # deduplicate: skip if same action+args already queued
            if not any(a["action"] == candidate and a["args"] == args for a in actions):
                actions.append({"action": candidate, "args": args})

        i += 1

    # post-pass: absorb orphan echo into preceding empty create_file
    merged = []
    j = 0
    while j < len(actions):
        a = actions[j]
        if (
            a["action"] == "create_file"
            and "," not in a["args"]
            and j + 1 < len(actions)
            and actions[j + 1]["action"] == "run_command"
            and actions[j + 1]["args"].lower().startswith("echo")
        ):
            echo_text = actions[j + 1]["args"][4:].strip().strip('"').strip("'")
            merged.append({"action": "create_file", "args": f"{a['args']}, {echo_text}"})
            j += 2
        else:
            merged.append(a)
            j += 1

    return merged

# ─── Public API ───────────────────────────────────────────────────────────────

def _snapshot() -> str:
    """Return a compact view of the current working directory for the AI."""
    lines = []
    skip  = {"venv", "__pycache__", ".git", ".mypy_cache", "node_modules",
              "agent.py", "main.py", "ui.py", "prompts.py"}
    for root, dirs, files in os.walk("."):
        dirs[:] = sorted(d for d in dirs if d not in skip)
        rel = os.path.relpath(root, ".")
        if rel == ".":
            continue
        lines.append(rel + "/")
        for f in sorted(files):
            lines.append(f"  {rel}/{f}")
    return "\n".join(lines) if lines else "(empty — no folders or files yet)"


def process(user_input: str) -> None:
    """Full pipeline: send to AI → parse → execute. Called by main.py."""
    snapshot = _snapshot()
    prompt   = (
        f"{SYSTEM}\n\n"
        f"Current working directory structure:\n{snapshot}\n\n"
        f"User request: {user_input}"
    )
    response = llm.invoke(prompt)

    ui.log_ai_raw(response)

    actions = parse_response(response)

    if not actions:
        ui.log_warn("No valid actions parsed. Try rephrasing your command.")
        return

    run_actions(actions)