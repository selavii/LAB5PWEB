#!/usr/bin/env python3

import socket
import ssl
import argparse
import pickle
import hashlib
import os
import sys
import json
from urllib.parse import urlparse, quote_plus
from pathlib import Path
import html2text
from bs4 import BeautifulSoup
import webbrowser

# Directory for caching responses
CACHE_PATH = Path.home() / ".go2web_cache"
CACHE_PATH.mkdir(exist_ok=True)

def build_cache_name(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()

def load_from_cache(url: str):
    file = CACHE_PATH / build_cache_name(url)
    if file.exists():
        with open(file, "rb") as f:
            return pickle.load(f)
    return None

def save_to_cache(url: str, data):
    file = CACHE_PATH / build_cache_name(url)
    with open(file, "wb") as f:
        pickle.dump(data, f)

def perform_http_get(target_url, accept='text/html', depth=5):
    if depth == 0:
        return None, "Redirect loop detected."

    cached = load_from_cache(target_url)
    if cached:
        return cached['type'], cached['body']

    try:
        parsed = urlparse(target_url)
        if not parsed.scheme:
            target_url = "http://" + target_url
            parsed = urlparse(target_url)

        port = 443 if parsed.scheme == "https" else 80
        host = parsed.netloc
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query

        headers = {
            "Host": host,
            "User-Agent": "go2web-browser",
            "Accept": accept,
            "Connection": "close"
        }

        req = f"GET {path} HTTP/1.1\r\n"
        req += ''.join(f"{k}: {v}\r\n" for k, v in headers.items()) + "\r\n"

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as raw_sock:
            if parsed.scheme == "https":
                context = ssl.create_default_context()
                sock = context.wrap_socket(raw_sock, server_hostname=host)
            else:
                sock = raw_sock
            sock.connect((host, port))
            sock.sendall(req.encode())

            reply = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                reply += chunk

        header_section, _, body_bytes = reply.partition(b"\r\n\r\n")
        headers_text = header_section.decode("utf-8", errors="ignore")
        body_text = body_bytes.decode("utf-8", errors="ignore")

        lines = headers_text.splitlines()
        status_line = lines[0]

        if "301" in status_line or "302" in status_line:
            for h in lines:
                if h.lower().startswith("location:"):
                    redirect_to = h.split(":", 1)[1].strip()
                    if not redirect_to.startswith("http"):
                        redirect_to = f"{parsed.scheme}://{host}{redirect_to}"
                    return perform_http_get(redirect_to, accept, depth-1)

        content_type = next((l.split(":", 1)[1].strip() for l in lines if l.lower().startswith("content-type:")), "text/html")
        save_to_cache(target_url, {"type": content_type, "body": body_text})
        return content_type, body_text

    except Exception as error:
        print(f"[!] Network error: {error}")
        return None, None

def to_readable(content_type, content):
    if "application/json" in content_type:
        try:
            return json.dumps(json.loads(content), indent=2)
        except:
            return content
    return convert_html_to_text(content)

def convert_html_to_text(html):
    parser = html2text.HTML2Text()
    parser.ignore_links = False
    parser.ignore_images = True
    return parser.handle(html)

def bing_search(query):
    search_url = f"http://www.bing.com/search?q={quote_plus(query)}"
    ctype, html = perform_http_get(search_url)

    if not html:
        print("Search failed or returned no data.")
        return []

    soup = BeautifulSoup(html, "html.parser")
    found = []

    for item in soup.find_all("li", class_="b_algo"):
        link = item.find("a")
        if link:
            found.append({
                "title": link.get_text(strip=True),
                "link": link.get("href")
            })
        if len(found) >= 10:
            break

    for idx, res in enumerate(found, 1):
        print(f"{idx}. {res['title']}\n   {res['link']}\n")

    try:
        choice = int(input("Enter number to open (0 to skip): "))
        if 1 <= choice <= len(found):
            webbrowser.open(found[choice - 1]["link"])
            print("Opening in browser...")
    except ValueError:
        print("Invalid input.")

    return found

def parse_args():
    parser = argparse.ArgumentParser(description="go2web - Minimal web client")
    parser.add_argument("-u", "--url", help="Fetch content from URL")
    parser.add_argument("-s", "--search", nargs="+", help="Search term to query on Bing")
    parser.add_argument("--json", action="store_true", help="Prefer JSON format")
    return parser.parse_args()

def main():
    args = parse_args()

    if args.url:
        accept_type = "application/json" if args.json else "text/html"
        ctype, content = perform_http_get(args.url, accept_type)
        if content:
            print(to_readable(ctype, content))
        else:
            print("Failed to retrieve the page.")
    elif args.search:
        term = " ".join(args.search)
        bing_search(term)
    else:
        print("No input provided. Use -u <url> or -s <search term>.")

if __name__ == "__main__":
    main()
