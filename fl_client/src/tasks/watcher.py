import requests

def poll_tasks(base_url):
    r = requests.get(f"{base_url}/tasks/open")
    r.raise_for_status()
    return r.json()
