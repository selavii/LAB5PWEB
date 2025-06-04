import argparse
import socket
import ssl
import html2text
import webbrowser
from urllib.parse import urlparse, quote_plus
from bs4 import BeautifulSoup

def perform_http_get(target_url, accept='text/html'):
    try:
        parsed = urlparse(target_url)
        if not parsed.scheme:
            target_url = "http://" + target_url
            parsed = urlparse(target_url)

        host = parsed.netloc
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        port = 443 if parsed.scheme == "https" else 80

        headers = {
            "Host": host,
            "User-Agent": "go2web",
            "Accept": accept,
            "Connection": "close"
        }

        request = f"GET {path} HTTP/1.1\r\n" + ''.join(f"{k}: {v}\r\n" for k, v in headers.items()) + "\r\n"

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as raw_sock:
            sock = ssl.create_default_context().wrap_socket(raw_sock, server_hostname=host) if parsed.scheme == "https" else raw_sock
            sock.connect((host, port))
            sock.sendall(request.encode())

            response = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk

        header, _, body = response.partition(b"\r\n\r\n")
        return "text/html", body.decode("utf-8", errors="ignore")

    except Exception as e:
        print(f"Request error: {e}")
        return None, None

def convert_to_text(html_content):
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True
    return h.handle(html_content)

def search_bing(query):
    encoded = quote_plus(query)
    url = f"http://www.bing.com/search?q={encoded}"
    ctype, html = perform_http_get(url)
    if not html:
        print("Search failed.")
        return

    soup = BeautifulSoup(html, "html.parser")
    results = soup.find_all("li", class_="b_algo")

    links = []
    print(f"\nTop {min(10, len(results))} results for '{query}':\n")
    for i, result in enumerate(results[:10], 1):
        link = result.find("a")
        title = link.get_text(strip=True) if link else "No title"
        href = link["href"] if link and link.has_attr("href") else "No link"
        print(f"{i}. {title}\n   {href}\n")
        links.append(href)

    try:
        choice = int(input("Enter result number to open (0 to skip): "))
        if 1 <= choice <= len(links):
            webbrowser.open(links[choice - 1])
            print("Opened in browser.")
        elif choice == 0:
            print("No link opened.")
        else:
            print("Invalid choice.")
    except ValueError:
        print("Invalid input.")

def main():
    parser = argparse.ArgumentParser(description="go2web - Minimal web client")
    parser.add_argument("-u", "--url", help="Fetch content from URL")
    parser.add_argument("-s", "--search", nargs="+", help="Search term to query on Bing")
    parser.add_argument("--json", action="store_true", help="Prefer JSON format")
    args = parser.parse_args()

    if args.url:
        accept_type = "application/json" if args.json else "text/html"
        ctype, body = perform_http_get(args.url, accept_type)
        if body:
            output = body if "json" in ctype else convert_to_text(body)
            print(output)
    elif args.search:
        query = " ".join(args.search)
        search_bing(query)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
