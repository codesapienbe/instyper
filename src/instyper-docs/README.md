# Instyper Developer Documentation

This module contains the Sphinx-based developer documentation for Instyper.

## How to build the docs

1. Install dependencies from the project root:
   ```bash
   pip install -r requirements.txt  # or use pyproject.toml
   ```
2. Build the HTML docs:
   ```bash
   sphinx-build -b html . _build/html
   ```
3. Open `_build/html/index.html` in your browser. 