#!/bin/sh
# Usage: PYTHON=/path/to/python sh code/run_analysis.sh (from project directory).
set -eu
PYTHON="${PYTHON:-python3}"
if [ "$(uname -s)" = Darwin ]; then
  OMP_DIR="$($PYTHON -c 'import importlib.util,pathlib; print(pathlib.Path(importlib.util.find_spec("sklearn").origin).parent / ".dylibs")')"
  export DYLD_LIBRARY_PATH="$OMP_DIR${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"
fi
"$PYTHON" code/analyze.py
"$PYTHON" code/audit.py
"$PYTHON" code/render_report.py
quarto render index.qmd
