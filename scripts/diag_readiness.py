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
    cases_path = "tests/readiness_audit_cases.json"
    with open(cases_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    results = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = ".logs/diagnostics/readiness"
    os.makedirs(log_dir, exist_ok=True)

    provider = BuilderSpaceAdapter()

    print("Starting Readiness Audit (Component Deconstruction + Scaling)...")

    for case in cases:
        case_id = case["case_id"]
        text = case["text"]
        category = case["category"]

        print(f"Testing [{category}] {case_id}: '{text}'...")

        try:
            req = EstimateRequest(text=text, allow_search=True)
            payload = await run_text_meal_canary(
                req,
                provider=provider,
                request_id=f"diag_{case_id}_{timestamp}"
            )

            qs = payload.quality_signals
            if hasattr(qs, "model_dump"):
                qs = qs.model_dump()
            elif hasattr(qs, "dict"):
                qs = qs.dict()

            eval_result = evaluate_trace_contract(
                payload.trace_contract,
                qs,
                best_answer_source=payload.best_answer_source,
                retry_triggered=payload.retry_triggered
            )

            # Extract component-level detail for analysis
            comp_estimates = [
                {"name": c.name, "kcal": c.estimated_kcal, "hint": c.quantity_hint, "basis": c.estimate_basis}
                for c in payload.component_estimates
            ]

            res = {
                "case_id": case_id,
                "category": category,
                "text": text,
                "verdict": eval_result["win_loss_neutral"],
                "kcal": payload.estimated_kcal,
                "protein_g": payload.protein_g,
                "carb_g": payload.carb_g,
                "fat_g": payload.fat_g,
                "source": payload.best_answer_source,
                "db_hit": payload.trace_contract.get("db_hit_type"),
                "components_count": len(payload.components),
                "component_estimates_count": len(comp_estimates),
                "component_estimates": comp_estimates,
                "why": eval_result.get("why"),
            }
            results.append(res)

            # Save full payload
            p_dict = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
            with open(f"{log_dir}/payload_{case_id}_{timestamp}.json", "w", encoding="utf-8") as f:
                json.dump(p_dict, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"  Error testing {case_id}: {str(e)}")
            results.append({
                "case_id": case_id, "category": category, "text": text,
                "verdict": "error", "why": str(e)
            })

    # Report
    report_path = f"{log_dir}/report_{timestamp}.md"
    wins = len([r for r in results if r["verdict"] == "win"])
    losses = len([r for r in results if r["verdict"] == "loss"])

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Readiness Audit Report ({timestamp})\n\n")
        f.write(f"## Summary\n")
        f.write(f"- Total: {len(results)}\n")
        f.write(f"- Win: {wins}\n")
        f.write(f"- Loss: {losses}\n\n")

        f.write(f"## Results\n\n")
        f.write(f"| Case | Category | Verdict | Kcal | P/C/F | Source | DB Hit | Components | CompEst | Why |\n")
        f.write(f"| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for r in results:
            pcf = f"{r.get('protein_g', 0)}/{r.get('carb_g', 0)}/{r.get('fat_g', 0)}"
            f.write(f"| {r['case_id']} | {r['category']} | {r['verdict']} | {r.get('kcal', 0)} | {pcf} | {r.get('source', '-')} | {r.get('db_hit', '-')} | {r.get('components_count', 0)} | {r.get('component_estimates_count', 0)} | {r.get('why', '-')} |\n")

        f.write(f"\n## Component-Level Detail\n\n")
        for r in results:
            if r.get("component_estimates"):
                f.write(f"### {r['case_id']}: {r['text']}\n\n")
                f.write(f"| Component | Kcal | Hint | Basis |\n")
                f.write(f"| :--- | :--- | :--- | :--- |\n")
                for c in r["component_estimates"]:
                    f.write(f"| {c['name']} | {c['kcal']} | {c.get('hint', '-')} | {c['basis']} |\n")
                f.write(f"\n")

    print(f"\nReadiness Audit complete. Report saved to: {report_path}")

if __name__ == "__main__":
    asyncio.run(run_diagnostic())
