from pathlib import Path

USER_AGENT = (
    "Arachnida42/1.0 "
    "(contact: odruke-s@student.42lausanne.ch) "
    "requests"
)

# Menu actions
RUN_SCORPION = "Run Scorpion"
RUN_SC_CLI = "Run Scorpion in CLI"
RUN_SC_GUI = "Run Scorpion on a GUI"
EXIT = "Exit"

# options
LEVEL = "Level"
URL = "url"
RECURSIVE = "recursive"
PATH = "path"
DEBUG = "debug"
RUN_TESTS = "Run tests"

# constant values
MAX_RESPONSE_SIZE = 20 * 1024 * 1024
MAX_IMAGE_SIZE = 50 * 1024 * 1024
CHUNK_SIZE = 8192
MAX_LINKS = 50
MAX_IMAGES = 20

# paths
SPIDER_PATH = Path(__file__).resolve().parent
SCORPION_PATH = (SPIDER_PATH.parent / "../scorpion").resolve()
SCORPION_EXEC = SCORPION_PATH / "scorpion.py"
SCORPION_INTERPRETER = SCORPION_PATH / ".venv" / "bin" / "python"
