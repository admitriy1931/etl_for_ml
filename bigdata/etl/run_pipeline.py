from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPTS = [
    "export_to_minio.py",
    "train_flow_model.py",
    "anomaly_failure_model.py",
    "logistics_analysis.py",
]


def main() -> None:
    root = Path(__file__).resolve().parent
    for script in SCRIPTS:
        print(f"\n=== Running {script} ===")
        subprocess.run([sys.executable, str(root / script)], check=True)


if __name__ == "__main__":
    main()
