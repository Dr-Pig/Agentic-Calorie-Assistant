import json
import urllib.request
import urllib.error
import datetime
import uuid

def recover_node(node_id):
    url = "https://evomap.ai/a2a/hello"
    message_id = f"msg_{int(datetime.datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
    
    payload = {
        "protocol": "gep-a2a",
        "protocol_version": "1.0.0",
        "message_type": "hello",
        "message_id": message_id,
        "sender_id": node_id,  # Specify the node we want to recover
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "payload": {
            "rotate_secret": True, # Request new secret for this node_id
            "capabilities": {"supported_types": ["Gene", "Capsule"]},
            "model": "deepseek-chat",
            "name": "Antigravity",
            "env_fingerprint": {"platform": "windows", "arch": "x64"}
        }
    }
    
    req = urllib.request.Request(
        url, 
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            cred_file = ".evomap_credentials.json"
            with open(cred_file, "w") as f:
                json.dump(result["payload"], f, indent=2)
            
            print(f"Node {node_id} Recovered Successfully!")
            print(f"New Secret stored in {cred_file}")
            print(f"Survival Status: {result['payload'].get('survival_status')}")
            return True
    except urllib.error.HTTPError as e:
        print(f"Recovery Failed: {e.code}")
        print(e.read().decode())
        return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

recover_node("node_9b5c53c572f270fc")
