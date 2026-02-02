import requests

def submit_update(url, payload):
    r = requests.post(f"{url}/aggregator/submit-update", json=payload)
    r.raise_for_status()
