
import os
import requests
import socket
from google.auth import default
from googleapiclient.discovery import build
from google.cloud import bigquery

def test_url(name, url, proxy=None):
    proxies = {"http": proxy, "https": proxy} if proxy else {"http": "", "https": ""}
    try:
        response = requests.get(url, proxies=proxies, timeout=5)
        print(f"[{name}] URL: {url} | Proxy: {proxy} | Status: {response.status_code}")
        return True
    except Exception as e:
        print(f"[{name}] URL: {url} | Proxy: {proxy} | Error: {str(e)[:100]}")
        return False

def test_dns(hostname):
    try:
        addr = socket.gethostbyname(hostname)
        print(f"[DNS] {hostname} -> {addr}")
        return True
    except Exception as e:
        print(f"[DNS] {hostname} -> Failed: {e}")
        return False

urls = [
    "https://www.googleapis.com/discovery/v1/apis",
    "https://oauth2.googleapis.com/token",
    "https://accounts.google.com/.well-known/openid-configuration"
]

hsbc_proxy = "http://googleapis-dev-gcp.cloud.uk.hsbc:3128"

print("--- DNS Tests ---")
test_dns("www.googleapis.com")
test_dns("oauth2.googleapis.com")
test_dns("googleapis-dev-gcp.cloud.uk.hsbc")

print("\n--- Direct Connectivity Tests ---")
for url in urls:
    test_url("Direct", url, None)

print("\n--- HSBC Proxy Connectivity Tests ---")
for url in urls:
    test_url("HSBC Proxy", url, hsbc_proxy)

print("\n--- Auth Test (DIRECT ENV) ---")
for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
    os.environ.pop(var, None)
try:
    creds, project = default()
    client = bigquery.Client()
    projects = list(client.list_projects(max_results=1))
    print("Direct Auth/BQ: SUCCESS")
except Exception as e:
    print(f"Direct Auth/BQ: FAILED - {e}")

print("\n--- Auth Test (HSBC PROXY ENV) ---")
os.environ['HTTP_PROXY'] = os.environ['HTTPS_PROXY'] = hsbc_proxy
try:
    creds, project = default()
    client = bigquery.Client()
    projects = list(client.list_projects(max_results=1))
    print("Proxy Auth/BQ: SUCCESS")
except Exception as e:
    print(f"Proxy Auth/BQ: FAILED - {e}")
