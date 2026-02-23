"""CLI entry point for gh-md-fetch."""

import sys


def main():
    if len(sys.argv) < 2:
        print("Usage: gh md-fetch <url>", file=sys.stderr)
        sys.exit(1)

    print("gh-md-fetch is ready")


if __name__ == "__main__":
    main()
