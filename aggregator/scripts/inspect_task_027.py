import requests
import json

def inspect():
    r = requests.get('http://localhost:3000/aggregator/task_027/submissions')
    subs = r.json()
    if not subs:
        print("No submissions found")
        return
    
    sub = subs[0]
    print(f"Submission Keys: {list(sub.keys())}")
    print(f"Miner Address: {sub.get('minerAddress') or sub.get('miner_address')}")
    pk = sub.get('miner_pk', '')
    sig = sub.get('signature', '')
    print(f"Miner PK: {pk}")
    print(f"Signature: {sig}")
    
    ct_list = sub.get('ciphertext', [])
    if ct_list:
        print(f"First Ciphertext Entry: {ct_list[0]}")
    print(f"Has Ciphertext: {bool(ct_list)}")

if __name__ == '__main__':
    inspect()
