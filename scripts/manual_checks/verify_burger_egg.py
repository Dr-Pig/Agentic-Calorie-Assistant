import asyncio
import httpx

BASE = "http://127.0.0.1:8011"
USER_ID = "tester_antigravity"

async def main():
    async with httpx.AsyncClient(timeout=60) as client:
        # 0. Reset context
        print("Resetting context...")
        await client.post(f"{BASE}/user/{USER_ID}/context/reset")

        # 1. Turn 1: Burger
        print("\n--- Turn 1: 漢堡 ---")
        r1 = await client.post(f"{BASE}/estimate", json={
            "text": "中午吃了一個牛肉漢堡",
            "user_id": USER_ID,
            "allow_search": False,
        })
        d1 = r1.json()
        print(f"Reply: {d1.get('coach_message', '')[:100]}...")
        
        # 2. Turn 2: Add an egg
        print("\n--- Turn 2: 對了還有加了一個蛋 ---")
        r2 = await client.post(f"{BASE}/estimate", json={
            "text": "對了還有加了一個蛋",
            "user_id": USER_ID,
            "allow_search": False,
        })
        d2 = r2.json()
        print(f"Reply: {d2.get('coach_message', '')[:100]}...")
        
        payload = d2.get("payload", {})
        components = [c.get("name") for c in payload.get("component_estimates", [])]
        print(f"\nFinal Components: {components}")
        
        if "蛋" in str(components) and "漢堡" in str(components) or "牛肉" in str(components):
            print("\n✅ SUCCESS: Merge confirmed.")
        else:
            print("\n❌ FAILURE: Context lost.")

if __name__ == "__main__":
    asyncio.run(main())
