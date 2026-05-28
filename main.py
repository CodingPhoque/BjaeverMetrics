import sys
from pathlib import Path


def _load_cli_main():
    # Ensure the src directory is in sys.path so we can import the CLI module and use its main() function.
    src_path = Path(__file__).resolve().parent / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    # Only now can we import the CLI function from fodbold.cli, as src_path is now in sys.path
    from fodbold.cli import main

    # The CLI function is returned, not run
    return main


if __name__ == "__main__":
    # Here the main() function is executed with the ()() and its exit code is used to exit the program
    raise SystemExit(_load_cli_main()())
