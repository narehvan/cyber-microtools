#!/usr/bin/env python3
"""Extract email addresses from a web page, including common obfuscations.

Fetches a URL and runs a set of statically-decodable extractors against the
raw HTML. Each extractor is a small function that returns a set of emails, so
adding support for a new obfuscation scheme is just: write a function and add
it to EXTRACTORS.

Handles (all decodable from the raw HTML, no JavaScript needed):
  - plain mailto: links
  - plain-text addresses in the markup
  - Cloudflare email obfuscation (data-cfemail / email-protection#)
  - HTML-entity encoding (&#116;&#101;... decimal or hex)
  - [at] / [dot] style obfuscation (test [at] example [dot] com)
  - reversed strings flipped with CSS direction:rtl

What it CANNOT do (the address isn't in the HTML; needs a browser to render):
  - JavaScript that builds the address at runtime (concatenation, base64, ROT13)
  - addresses fetched from an API on click
If nothing is found, the script says so and lists these JS-based possibilities.
"""
import argparse
import html
import re
import ssl
import sys
import urllib.request

# A reasonable email shape. Deliberately not RFC-5322-complete: 
# want common real-world forms without matching half the page.
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


# --- extractors -------------------------------------------------------------
# Each takes the page HTML and returns a set of plain email strings. The
# method label (shown with -t) comes from the EXTRACTORS list

def extract_mailto(page_html):
    """Addresses in mailto: links (strips any ?subject=... query)."""
    emails = set()
    for link_target in re.findall(r"mailto:([^\"'?>\s]+)", page_html):
        emails.add(html.unescape(link_target))
    return emails


def extract_plaintext(page_html):
    """Addresses written in clear in the markup."""
    return set(EMAIL_PATTERN.findall(page_html))


def decode_cloudflare_hex(hex_blob):
    """Reverse Cloudflare's XOR obfuscation.

    The first byte of the blob is the XOR key; every following byte is XORed
    with it to recover the original ASCII characters.
    """
    encoded_bytes = bytes.fromhex(hex_blob)
    xor_key = encoded_bytes[0]
    return "".join(chr(byte ^ xor_key) for byte in encoded_bytes[1:])


def extract_cloudflare(page_html):
    """Cloudflare obfuscation: XOR-encoded hex in data-cfemail / href."""
    emails = set()
    hex_blobs = re.findall(
        r'(?:data-cfemail="|email-protection#)([a-f0-9]{6,})', page_html)
    for hex_blob in hex_blobs:
        try:
            email = decode_cloudflare_hex(hex_blob)
            if EMAIL_PATTERN.fullmatch(email):
                emails.add(email)
        except (ValueError, IndexError):
            pass
    return emails


def extract_html_entities(page_html):
    """Addresses hidden as HTML entities (&#116;&#101;... or &#x74;...).

    Unescape the whole page, then keep only addresses that were NOT already
    readable as plain text (those are covered by extract_plaintext).
    """
    if "&#" not in page_html:
        return set()
    
    unescaped_html = html.unescape(page_html)
    entity_emails = set(EMAIL_PATTERN.findall(unescaped_html))
    return entity_emails - extract_plaintext(page_html)


def extract_at_dot(page_html):
    """'test [at] example [dot] com' and friends: (at)/(dot), spaces, etc."""
    # Normalize the common at/dot spellings back into @ and . so the normal
    # email pattern can match them.
    normalized_html = re.sub(r"\s*[\[(]\s*at\s*[\])]\s*", "@", page_html, flags=re.I)
    normalized_html = re.sub(r"\s*[\[(]\s*dot\s*[\])]\s*", ".", normalized_html, flags=re.I)
    
    # Also the bare-word spaced form: "test at example dot com"
    normalized_html = re.sub(r"\s+at\s+", "@", normalized_html)
    normalized_html = re.sub(r"\s+dot\s+", ".", normalized_html)
    candidate_emails = set(EMAIL_PATTERN.findall(normalized_html))
    
    # Drop ones that were already plainly present (those weren't obfuscated).
    return candidate_emails - extract_plaintext(page_html)


def extract_reversed(page_html):
    """Addresses stored backwards and flipped with CSS direction:rtl.

    Reversing the whole page turns a genuinely-backwards address into a
    readable one -- but it also turns every ordinary forward address into a
    reversed string that still looks email-shaped. Keep a candidate only
    if reversing it back does NOT yield a valid email: a real address reversed
    is almost never still valid (".com" becomes a leading "moc."), so this
    drops the false positives while keeping true RTL-obfuscated addresses.
    """
    emails = set()
    for candidate in EMAIL_PATTERN.findall(page_html[::-1]):
        if not EMAIL_PATTERN.fullmatch(candidate[::-1]):
            emails.add(candidate)
    return emails


# Order matters only for which method label wins when the same address is found
# by several extractors (earlier = preferred label). mailto/plaintext come
# first so a clearly-readable address isn't mislabeled as an exotic method
EXTRACTORS = [
    ("mailto", extract_mailto),
    ("plaintext", extract_plaintext),
    ("cloudflare", extract_cloudflare),
    ("html-entities", extract_html_entities),
    ("at-dot", extract_at_dot),
    ("reversed", extract_reversed),
]

JS_ONLY_HINT = """\
No email addresses could be extracted from the page source.

The address may be built by JavaScript at runtime, which this tool cannot see
(it reads only the static HTML). Possibilities to check manually in a browser:
  - JS string concatenation / base64 / ROT13 decoded on the page
  - address fetched from an API when a link is clicked
  - a WordPress/anti-spam plugin that assembles the address client-side
Open the page in a browser, let it render, and inspect the final DOM."""


def fetch_page(url, skip_cert_check=False, timeout_seconds=20):
    """Download a URL and return its decoded HTML text."""
    ssl_context = None
    if skip_cert_check:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=timeout_seconds, context=ssl_context) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def harvest_emails(page_html):
    """Run every extractor and return {email: method_that_found_it_first}."""
    email_to_method = {}
    for method_name, extractor_fn in EXTRACTORS:
        for email in extractor_fn(page_html):
            email_to_method.setdefault(email, method_name)  # first method wins
    return email_to_method

# --- main -------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Extract (and de-obfuscate) emails from a web page.")
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("url", nargs="?", help="page URL to fetch and scan")
    source_group.add_argument("-f", "--from-file", metavar="PATH", help="scan an already-downloaded HTML file instead of fetching a URL")
    parser.add_argument("-o", "--output", help="write results to this file (default: stdout)")
    parser.add_argument("-t", "--tag", action="store_true", help="append the detection method as [method] after each email")
    parser.add_argument("-k", "--insecure", action="store_true", help="skip TLS certificate verification (default: verify)")
    cli = parser.parse_args()

    try:
        if cli.from_file:
            with open(cli.from_file, "r", errors="replace") as html_file:
                page_html = html_file.read()
        else:
            page_html = fetch_page(cli.url, skip_cert_check=cli.insecure)
    except Exception as err:
        source_name = cli.from_file or cli.url
        sys.exit(f"error: could not read {source_name}: {err}")

    email_to_method = harvest_emails(page_html)

    if not email_to_method:
        sys.stderr.write(JS_ONLY_HINT + "\n")
        sys.exit(2)

    output_lines = []
    for email in sorted(email_to_method):
        if cli.tag:
            output_lines.append(f"{email} [{email_to_method[email]}]")
        else:
            output_lines.append(email)
    output_text = "\n".join(output_lines) + "\n"

    if cli.output:
        with open(cli.output, "w") as output_file:
            output_file.write(output_text)
        sys.stderr.write(
            f"wrote {len(email_to_method)} address(es) to {cli.output}\n")
    else:
        sys.stdout.write(output_text)


if __name__ == "__main__":
    main()