import requests, re, json

url = 'https://www.walmart.ca/en/ip/dairyland-2-milk/10183930'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
r = requests.get(url, headers=headers)

match = re.search(r'__PRELOADED_STATE__\s*=\s*(\{.+?\})\s*;', r.text, re.DOTALL)
if match:
    print('Found state!')
else:
    print('Not found')
    print('currentPrice in HTML:', '\"currentPrice\"' in r.text)
    print('Status code:', r.status_code)
