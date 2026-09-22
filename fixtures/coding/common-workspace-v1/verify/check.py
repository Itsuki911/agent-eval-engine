from pathlib import Path

if not Path("../verify/check.py").is_file():
    raise SystemExit("verification file is missing")

print("common fixture healthy")
