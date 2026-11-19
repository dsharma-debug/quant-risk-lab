"""Rebuild numerical experiments, CSVs and charts with recorded provenance."""

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import platform
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true",
                        help="Use smaller repeated studies for a setup check")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    output = root / "results"
    logs = output / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    repeats = ["--runs", "20"] if args.quick else []
    paths = ["--paths", "50"] if args.quick else []
    commands = [
        ["main.py"],
        ["compare_pricers.py"],
        ["compare_monte_carlo.py"],
        ["delta_experiment.py"],
        ["plot_delta_convergence.py"],
        ["mc_repeated_experiment.py", *repeats],
        ["compare_variance_reduction.py", *repeats],
        ["check_greeks.py"],
        ["run_hedge.py"],
        ["hedging_study.py", *paths],
        ["plot_hedging_study.py"],
        ["volatility_study.py", *paths],
        ["plot_volatility_study.py"],
    ]
    for index, command in enumerate(commands, start=1):
        print(f"[{index}/{len(commands)}] {' '.join(command)}", flush=True)
        result = subprocess.run([sys.executable, *command], cwd=root,
                                text=True, capture_output=True)
        text = result.stdout
        if result.stderr:
            text += "\n[stderr]\n" + result.stderr
        (logs / f"{Path(command[0]).stem}.txt").write_text(
            text.replace(str(root), "."), encoding="utf-8"
        )
        if result.returncode:
            print(text.replace(str(root), "."), file=sys.stderr)
            raise SystemExit(result.returncode)

    dependencies = {}
    for package in ("matplotlib", "pandas", "streamlit"):
        try:
            dependencies[package] = version(package)
        except PackageNotFoundError:
            dependencies[package] = None
    source_paths = (sorted(root.glob("*.py")) + sorted(root.glob("requirements*.txt"))
                    + [root / ".github/workflows/tests.yml"])
    source_hashes = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
                     for path in source_paths}
    result_hashes = {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(output.glob("*"))
        if path.is_file() and path.name != "run_manifest.json"
    }
    manifest = dict(created_at_utc=datetime.now(timezone.utc).isoformat(),
                    mode="quick" if args.quick else "reference",
                    python=platform.python_version(), platform=platform.system(),
                    dependencies=dependencies, commands=commands,
                    source_sha256=source_hashes, result_sha256=result_hashes)
    (output / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Complete. Results, command logs and run_manifest.json are in results/.")


if __name__ == "__main__":
    main()
