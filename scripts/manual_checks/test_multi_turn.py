"""Multi-turn persistence test for the unified MealLog memory system."""
import asyncio
import httpx

BASE = "http://127.0.0.1:8011"
USER_ID = "test_user_multiturn"


async def main():
    async with httpx.AsyncClient(timeout=60) as client:
        # Reset context
        await client.post(f"{BASE}/user/{USER_ID}/context/reset")

        # ── Turn 1: New intake ──
        print("--- Turn 1: New intake ---")
        r1 = await client.post(f"{BASE}/estimate", json={
            "text": "我中午吃了一碗滷肉飯",
            "user_id": USER_ID,
            "allow_search": False,
        })
        d1 = r1.json()
        print(f"Status: {r1.status_code}")
        print(f"Reply: {d1.get('coach_message', '')[:200]}")
        p1 = d1.get("payload", {})
        print(f"Action: {p1.get('action_taken')}")
        print(f"Kcal: {p1.get('estimated_kcal')}")

        # Check logs
        logs1 = (await client.get(f"{BASE}/user/{USER_ID}/logs")).json()
        print(f"\nLogs after Turn 1: {len(logs1['logs'])} record(s)")
        if logs1["logs"]:
            print(f"  Latest: {logs1['logs'][0]['meal_title']} - {logs1['logs'][0]['kcal']} kcal")

        print()

        # ── Turn 2: Refinement ──
        print("--- Turn 2: Refinement (大碗的) ---")
        r2 = await client.post(f"{BASE}/estimate", json={
            "text": "對了，那是大碗的",
            "user_id": USER_ID,
            "allow_search": False,
        })
        d2 = r2.json()
        print(f"Status: {r2.status_code}")
        print(f"Reply: {d2.get('coach_message', '')[:200]}")
        p2 = d2.get("payload", {})
        print(f"Action: {p2.get('action_taken')}")
        print(f"Kcal: {p2.get('estimated_kcal')}")

        # Check logs - should see superseded + new completed
        logs2 = (await client.get(f"{BASE}/user/{USER_ID}/logs")).json()
        print(f"\nLogs after Turn 2: {len(logs2['logs'])} record(s)")
        for log in logs2["logs"]:
            status = "(active)" if log.get("id") else ""
            print(f"  [{log.get('id')}] {log['meal_title']} - {log['kcal']} kcal")

        print()

        # ── Turn 3: New intake (different meal) ──
        print("--- Turn 3: New intake (different meal) ---")
        r3 = await client.post(f"{BASE}/estimate", json={
            "text": "晚上吃了義大利肉醬麵",
            "user_id": USER_ID,
            "allow_search": False,
        })
        d3 = r3.json()
        print(f"Status: {r3.status_code}")
        print(f"Reply: {d3.get('coach_message', '')[:200]}")
        p3 = d3.get("payload", {})
        print(f"Action: {p3.get('action_taken')}")
        print(f"Kcal: {p3.get('estimated_kcal')}")

        logs3 = (await client.get(f"{BASE}/user/{USER_ID}/logs")).json()
        print(f"\nLogs after Turn 3: {len(logs3['logs'])} record(s)")
        for log in logs3["logs"]:
            print(f"  [{log.get('id')}] {log['meal_title']} - {log['kcal']} kcal")

        print("\n=== Test Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
