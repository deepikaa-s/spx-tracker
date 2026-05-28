"""Render dashboard.html into docs/index.html using Jinja2 directly (no Flask)."""
import json
import os
import shutil

from jinja2 import Environment, FileSystemLoader

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA_PATH = os.path.join(ROOT, "data", "dashboard_data.json")
DOCS_DIR = os.path.join(ROOT, "docs")


def build():
    with open(DATA_PATH) as f:
        data = json.load(f)

    env = Environment(loader=FileSystemLoader(os.path.join(ROOT, "templates")))
    # Mock Flask's url_for — returns just the filename for static assets
    env.globals["url_for"] = lambda endpoint, **kwargs: kwargs.get("filename", "")

    template = env.get_template("dashboard.html")
    html = template.render(data=data)

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "index.html"), "w") as f:
        f.write(html)

    shutil.copy(os.path.join(ROOT, "static", "style.css"),
                os.path.join(DOCS_DIR, "style.css"))

    print(f"Built docs/index.html  (updated_at: {data['updated_at']})")


if __name__ == "__main__":
    build()
