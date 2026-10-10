# cloudflare_email_deobfuscator
Decrypt Cloudflare's obfuscated email to human readable email
Encrypt human readable email to Cloudflare's obfuscated email

# Usage
## Decode (default option)
`python3 cloudflare_email_deobfuscator.py <encoded hexadecimal string>`

## Encode (random key) output is random string
`python3 cloudflare_email_deobfuscator.py -e <email address>`

## Encode (fixed key) output is reproducible string
`python3 cloudflare_email_deobfuscator.py -e -k <key> <email address>`

## examples
`python3 cloudflare_email_deobfuscator.py 7a0e1f090e3a1f021b170a161f54191517`
`python3 cloudflare_email_deobfuscator.py -e test@example.com`
`python3 cloudflare_email_deobfuscator.py -e -k 0x7a test@example.com`

# Note
To extract the hex values from a URL, use the curl command below. 
Replace the "URL" string with your "https://..." string

```
curl -s URL \
  | grep -oE '(email-protection#|data-cfemail=")[a-f0-9]+' \
  | grep -oE '[a-f0-9]{6,}' \
  | sort -u > extracted_hexes.txt
```