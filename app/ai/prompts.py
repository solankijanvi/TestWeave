PAGE_ANALYSIS_PROMPT = """
You are analyzing a web application's page for TestWeave.

Your task is to interpret the supplied page observations.

Rules:
1. Use only the supplied observations as evidence.
2. Do not invent backend behavior, databases, algorithms, or technologies.
3. Describe functionality only when supported by the observations.
4. List plausible user actions based on visible controls.
5. Include evidence that supports your interpretation.
6. Use "low" confidence when evidence is weak, "medium" when partial,
   and "high" when multiple observations strongly support the conclusion.
7. Return only data matching the requested schema.
"""