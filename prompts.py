# prompts.py — pre-made prompt library for the AI agent
# Add, edit, or remove prompts here anytime. Each entry is a dict with:
#   label   → short name shown in the menu
#   icon    → single emoji for the button
#   prompt  → the actual text sent to the AI

PRESETS = [
    {
        "label": "Folder + file + echo",
        "icon":  "📁",
        "prompt": (
            'Create a folder "Introduction" with a subfolder "About", '
            'inside About create bio.txt and echo "My name is PaulJohn Punzal"'
        ),
    },
    {
        "label": "Nested project scaffold",
        "icon":  "🏗️",
        "prompt": (
            'Create a project scaffold: folder "MyApp" with subfolders "src" and "tests", '
            'add __init__.py to src with content "# MyApp source", '
            'and add README.md to MyApp with "# MyApp Project"'
        ),
    },
    {
        "label": "Multiple files with content",
        "icon":  "📝",
        "prompt": (
            'Create folder "Notes", inside create monday.txt with "Team standup at 9am", '
            'tuesday.txt with "Code review day", '
            'wednesday.txt with "Sprint planning"'
        ),
    },
    {
        "label": "Run ls command",
        "icon":  "🔍",
        "prompt": "Run the command: ls -la",
    },
    {
        "label": "Python hello world file",
        "icon":  "🐍",
        "prompt": (
            'Create folder "scripts", inside create hello.py '
            'with content: print("Hello, PaulJohn!")'
        ),
    },
]