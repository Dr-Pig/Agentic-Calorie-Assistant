# -*- coding: utf-8 -*-
import asyncio
import json
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from app.usecases.text_meal import run_text_meal_canary
from app.schemas import EstimateRequest, EstimatePayload
from app.providers.builderspace_adapter import BuilderSpaceAdapter

async def run_diagnostic():
    print("Starting Text Meal Layered Diagnostic Suite...")
    
    # Setup paths
    repo_root = Path(__file__).resolve().parent
    cases_path = repo_root / "tests" / "diagnostic_cases.json"
    results_dir = repo_root / ".logs" / "diagnostics"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    if not cases_path.exists():
        print(f"Cases file not found at {cases_path}")
        return


    with open(cases_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    cases = config.get("test_cases", [])
    provider = BuilderSpaceAdapter()
    
    report_items = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for case in cases:
        case_id = case["id"]
        text = case["text"]
        category = case["category"]
        print(f"Testing [{category}] {case_id}: '{text}'...")
        
        req = EstimateRequest(text=text, allow_search=True)
        try:
            payload: EstimatePayload = await run_text_meal_canary(
                req, provider=provider, request_id=f"diag_{case_id}_{timestamp}"
            )
            
            # Save full payload for deep investigation
            payload_path = results_dir / f"payload_{case_id}_{timestamp}.json"
            payload_path.write_text(payload.model_dump_json(indent=2), encoding="utf-8")
            
            # Extract evaluation from payload
            eval_result = payload.north_star_evaluation
            verdict = eval_result.get("win_loss_neutral", "unknown")
            failed_layer = eval_result.get("failed_layer")
            why = eval_result.get("why", "N/A")
            
            report_items.append({
                "case_id": case_id,
                "text": text,
                "category": category,
                "verdict": verdict,
                "failed_layer": failed_layer,
                "why": why,
                "best_answer_source": payload.best_answer_source,
                "estimated_kcal": payload.estimated_kcal,
                "retrieval_triggered": payload.retrieval_triggered,
                "retrieved_count": len(payload.retrieved_knowledge),
                "rescue_triggered": payload.quality_signals.get("rescue_applied") or False
            })
            
        except Exception as e:
            print(f"Error in case {case_id}: {str(e)}")
            report_items.append({
                "case_id": case_id,
                "text": text,
                "category": category,
                "verdict": "error",
                "error": str(e)
            })

    # Generate Markdown Report
    report_path = results_dir / f"diagnostic_report_{timestamp}.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Text Meal Canary Layered Diagnostic Report ({timestamp})\n\n")
        f.write("## Execution Summary\n")
        wins = len([i for i in report_items if i.get("verdict") == "win"])
        losses = len([i for i in report_items if i.get("verdict") == "loss"])
        neutrals = len([i for i in report_items if i.get("verdict") == "neutral"])
        errors = len([i for i in report_items if i.get("verdict") == "error"])
        
        f.write(f"- **Total Cases**: {len(report_items)}\n")
        f.write(f"- **Win**: {wins}\n")
        f.write(f"- **Loss**: {losses}\n")
        f.write(f"- **Neutral/Error**: {neutrals + errors}\n\n")
        
        f.write("## Detailed Results\n\n")
        f.write("| Case ID | Category | Verdict | Failed Layer | Why | Source | Kcal |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for item in report_items:
            verdict_text = "[Win]" if item["verdict"] == "win" else "[Loss]" if item["verdict"] == "loss" else "[Other]"
            f.write(f"| {item['case_id']} | {item['category']} | {verdict_text} {item['verdict']} | {item.get('failed_layer') or '-'} | {item.get('why')} | {item.get('best_answer_source') or '-'} | {item.get('estimated_kcal') or 0} |\n")
        
        f.write("\n\n## Failure Hotspots\n")
        fail_stats = {}
        for item in report_items:
            if item.get("verdict") == "loss" and item.get("failed_layer"):
                layer = item["failed_layer"]
                fail_stats[layer] = fail_stats.get(layer, 0) + 1
        
        if fail_stats:
            for layer, count in fail_stats.items():
                f.write(f"- **{layer}**: {count} failures\n")
        else:
            f.write("- No layer failure detected in this run.\n")

    print(f"\nDiagnostic complete. Report saved to: {report_path}")


if __name__ == "__main__":
    asyncio.run(run_diagnostic())
