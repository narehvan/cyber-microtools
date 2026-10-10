#!/usr/bin/env python3
"""Decode or encode a Cloudflare-obfuscated email (cloudflare_email hex string).

Decode (default): given a cloudflare_email hex string, print the plain email.
Encode (--encode): given a plain email, print a cloudflare_email hex string that
decodes back to it.

Cloudflare's obfuscation is a simple XOR: the first byte of the hex is the
key, and every following byte is XORed with it. Encoding picks an arbitrary
key byte, so the same email can produce many different valid hex strings --
all decode to the same address.

The Cloudflare's obfuscation code is baked into Cloudflare's "email-decode.min.js"

curl command to extract the hex values. Replace URL with your https:// URL:

curl -s URL \
  | grep -oE '(email-protection#|data-cloudflare_email=")[a-f0-9]+' \
  | grep -oE '[a-f0-9]{6,}' \
  | sort -u > hexes.txt

"""
import argparse
import random


def decode_cloudflare_email(hex_string):
    data = bytes.fromhex(hex_string)
    key = data[0]
    return "".join(chr(b ^ key) for b in data[1:])


def encode_cloudflare_email(email, key=None):
    if key is None:
        key = random.randint(1, 255)
    return bytes([key, *(ord(c) ^ key for c in email)]).hex()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("value", help="cloudflare_email hex to decode, or email to encode with --encode")
    p.add_argument("-e", "--encode", action="store_true", help="encode the given email into a cloudflare_email hex string")
    p.add_argument("-k", "--key", type=lambda x: int(x, 0), help="XOR key byte for encoding (e.g. 0x7a); random if omitted")
    args = p.parse_args()

    if args.encode:
        print(encode_cloudflare_email(args.value, args.key))
    else:
        print(decode_cloudflare_email(args.value))
