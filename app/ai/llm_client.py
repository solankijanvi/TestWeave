import os

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel


class LLMClient:

    def __init__(self, model: str = "gemini-flash-latest"):
        load_dotenv()

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")

        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt
        )

        return response.text
    
    def generate_structured(
        self,
        prompt: str,
        response_schema: type[BaseModel]
    ) -> BaseModel:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": response_schema,
            },
        )

        if not response.text:
            raise ValueError("Gemini returned an empty response.")

        return response_schema.model_validate_json(response.text)


if __name__ == "__main__":

    llm = LLMClient()

    result = llm.generate(
        "Explain what an API is in one sentence."
    )

    print(result)