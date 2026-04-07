from app.application.context_assembly import knowledge_context as _knowledge_context
test_docs = [
    {
        "title": "Egg",
        "kcal_band": "75 kcal",
        "common_components": ["egg content"],
        "portion_notes": "1 medium",
        "notes": "",
        "snippet": "",
        "source_url": "",
        "evidence_role": "exact_truth",
        "macro_completeness": "complete",
        "protein_g": 6,
        "carb_g": 0,
        "fat_g": 5,
        "sodium_mg": 71,
    }
]
print(_knowledge_context(test_docs))
