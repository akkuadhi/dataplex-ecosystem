
import os
import requests
from google.auth import default
from googleapiclient.discovery import build

def check_connectivity(proxy=None):
    """Checks connectivity to Google Discovery and OAuth APIs with an optional proxy."""
    discovery_url = "https://www.googleapis.com/discovery/v1/apis"
    oauth_url = "https://oauth2.googleapis.com/token"
    proxies = {"http": proxy, "https": proxy} if proxy else {"http": "", "https": ""}
    try:
        # 1. Check Discovery (General API access)
        d_res = requests.get(discovery_url, proxies=proxies, timeout=5)
        is_google = d_res.status_code == 200 and "discovery#directoryItem" in d_res.text
        
        # 2. Check OAuth (Authentication access)
        # A 404 or 405 on a GET to /token is usually fine, it means the server is reached.
        # A timeout or connection error means it's blocked.
        o_res = requests.get(oauth_url, proxies=proxies, timeout=5)
        is_oauth_reachable = o_res.status_code in [200, 400, 404, 405]
        
        return is_google and is_oauth_reachable
    except:
        return False

def get_best_proxy():
    """Identifies the best proxy to use: Direct first, then HSBC proxy."""
    hsbc_proxy = "http://googleapis-dev-gcp.cloud.uk.hsbc:3128"
    
    # Try Direct first
    if check_connectivity(None):
        return None, "Direct"
    
    # Try HSBC proxy
    if check_connectivity(hsbc_proxy):
        return hsbc_proxy, "Corporate Proxy (HSBC)"
            
    return "Manual", "Manual Required"

def setup_environment_logic():
    """Common logic for setting up the environment, used by both Hub and specialized UIs."""
    # Reset proxies for a clean start
    for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
        os.environ.pop(var, None)
    
    proxy, mode = get_best_proxy()
    
    if proxy == "Manual":
        return False, mode, "❌ Network Error (Proxy required?)"
    
    if proxy:
        os.environ['HTTP_PROXY'] = os.environ['HTTPS_PROXY'] = proxy
        os.environ['http_proxy'] = os.environ['https_proxy'] = proxy
    
    try:
        creds, project = default()
        
        # Live verification - Try Resource Manager first
        try:
            temp_rm = build('cloudresourcemanager', 'v1', credentials=creds, cache_discovery=False)
            temp_rm.projects().list(pageSize=1).execute()
        except Exception as rm_err:
            # If RM fails (often due to permissions), try BigQuery as fallback
            if "forbidden" in str(rm_err).lower() or "permission" in str(rm_err).lower():
                try:
                    temp_bq = build('bigquery', 'v2', credentials=creds, cache_discovery=False)
                    temp_bq.projects().list().execute()
                except Exception as bq_err:
                    raise Exception(f"Live verification failed (RM & BQ). RM error: {str(rm_err)[:50]} | BQ error: {str(bq_err)[:50]}")
            else:
                # Likely a network error if it's not a permission issue
                raise rm_err

        return True, mode, "✅ Authenticated & Connected"
    except Exception as e:
        error_msg = str(e)
        return False, mode, f"❌ Auth Failed: {error_msg[:50]}"
