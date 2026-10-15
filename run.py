"""Entry point used by PyInstaller (and handy for `python run.py`)."""

from wincam.app import main

if __name__ == "__main__":
    raise SystemExit(main())
