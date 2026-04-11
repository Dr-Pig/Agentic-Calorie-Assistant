import asyncio
import json
import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from app.usecases.text_meal import run_text_meal_canary
from app.usecases.text_meal_trace_eval import evaluate_trace_contract
from app.schemas import EstimateRequest
from app.providers.builderspace_adapter import BuilderSpaceAdapter

async def run_diagnostic():
    # Load cases
    cases_path = "tests/chain_conv_cases.json"
    with open(cases_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    results = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = ".logs/diagnostics/chain_conv"
    os.makedirs(log_dir, exist_ok=True)

    provider = BuilderSpaceAdapter()

    print(f"Starting Chain & Conv Store Quality Audit...")

    for case in cases:
        case_id = case["case_id"]
        text = case["text"]
        category = case["category"]
        
        print(f"Testing [{category}] {case_id}: '{text}'...")
        
        try:
            # Create request object
            req = EstimateRequest(text=text, allow_search=True)
            
            # Run the engine
            payload = await run_text_meal_canary(
                req, 
                provider=provider, 
                request_id=f"diag_{case_id}_{timestamp}"
            )
            
            # Handle quality_signals as dict or Pydantic
            qs = payload.quality_signals
            if hasattr(qs, "dict"):
                qs = qs.dict()
            elif hasattr(qs, "model_dump"):
                qs = qs.model_dump()
            
            # Evaluate using the upgraded contract
            eval_result = evaluate_trace_contract(
                payload.trace_contract,
                qs,
                best_answer_source=payload.best_answer_source,
                retry_triggered=payload.retry_triggered
            )
            
            # Record result
            res = {
                "case_id": case_id,
                "category": category,
                "text": text,
                "verdict": eval_result["win_loss_neutral"],
                "failed_layer": eval_result.get("failed_layer"),
                "why": eval_result.get("why"),
                "kcal": payload.estimated_kcal,
                "source": payload.best_answer_source,
                "db_hit": payload.trace_contract.get("db_hit_type")
            }
            results.append(res)
            
            # Save individual payload for deep dive
            with open(f"{log_dir}/payload_{case_id}_{timestamp}.json", "w", encoding="utf-8") as f:
                p_dict = payload.dict() if hasattr(payload, "dict") else payload.model_dump() if hasattr(payload, "model_dump") else payload
                json.dump(p_dict, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"  Error testing {case_id}: {str(e)}")
            results.append({
                "case_id": case_id,
                "category": category,
                "text": text,
                "verdict": "error",
                "why": str(e)
            })

    # Summary and Report
    report_path = f"{log_dir}/report_{timestamp}.md"
    wins = len([r for r in results if r["verdict"] == "win"])
    losses = len([r for r in results if r["verdict"] == "loss"])
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Chain & Conv Store Quality Audit Report ({timestamp})\n\n")
        f.write(f"## Summary\n")
        f.write(f"- Total: {len(results)}\n")
        f.write(f"- Win: {wins}\n")
        f.write(f"- Loss: {losses}\n\n")
        f.write(f"| Case ID | Category | Verdict | DB Hit | Kcal | Source | Why |\n")
        f.write(f"| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for r in results:
            f.write(f"| {r['case_id']} | {r['category']} | {r['verdict']} | {r.get('db_hit', '-')} | {r.get('kcal', 0)} | {r.get('source', '-')} | {r.get('why', '-')} |\n")

    print(f"\nAudit complete. Report saved to: {report_path}")

if __name__ == "__main__":
    asyncio.run(run_diagnostic())
