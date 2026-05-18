"""Entry point — `python run.py [path]`."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))

from main import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
