import curses

from src.constants import EXIT, RUN_SCORPION, RUN_SC_CLI, RUN_SC_GUI


def selector(stdscr, options: list, prompt: str) -> int:

    selected = 0

    while True:
        stdscr.clear()

        stdscr.addstr(prompt)

        for index, option in enumerate(options):
            if index == selected:
                stdscr.addstr(f"> {option}\n")
            else:
                stdscr.addstr(f"  {option}\n")

        key = stdscr.getch()

        if key == curses.KEY_UP:
            selected -= 1

        elif key == curses.KEY_DOWN:
            selected += 1

        elif key == curses.KEY_ENTER or key in [10, 13]:
            return selected

        if selected < 0:
            selected = len(options) - 1

        elif selected >= len(options):
            selected = 0


def menu(stdscr, options: str) -> str:
    menus = {
        RUN_SCORPION: [
            RUN_SCORPION,
            RUN_SC_CLI,
            RUN_SC_GUI,
            EXIT,
        ],
    }

    prompts = {
        RUN_SCORPION: "Do you want to launch the Scorpion program to browse \
metadata in the downloaded images?\n\n",
    }

    selection = selector(
        stdscr=stdscr,
        options=menus[options],
        prompt=prompts[options]
        )

    return menus[options][selection]
