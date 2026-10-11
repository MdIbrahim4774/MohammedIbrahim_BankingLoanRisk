# Entry point forwarding to frontend/app.py
import runpy
import sys
import os

if __name__ == "__main__":
    app_path = os.path.join(os.path.dirname(__file__), "frontend", "app.py")
    runpy.run_path(app_path, run_name="__main__")

