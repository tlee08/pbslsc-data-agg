## Dev

```bash
uv sync
```

```bash
uv run marimo edit
```

## Deploy

From template here: https://github.com/marimo-team/marimo-gh-pages-template

```bash
uv run .github/scripts/build.py --template templates/tailwind.html.j2
```

```bash
uv run -m http.server -d _site
```
