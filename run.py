"""Top-level launcher (also the PyInstaller entry point).

`app/main.py` uses relative imports internally, so it cannot be run
directly as a script (`python app/main.py` or a frozen PyInstaller build
pointed at that file would fail with "attempted relative import"). This
thin wrapper imports the `app` package properly instead.
"""

import sys

from app.main import main

if __name__ == "__main__":
    sys.exit(main())
