import json
import urllib.request
import urllib.error

def activate_node(node_id, secret):
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
            
            # Save the valid credentials
            creds = {
                "your_node_id": node_id,
                "node_secret": secret,
                "status": "active",
                "last_heartbeat": result.get("timestamp")
            }
            with open(".evomap_credentials.json", "w") as f:
                json.dump(creds, f, indent=2)
            return True
    except Exception as e:
        print(f"Activation Failed: {str(e)}")
        return False

node_id = "node_9b5c53c572f270fc"
secret = "21cb452cc91d1b9775b0ba68b9d987a2ed0bf42cf6fa1827790c221e3b36066c"
activate_node(node_id, secret)
