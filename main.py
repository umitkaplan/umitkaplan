"""Entry point for repository automation.

This repository primarily contains a Revit Python script that can turn
model lines into walls.  Running this module as a script simply prints a
short message so that executing ``python main.py`` outside of Revit does
not fail.
"""


def main():
    """Print a short note about the available Revit script."""

    message = (
        "This repository provides `model_lines_to_walls.py`, a Python "
        "script intended to run inside Revit (pyRevit/RevitPythonShell)."
    )
    print(message)


if __name__ == "__main__":
    main()

