#!/usr/bin/env python3
#Initial project setup with basic CLI argument parsing
import argparse

def main():
    parser = argparse.ArgumentParser(description="go2web - Minimal web client")
    parser.add_argument("-u", "--url", help="Fetch content from URL")
    parser.add_argument("-s", "--search", nargs="+", help="Search term to query on Bing")
    parser.add_argument("--json", action="store_true", help="Prefer JSON format")
    args = parser.parse_args()

    if args.url:
        print(f"URL mode: {args.url}")
    elif args.search:
        print(f"Search mode: {' '.join(args.search)}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
