import json
import os
from flask import Flask, render_template, jsonify, abort

app = Flask(__name__)

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "dashboard_data.json")


def _load_data():
    if not os.path.exists(DATA_PATH):
        abort(503, description="Dashboard data not yet available. Run: python agent/run_daily.py")
    with open(DATA_PATH) as f:
        return json.load(f)


@app.route("/")
def dashboard():
    data = _load_data()
    return render_template("dashboard.html", data=data)


@app.route("/api/data")
def api_data():
    return jsonify(_load_data())


if __name__ == "__main__":
    app.run(debug=True)
