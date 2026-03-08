"""BLACKJACK 21 — Entry point (Terminal + GUI)."""

import os
import sys


def run_terminal() -> None:
    from blackjack.renderer import Ansi
    from blackjack.game import BlackjackGame
    from blackjack.menu import main_menu, select_difficulty, show_theory

    while True:
        main_menu()
        ch = input(f"  {Ansi.BOLD}Выбор: {Ansi.RST}").strip().lower()
        if ch in ("1", "о"):
            diff = select_difficulty()
            if diff is not None:
                BlackjackGame(edu_mode=False, difficulty=diff).run()
        elif ch in ("2", "у"):
            diff = select_difficulty()
            if diff is not None:
                BlackjackGame(edu_mode=True, difficulty=diff).run()
        elif ch in ("3", "т"):
            show_theory()
        elif ch in ("q", "quit", "й"):
            break


def run_gui() -> None:
    from blackjack.gui.app import run_gui as gui_main
    gui_main()


def main() -> None:
    if sys.platform == "win32":
        os.system("")

    # Accept command-line argument from bat file
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else None

    if mode == "terminal":
        run_terminal()
    elif mode == "gui":
        run_gui()
    else:
        # Interactive selection (if launched directly without args)
        from blackjack.renderer import Ansi
        print(f"""
{Ansi.YELLOW}{Ansi.BOLD}    +==========================================+
    |     BLACKJACK 21                        |
    +==========================================+{Ansi.RST}

  {Ansi.GREEN}{Ansi.BOLD}1{Ansi.RST}  Terminal (консоль)
  {Ansi.CYAN}{Ansi.BOLD}2{Ansi.RST}  GUI (Pygame)
  {Ansi.DIM}q  Выход{Ansi.RST}
        """)
        choice = input(f"  {Ansi.BOLD}Выбор: {Ansi.RST}").strip().lower()
        if choice in ("1", "т"):
            run_terminal()
        elif choice in ("2", "г"):
            run_gui()

    print("\n  До встречи!\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Выход...\n")
