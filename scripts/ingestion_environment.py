"""Load local ingestion environment data without shell evaluation."""
import os
from pathlib import Path
import re
import sys

from dotenv.parser import parse_stream


def merged_environment(path: Path, inherited: dict[str, str]) -> dict[str, str]:
    values = {}
    if path.exists():
        with path.open(encoding="utf-8") as stream:
            for binding in parse_stream(stream):
                if binding.error:
                    raise ValueError("Invalid ingestion environment file")
                if binding.key is None:
                    continue
                if (not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", binding.key)
                        or binding.value is None or "\0" in binding.value):
                    raise ValueError("Invalid ingestion environment assignment")
                values[binding.key] = binding.value
    return {**values, **inherited}


def main():
    scripts = Path(__file__).resolve().parent
    try:
        environment = merged_environment(scripts.parent / "configs/.env", dict(os.environ))
        os.execvpe("bash", ["bash", str(scripts / "ingest-with-questions.sh"),
                           "--environment-loaded", *sys.argv[1:]], environment)
    except (OSError, ValueError):
        print("ERROR: Unable to load ingestion environment or launch ingestion.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
