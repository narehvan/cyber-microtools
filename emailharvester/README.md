# emailharvester
Scrap email addresses from a URL or a file and either print them to console to save then to a file
Each email in a single line

Uses `import urllib.request` for web access.

# Usage
```
python3 emailharvester.py URL                           # fetch and scan
python3 emailharvester.py -f page.html                  # scan a saved HTML file
python3 emailharvester.py -t -f page.html               # file + method tags
python3 emailharvester.py -f page.html -o emails.txt    # file + outputfile name
```

## Options
`-f` - read a file instead of a URL
`-t` - next to each email address, print the extraction method the email address was stored in the HTML
`-k` - Ignore certificate verification
`-o` - save the extracted email address to a file, instead of output to console