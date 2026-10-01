"""python -m pipeline build [--version v1.0] [--no-screens]
python -m pipeline test
python -m pipeline pull     (form submissions straight from Tally; needs TALLY_API_KEY in .env)"""
import argparse
import json
import sys
import unittest
from pathlib import Path


def main():
    p = argparse.ArgumentParser(prog="pipeline")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="raw/ -> release/<version>/")
    b.add_argument("--version", default="dev")
    b.add_argument("--no-screens", action="store_true", help="skip screenshot download + OCR")
    sub.add_parser("test", help="run the test suite")
    sub.add_parser("pull", help="download all form submissions from the Tally API")
    a = p.parse_args()

    if a.cmd == "test":
        import os
        os.environ.setdefault("STOPARNAQUE_ALLOW_NEW_KEY", "1")  # a fresh clone has no key; tests may make a throwaway one
        root = Path(__file__).resolve().parent.parent
        suite = unittest.defaultTestLoader.discover(str(root / "pipeline" / "tests"), top_level_dir=str(root))
        sys.exit(0 if unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful() else 1)

    if a.cmd == "pull":
        from .pull_tally import pull
        pull(Path(__file__).resolve().parent.parent)
        return

    from .build import build
    res = build(a.version, with_screens=not a.no_screens)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
