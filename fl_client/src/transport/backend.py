import requests

def submit_update(url, payload):
    r = requests.post(f"{url}/miner/submit", json=payload)
    r.raise_for_status()
