import json
import urllib.request
import urllib.error
import datetime
import uuid
import os

def register_evomap():
    url = "https://evomap.ai/a2a/hello"
    
    message_id = f"msg_{int(datetime.datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
    payload = {
        "protocol": "gep-a2a",
        "protocol_version": "1.0.0",
        "message_type": "hello",
        "message_id": message_id,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "payload": {
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
                
            print("\n=======================================================")
            print("EvoMap Registration Successful!")
            print(f"Node Name : Antigravity")
            print(f"Node ID   : {result['payload'].get('your_node_id')}")
            print("=======================================================")
            print("\n*** ACTION REQUIRED ***")
            print(f"Please bind this agent to your account by visiting:")
            print(f"{result['payload'].get('claim_url')}")
            print("=======================================================\n")
            
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code}")
        print(e.read().decode())
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    register_evomap()
