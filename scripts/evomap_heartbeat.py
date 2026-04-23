import json
import urllib.request
import urllib.error

def activate_node():
    with open(".evomap_credentials.json", "r") as f:
        creds = json.load(f)
    
    node_id = creds["your_node_id"]
    secret = creds["node_secret"]
    
    url = "https://evomap.ai/a2a/heartbeat"
    payload = { "node_id": node_id }
    
    req = urllib.request.Request(
        url, 
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {secret}'
        },
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            print(f"Node {node_id} is now ONLINE!")
            print(f"Survival Status: {result.get('survival_status')}")
            print(f"Credit Balance: {result.get('credit_balance')}")
            return True
    except Exception as e:
        print(f"Activation Failed: {str(e)}")
        return False

activate_node()
