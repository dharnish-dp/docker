import requests
import sys

url = "https://httpbin.org/get"
response = requests.get(url)

print(f"Status code: {response.status_code}")
print(f"Python version inside container: {sys.version}")
print(f"Response JSON: {response.json()['url']}")
# a comment
# another comment
print("bind mount works!")
