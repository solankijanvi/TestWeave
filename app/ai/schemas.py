from typing import Literal

from pydantic import BaseModel


class AIPageAnalysis(BaseModel):
    page_purpose: str
    functionality: str
    user_actions: list[str]
    evidence: list[str]
    confidence: Literal["low", "medium", "high"]
    
    
if __name__ == "__main__":
    from pydantic import ValidationError

    try:
        analysis = AIPageAnalysis(
            page_purpose="Prediction",
            functionality="Allows users to submit cattle information.",
            user_actions=["Enter age", "Select symptoms"],
            evidence=["Prediction form detected"],
            confidence="very_high"
        )

        print("Unexpected success:", analysis.model_dump())

    except ValidationError as error:
        print("Validation failed as expected:")
        print(error)