import json

from app.ai.llm_client import LLMClient
from app.ai.prompts import PAGE_ANALYSIS_PROMPT
from app.ai.schemas import AIPageAnalysis


observations = {
    "url": "https://example.com/predict",
    "title": "Cattle Disease Prediction",
    "headings": ["Predict Cattle Disease"],
    "inputs": [
        {"type": "text", "name": "age", "id": "age"},
        {"type": "text", "name": "breed", "id": "breed"},
    ],
    "selects": [
        {"name": "symptom1", "options_count": 132}
    ],
    "forms": [
        {"action": "/predict", "method": "POST"}
    ],
}

prompt = (
    PAGE_ANALYSIS_PROMPT
    + "\n\nAnalyze these page observations:\n"
    + json.dumps(observations, indent=2)
)

llm = LLMClient()

analysis = llm.generate_structured(
    prompt=prompt,
    response_schema=AIPageAnalysis,
)

print("\nStructured AI analysis:")
print(analysis.model_dump_json(indent=2))
