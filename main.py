#!/usr/bin/env python3
# main.py — entry point for PaulJohn's AI File Agent
# Run with:  python main.py

import ui
import agent
from prompts import PRESETS

def main():
    ui.banner()
    ui.show_presets(PRESETS)

    while True:
        ui.sep()
        user_input = ui.prompt_input(PRESETS)

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "q"):
            print(f"\n  Bye, PaulJohn! 👋\n")
            break

        print(f"\n  Sending to AI...\n")
        agent.process(user_input)

if __name__ == "__main__":
    main()