import argparse
from uci.adapter import UCIAdapter


def main():
    parser = argparse.ArgumentParser(description="Hackathon Chess Engine (UCI)")
    parser.add_argument("--depth", type=int, default=3, help="Search depth (default: 3)")
    args = parser.parse_args()

    adapter = UCIAdapter(depth=args.depth)
    adapter.run()


if __name__ == "__main__":
    main()
