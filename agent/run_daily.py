#!/usr/bin/env python3
"""Daily agent entry point. Run this via PythonAnywhere scheduled task:
   cd /home/<username>/spx-dashboard && python agent/run_daily.py
"""
import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)

from agent.fetch_data import build_dashboard_data, save_data

if __name__ == "__main__":
    data = build_dashboard_data()
    save_data(data)
    print(f"Dashboard data updated at {data['updated_at']}")
    print(f"SPX 5d MA: {data['spx']['callout']['ma5_today']} "
          f"({data['spx']['callout']['direction']} than yesterday's "
          f"{data['spx']['callout']['ma5_yesterday']})")
    print(f"Holdings fetched: {len(data['holdings'])}")
