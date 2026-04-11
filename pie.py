#!/usr/bin/env python3
# ============================================================
# 🥧 pie.py — Goldilocks CLI Entry Point
# ============================================================
# Pipeline Intelligence Engine
# ============================================================

import sys
import time

# ------------------------------------------------------------
# ANSI colour codes
# ------------------------------------------------------------
YELLOW  = "\033[93m"
GOLD    = "\033[33m"
GREEN   = "\033[92m"
RED     = "\033[91m"
CYAN    = "\033[96m"
RESET   = "\033[0m"
BOLD    = "\033[1m"


# ------------------------------------------------------------
# ASCII LOGO
# ------------------------------------------------------------

LOGO = f"""{YELLOW}
 
                                                      
 ▄   ▄▄▄▄      ▄▄          ▄▄                          
 ▀██████▀       ██    █▄    ██                         
   ██   ▄       ██    ██ ▀▀ ██             ▄▄          
   ██  ██ ▄███▄ ██ ▄████ ██ ██ ▄███▄ ▄███▀ ██ ▄█▀ ▄██▀█
   ██  ██ ██ ██ ██ ██ ██ ██ ██ ██ ██ ██    ████   ▀███▄
   ▀█████▄▀███▀▄██▄█▀███▄██▄██▄▀███▀▄▀███▄▄██ ▀█▄█▄▄██▀
   ▄   ██                                              
   ▀████▀                                              
{RESET}"""

TAGLINE = f"{GOLD}  Pipeline Intelligence Platform  •  curl · parse · graph · monitor{RESET}"
DIVIDER = f"{YELLOW}  {'─' * 72}{RESET}"


# ------------------------------------------------------------
# MENU
# ------------------------------------------------------------

MENU = f"""
{DIVIDER}
{BOLD}  What would you like to do?{RESET}

  {CYAN}[1]{RESET}  Run full pipeline  {GOLD}← recommended{RESET}
  {CYAN}[2]{RESET}  Fetch pipelines from SnapLogic
  {CYAN}[3]{RESET}  Anonymise pipeline data
  {CYAN}[4]{RESET}  Seed Neo4j graph
  {CYAN}[5]{RESET}  Generate Mermaid diagrams
  {CYAN}[6]{RESET}  Ask Goldilocks a question  {GOLD}← AI mode 🤖{RESET}
  {CYAN}[q]{RESET}  Quit
{DIVIDER}
"""


# ------------------------------------------------------------
# STEP FUNCTIONS (stubs for now — we wire these up next)
# ------------------------------------------------------------

def step_fetch():
    print(f"\n{CYAN}🌐 Fetching pipelines from SnapLogic...{RESET}")
    time.sleep(0.5)
    print(f"{GREEN}✅ Pipelines fetched!{RESET}")

def step_anonymise():
    print(f"\n{CYAN}🔒 Anonymising sensitive data...{RESET}")
    time.sleep(0.5)
    print(f"{GREEN}✅ Data anonymised!{RESET}")

def step_seed():
    print(f"\n{CYAN}🌱 Seeding Neo4j graph...{RESET}")
    time.sleep(0.5)
    print(f"{GREEN}✅ Graph seeded!{RESET}")

def step_visualise():
    print(f"\n{CYAN}🎨 Generating Mermaid diagrams...{RESET}")
    time.sleep(0.5)
    print(f"{GREEN}✅ Diagrams generated!{RESET}")

def step_ask():
    print(f"\n{CYAN}🤖 Goldilocks AI mode{RESET}")
    question = input(f"{GOLD}  Ask Goldilocks > {RESET}")
    print(f"\n{GREEN}  🔍 Thinking...{RESET}")
    time.sleep(1)
    print(f"{GREEN}  Coming soon! 🚀{RESET}")

def run_full_pipeline():
    print(f"\n{GOLD}  Running full pipeline...{RESET}")
    step_fetch()
    step_anonymise()
    step_seed()
    step_visualise()
    print(f"\n{GREEN}{BOLD}  🐻 All done! Your pipeline graph is ready.{RESET}\n")


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main():
    # Print logo
    print(LOGO)
    print(TAGLINE)

    while True:
        print(MENU)
        choice = input(f"{GOLD}  Choose (default: 1) > {RESET}").strip().lower()

        if choice in ("", "1"):
            proceed = input(f"\n{YELLOW}  Are you happy to proceed? (y/n) > {RESET}").strip().lower()
            if proceed == "y":
                run_full_pipeline()
            else:
                print(f"\n{RED}  Cancelled.{RESET}\n")

        elif choice == "2":
            step_fetch()
        elif choice == "3":
            step_anonymise()
        elif choice == "4":
            step_seed()
        elif choice == "5":
            step_visualise()
        elif choice == "6":
            step_ask()
        elif choice == "q":
            print(f"\n{YELLOW}  🐻 Goodbye! Just right.{RESET}\n")
            sys.exit(0)
        else:
            print(f"\n{RED}  Invalid choice — please try again.{RESET}")


if __name__ == "__main__":
    main()