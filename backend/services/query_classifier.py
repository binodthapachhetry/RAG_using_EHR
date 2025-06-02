import vertexai
from vertexai.generative_models import GenerativeModel
from ..config import settings

# One-time Vertex AI init (safe to call multiple times)
vertexai.init(project=settings.VERTEX_AI_PROJECT_ID,
              location=settings.GCP_REGION)

_model = GenerativeModel(settings.LLM_MODEL_NAME)

# Returns "simple" or "complex"
def classify_query(question: str) -> str:
    prompt = f"""
You are a medical Q&A routing assistant.
Label the doctor’s question as:
- "simple": can be answered with ONE direct structured SQL lookup
- "complex": needs multi-step reasoning, synthesis, or free-text RAG
Respond ONLY with the single word simple or complex.

Question: \"\"\"{question}\"\"\" 
Category:"""
    try:
        resp = _model.generate_content(prompt)
        label = resp.text.strip().lower()
        return "simple" if label == "simple" else "complex"
    except Exception:
        return "complex"   # Fail-safe
