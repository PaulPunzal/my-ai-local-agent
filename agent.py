# =============================================================================
# agent.py — the brain of your AI File Agent
# =============================================================================
# This file has three responsibilities:
#   1. TOOLS     — Python functions that actually do things (create files, etc.)
#   2. PIPELINE  — takes user text -> asks AI -> parses JSON -> runs tools
#   3. PROMPT    — the instruction manual we give the AI every single call
#
# How a single user command flows through this file:
#
#   main.py calls process(user_input)
#       |
#       v
#   _snapshot()          <- builds a "map" of existing files to give the AI context
#       |
#       v
#   llm.invoke(prompt)   <- sends everything to llama3, gets back JSON
#       |
#       v
#   json.loads(raw)      <- parses the JSON into a Python list of action dicts
#       |
#       v
#   run_actions(actions) <- loops through actions and calls the right tool
#       |
#       v
#   create_file / read_file / fix_grammar / etc.
# =============================================================================

import os
import subprocess
import time
from langchain_ollama import OllamaLLM   # pip package that talks to your local Ollama server

import ui   # our terminal display helpers (colors, logs, summary)

# =============================================================================
# MODEL SETUP
# =============================================================================
# OllamaLLM connects to the Ollama server running on your machine (localhost:11434).
# Think of `llm` as your direct line to llama3 -- calling llm.invoke("...") is
# like sending a message and waiting for a reply. It's synchronous (blocking),
# meaning Python pauses here until llama3 finishes responding.
# =============================================================================

ui.log_sys("Connecting to Ollama llama3...")
llm = OllamaLLM(model="llama3")
ui.log_sys("Model ready.")


# =============================================================================
# TOOLS -- the real-world actions the agent can perform
# =============================================================================
# These are plain Python functions. The AI doesn't call them directly --
# it just tells us *which one* to call (via JSON). We then call it ourselves.
# This pattern is called "tool use" or "function calling" in AI terminology.
# =============================================================================

def create_folder(path: str) -> str:
    # Strip stray quotes the AI sometimes wraps paths in (e.g. "Introduction/About")
    path = path.strip().strip('"').strip("'")

    # exist_ok=True means: don't crash if the folder already exists
    # makedirs also creates all missing parent folders in one shot
    os.makedirs(path, exist_ok=True)

    ui.log_folder(path)
    return f"Folder created: {path}"


def create_file(path: str, content: str = "") -> str:
    path    = path.strip().strip('"').strip("'")
    content = content.strip().strip('"').strip("'")

    # If the file is inside a subfolder that doesn't exist yet, create it first.
    # os.path.dirname("Introduction/About/bio.txt") returns "Introduction/About"
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
        ui.log_parent(parent)

    # "w" mode = write mode. Creates the file if it doesn't exist,
    # or OVERWRITES it completely if it does. Use append_to_file to add instead.
    with open(path, "w") as f:
        f.write(content)

    ui.log_file_created(path)
    if content:
        ui.log_echo(content, path)

    return f"File created: {path}"


def read_file(path: str) -> str:
    # This function does two things:
    #   1. Reads the file from disk into a Python string
    #   2. Makes a SECOND llm.invoke() call to explain what it read
    #
    # Why a second LLM call? Because the first call only returns JSON actions.
    # To get a natural language explanation we need a fresh, separate prompt
    # that's focused entirely on understanding the content -- not parsing commands.

    path = path.strip().strip('"').strip("'")
    if not os.path.exists(path):
        ui.log_warn(f"read_file: file not found -> {path}")
        return f"[ERROR] File not found: {path}"

    # errors="replace" means: if there are weird/broken characters, replace them
    # with a placeholder instead of crashing
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    ui.log_file_read(path, content)

    # Build a focused prompt just for explaining -- no JSON, no actions.
    # The more specific your prompt, the better the AI's response quality.
    explain_prompt = (
        f"A user asked you to read and explain the file '{path}'. "
        f"Here are its contents:\n\n{content}\n\n"
        "Give a friendly, clear explanation of what this file is about and what it contains. "
        "Be concise -- 2 to 4 sentences max. Talk directly to the user."
    )
    explanation = llm.invoke(explain_prompt).strip()
    ui.log_file_explanation(path, explanation)

    return content


def append_to_file(path: str, content: str) -> str:
    # Unlike create_file which uses "w" (overwrite), this uses "a" (append).
    # "a" mode moves the write cursor to the END of the file, so existing
    # content is never touched. If the file doesn't exist, "a" creates it.
    path    = path.strip().strip('"').strip("'")
    content = content.strip().strip('"').strip("'")

    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open(path, "a", encoding="utf-8") as f:
        f.write("\n" + content)   # \n ensures the new content starts on its own line

    ui.log_file_appended(path, content)
    return f"Appended to: {path}"


def fix_grammar(path: str) -> str:
    # This is the most "agentic" tool -- it does a full read -> AI call -> write cycle.
    # The key design decision: we use a DEDICATED grammar prompt, completely
    # separate from the main action-parsing prompt. This is important because
    # mixing concerns (parse actions + fix grammar) in one prompt makes the AI
    # confused and produces worse results. Focused prompts = better outputs.

    path = path.strip().strip('"').strip("'")
    if not os.path.exists(path):
        ui.log_warn(f"fix_grammar: file not found -> {path}")
        return f"[ERROR] File not found: {path}"

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        original = f.read()

    ui.log_grammar_start(path, original)

    # Prompt engineering tip: giving the AI a role ("You are a grammar corrector")
    # and explicit rules ("do NOT add sentences") dramatically improves consistency.
    # Without these constraints llama3 tends to rewrite the whole text or add commentary.
    grammar_prompt = (
        "You are a grammar and spelling corrector.\n"
        "Fix ALL grammar, spelling, punctuation, and capitalization errors in the text below.\n"
        "Rules:\n"
        "- Preserve the original meaning and tone exactly\n"
        "- Do NOT add new sentences or extra information\n"
        "- Do NOT remove any sentences\n"
        "- Return ONLY the corrected text -- no explanations, no labels, no quotes\n\n"
        f"Text to fix:\n{original}"
    )

    corrected = llm.invoke(grammar_prompt).strip()

    # Safety check: if the AI returned something suspiciously short (less than
    # 40% of the original length), something went wrong -- bail out and don't
    # overwrite the file. Better to do nothing than corrupt your data.
    if not corrected or len(corrected) < len(original) * 0.4:
        ui.log_warn("fix_grammar: AI response looked wrong -- file not changed.")
        return "[SKIPPED] Grammar fix response looked unsafe."

    with open(path, "w", encoding="utf-8") as f:
        f.write(corrected)

    # log_grammar_done uses Python's difflib to show exactly what changed
    ui.log_grammar_done(path, original, corrected)
    return corrected


def run_command(command: str) -> str:
    # subprocess.check_output() runs a shell command and captures its output.
    # shell=True means the command is passed to /bin/sh -- so pipes, wildcards,
    # and other shell features all work (e.g. "ls -la | grep .txt").
    # stderr=STDOUT merges error output into the normal output so we see both.
    # WARNING: shell=True with untrusted input is a security risk in production.
    # For a personal local agent it's fine, but keep this in mind if you ever
    # expose this agent to other users or the internet.
    command = command.strip().strip('"').strip("'")
    ui.log_cmd(command)
    try:
        result = subprocess.check_output(command, shell=True, text=True, stderr=subprocess.STDOUT)
        for line in result.strip().splitlines():
            ui.log_cmd_out(line)
        return result
    except subprocess.CalledProcessError as e:
        # CalledProcessError is raised when the command exits with a non-zero status
        # (i.e. something went wrong). e.output contains whatever the command printed.
        ui.log_cmd_err(str(e.output))
        return str(e)


# =============================================================================
# SNAPSHOT -- giving the AI "eyes" on the filesystem
# =============================================================================
# Before every AI call, we walk the current directory and build a text summary
# of what files and folders exist -- including their contents for small text files.
#
# Why? Because the AI has NO memory between calls. It doesn't know what files
# you created last time. The snapshot is how we give it that context each time.
#
# This snapshot gets inserted into the prompt, so the AI can say things like:
#   "I see bio.txt already has your name, so I'll append to it, not overwrite."
# =============================================================================

def _snapshot() -> str:
    lines = []

    # These folders/files are part of the agent itself -- we skip them so the AI
    # doesn't get confused by its own source code sitting in the directory.
    skip = {"venv", "__pycache__", ".git", ".mypy_cache", "node_modules",
            "agent.py", "main.py", "ui.py", "prompts.py"}

    # Only include contents of files with these extensions (text-based formats).
    # Binary files like images or .pyc would just show garbage characters.
    TEXT_EXTS = {".txt", ".md", ".py", ".json", ".csv", ".env",
                 ".yaml", ".yml", ".toml", ".ini", ".cfg"}

    MAX_PREVIEW = 2048  # bytes -- skip content preview for files larger than 2KB

    for root, dirs, files in os.walk("."):
        # Sort and filter dirs in-place -- os.walk respects this to avoid entering skipped folders
        dirs[:] = sorted(d for d in dirs if d not in skip)

        rel = os.path.relpath(root, ".")
        if rel == ".":
            continue   # skip the root "." itself, only show subfolders

        lines.append(rel + "/")

        for fname in sorted(files):
            fpath     = os.path.join(root, fname)
            rel_fpath = os.path.join(rel, fname)
            size      = os.path.getsize(fpath)
            ext       = os.path.splitext(fname)[1].lower()

            if ext in TEXT_EXTS and size <= MAX_PREVIEW:
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        contents = f.read().strip()
                    # <<< and >>> are our delimiters -- the AI prompt tells llama3
                    # to look between these to find existing file contents
                    lines.append(f"  {rel_fpath}  ({size}B)")
                    lines.append(f"  <<<")
                    for line in contents.splitlines():
                        lines.append(f"    {line}")
                    lines.append(f"  >>>")
                except Exception:
                    lines.append(f"  {rel_fpath}  ({size}B) [unreadable]")
            else:
                # Large or binary file -- just show name and size, no content
                lines.append(f"  {rel_fpath}  ({size}B)")

    return "\n".join(lines) if lines else "(empty -- no folders or files yet)"


# =============================================================================
# ACTION RUNNER -- the executor that connects parsed JSON to real tool calls
# =============================================================================
# run_actions receives a list like:
#   [{"action": "create_file", "args": "Notes/todo.txt, Buy milk"}, ...]
# and calls the matching Python function for each one.
#
# The slight complexity with create_file and append_to_file is that their args
# pack both path and content into one comma-separated string -- we split them here.
# =============================================================================

def run_actions(actions: list, explanation: str = "") -> None:
    ui.log_plan(len(actions))

    for i, a in enumerate(actions, 1):
        atype = a.get("action", "")
        args  = a.get("args", "")
        ui.log_step(i, len(actions), atype)

        if atype == "create_folder":
            create_folder(args)

        elif atype == "create_file":
            # args format: "path/to/file.txt, content goes here"
            # We split on the FIRST comma only (maxsplit=1) so content can contain commas
            if "," in args:
                path, content = args.split(",", 1)
            else:
                path, content = args, ""
            path = path.strip()
            if not path:
                ui.log_warn("create_file skipped -- no path was parsed.")
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
                ui.log_warn("append_to_file skipped -- no content provided.")
                continue
            append_to_file(path.strip(), content.strip())

        elif atype == "run_command":
            run_command(args)

        else:
            ui.log_warn(f"Unknown action: {atype!r}")

        # Small delay between actions -- mostly cosmetic, but also prevents
        # hammering the filesystem with rapid-fire writes
        time.sleep(0.05)

    ui.log_done(len(actions))
    ui.print_summary(actions, explanation)


# =============================================================================
# SYSTEM PROMPT -- the rulebook we hand to the AI on every single call
# =============================================================================
# This is the most important part of prompt engineering. The system prompt:
#   - Defines the AI's role ("You are a file-system assistant")
#   - Lists every available action and when to use each one
#   - Gives strict output format rules (raw JSON only)
#   - Provides concrete examples so the AI can pattern-match
#
# Key insight: LLMs don't "understand" your program. They predict text.
# The clearer and more example-rich your system prompt, the more reliably
# the model produces the exact JSON format your parser expects.
#
# The snapshot is appended BELOW this prompt on each call, followed by
# the user's actual request -- so the model always sees: rules -> context -> task.
# =============================================================================

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
  create_folder    -> make a new directory
  create_file      -> make a NEW file or OVERWRITE an existing one (use only when asked to replace)
  read_file        -> read and understand an existing file's contents (path only, no content needed)
  append_to_file   -> ADD new content to the END of an existing file WITHOUT overwriting it
  fix_grammar      -> read a file, fix all grammar/spelling/punctuation, and save it back (path only)
  run_command      -> run a shell command

IMPORTANT RULES:
- If the user says "fix grammar", "correct", "proofread", "check spelling", "clean up" a file -> use fix_grammar
- If the user says "add to", "append", "insert into", or "don't overwrite" -> use append_to_file
- If the user says "read", "explain", "what's in", "summarize" a file -> use read_file
- The snapshot already contains file contents between <<< and >>> -- use this to understand what's already there
- NEVER use create_file when the intent is to add to or fix an existing file
- NEVER use run_command to write file content -- use create_file or append_to_file instead
- Output raw JSON only -- no markdown fences, no extra commentary outside the array

Example snapshot:
  Introduction/
  Introduction/About/
    Introduction/About/bio.txt  (27B)
    <<<
      My name is PaulJohn Punzal
    >>>

Example -- user says "fix the grammar in bio.txt":
[
  {"action": "fix_grammar", "path": "Introduction/About/bio.txt", "content": ""},
  {"action": "explanation", "path": "", "content": "Fixed all grammar and spelling errors in bio.txt and saved the corrected version."}
]

Example -- user says "read bio.txt and add a line about my hobby":
[
  {"action": "read_file",      "path": "Introduction/About/bio.txt", "content": ""},
  {"action": "append_to_file", "path": "Introduction/About/bio.txt", "content": "I love building AI agents."},
  {"action": "explanation",    "path": "", "content": "Read bio.txt which already had your name, then appended your hobby without overwriting."}
]

Example -- user says "overwrite bio.txt with new content":
[
  {"action": "create_file", "path": "Introduction/About/bio.txt", "content": "New content here."},
  {"action": "explanation", "path": "", "content": "Overwrote bio.txt with the new content you specified."}
]
"""


# =============================================================================
# process() -- the main entry point called by main.py
# =============================================================================
# This is the full pipeline in one function:
#   1. Build the snapshot (filesystem context)
#   2. Assemble the full prompt (system + snapshot + user input)
#   3. Send to llama3 and get raw text back
#   4. Extract JSON from the raw text (model sometimes wraps it in markdown)
#   5. Convert JSON items into internal action dicts
#   6. Hand off to run_actions()
# =============================================================================

def process(user_input: str) -> None:
    import json, re

    # Step 1: snapshot gives the AI awareness of what already exists
    snapshot = _snapshot()

    # Step 2: assemble full prompt -- order matters here.
    # System rules come first so they set the context, then the snapshot,
    # then the user request last so it's fresh in the model's attention window.
    prompt = (
        f"{SYSTEM}\n\n"
        f"Current filesystem snapshot (file contents included between <<< and >>>):\n{snapshot}\n\n"
        f"User request: {user_input}"
    )

    # Step 3: send to llama3 -- this is a blocking call, takes a few seconds
    response = llm.invoke(prompt)
    ui.log_ai_raw(response)

    # Step 4: extract JSON from the response.
    # llama3 often wraps JSON in ```json ... ``` markdown fences even when told not to.
    # We handle both cases: fenced and bare JSON.
    raw = response.strip()

    fence = re.search(r"```(?:json)?\s*([\s\S]+?)```", raw)
    if fence:
        raw = fence.group(1).strip()

    # Grab the first [...] block -- handles cases where the model adds
    # commentary before or after the JSON array
    bracket = re.search(r"(\[\s*\{[\s\S]+?\])", raw)
    if bracket:
        raw = bracket.group(1)

    try:
        items = json.loads(raw)
    except Exception:
        # If we still can't parse it, give the user a helpful message
        ui.log_warn("Could not parse AI response as JSON. Try rephrasing.")
        return

    # Step 5: convert the parsed JSON list into our internal action format.
    # The AI uses {"action", "path", "content"} keys.
    # Internally we use {"action", "args"} where args packs path+content together.
    actions     = []
    explanation = ""

    for item in items:
        action  = str(item.get("action", "")).strip()
        path    = str(item.get("path",   "")).strip().strip('"').strip("'")
        content = str(item.get("content","")).strip().strip('"').strip("'")

        # Pick up explanation text if the AI included it anywhere in the item
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
            explanation = path or content   # model sometimes puts the text in path field

    if not actions:
        ui.log_warn("No valid actions found. Try rephrasing your command.")
        return

    # Step 6: execute!
    run_actions(actions, explanation)