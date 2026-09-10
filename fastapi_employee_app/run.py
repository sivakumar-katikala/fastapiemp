"""
run.py

Convenience script to launch the app with Uvicorn (the ASGI server).
Equivalent to running: uvicorn app.main:app --reload

Usage:
    python run.py
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
