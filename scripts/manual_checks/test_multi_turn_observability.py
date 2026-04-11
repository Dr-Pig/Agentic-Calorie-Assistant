"""Multi-turn persistence and observability test."""
import asyncio
import httpx

BASE = "http://127.0.0.1:8011"
USER_ID = "obs_test_user"

async def main():
    async with httpx.AsyncClient(timeout=60) as client:
        # 0. Reset
        print("--- Resetting Context ---")
        await client.post(f"{BASE}/user/{USER_ID}/context/reset")

        # 1. Turn 1: New Intake
        print("\n--- Turn 1: 我中午吃了一碗滷肉飯 ---")
        r1 = await client.post(f"{BASE}/estimate", json={
            "text": "我中午吃了一碗滷肉飯",
            "user_id": USER_ID,
            "allow_search": False,
        })
        d1 = r1.json()
        p1 = d1.get("payload", {})
        mt1 = p1.get("multi_turn_context", {})
        tokens1 = p1.get("trace_contract", {}).get("token_usage", {})
        
        print(f"Intent: {mt1.get('turn_intent')}")
        print(f"Kcal: {p1.get('estimated_kcal')}")
        print(f"Tokens: {tokens1.get('total_tokens')} (Calls: {tokens1.get('llm_call_count')})")
        print(f"Is Multi-turn: {mt1.get('is_multi_turn')}")

        # 2. Turn 2: Modification
        print("\n--- Turn 2: 對了，那是大碗的 ---")
        r2 = await client.post(f"{BASE}/estimate", json={
            "text": "對了，那是大碗的",
            "user_id": USER_ID,
            "allow_search": False,
        })
        d2 = r2.json()
        p2 = d2.get("payload", {})
        mt2 = p2.get("multi_turn_context", {})
        tokens2 = p2.get("trace_contract", {}).get("token_usage", {})
        eval2 = p2.get("north_star_evaluation", {})

        print(f"Intent: {mt2.get('turn_intent')}")
        print(f"Kcal: {p2.get('estimated_kcal')}")
        print(f"Tokens: {tokens2.get('total_tokens')} (Calls: {tokens2.get('llm_call_count')})")
        print(f"Is Multi-turn: {mt2.get('is_multi_turn')}")
        print(f"Rewritten Query: {mt2.get('effective_retrieval_query')}")
        print(f"North Star Verdict: {eval2.get('win_loss_neutral')}")
        print(f"Multi-turn Intent Correct: {eval2.get('observable_metrics', {}).get('multi_turn_intent_correct')}")
        print(f"Retrieval Contextual: {eval2.get('observable_metrics', {}).get('retrieval_query_contextual')}")

        # 3. Check Logs API (Filter test)
        print("\n--- Checking Logs API (Default: No Superseded) ---")
        l_def = (await client.get(f"{BASE}/user/{USER_ID}/logs")).json()
        print(f"Count: {len(l_def['logs'])}")
        for l in l_def['logs']:
            print(f"  - {l['meal_title']} ({l['status']})")

        print("\n--- Checking Logs API (Include Superseded) ---")
        l_all = (await client.get(f"{BASE}/user/{USER_ID}/logs?include_superseded=true")).json()
        print(f"Count: {len(l_all['logs'])}")
        for l in l_all['logs']:
            print(f"  - {l['meal_title']} ({l['status']})")

        print("\n=== Test Complete ===")

if __name__ == "__main__":
    asyncio.run(main())
