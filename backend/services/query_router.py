from ..api.models import QueryType
import vertexai
from vertexai.generative_models import GenerativeModel

# System prompt for LLM-based routing
ROUTER_PROMPT = """
You are a medical Q&A routing assistant.
Label the doctor’s question as:
- "simple": can be answered with ONE direct structured SQL lookup
- "complex": needs multi-step reasoning, synthesis, or free-text RAG
Respond ONLY with the single word simple or complex.

Question: What allergies does patient 42 have?
Category: simple

Question: Provide a brief summary of patient 42’s current condition and medications.
Category: complex

Question: {question}
Category:
"""

def classify_query_llm(question: str) -> str:
    # Use Vertex AI Gemini or other LLM to classify the query
    # Assumes vertexai.init() has been called elsewhere, or call here if needed
    model = GenerativeModel("gemini-pro")  # Or use settings.LLM_MODEL_NAME if available
    prompt = ROUTER_PROMPT.format(question=question)
    response = model.generate_content(prompt)
    label = response.text.strip().lower()
    if "simple" in label:
        return "simple"
    elif "complex" in label:
        return "complex"
    else:
        # Fallback: treat as complex if ambiguous
        return "complex"

def route_query(query_text: str, patient_id: str) -> tuple[QueryType, str, str]:
    label = classify_query_llm(query_text)
    qtype = QueryType.SIMPLE if label == "simple" else QueryType.COMPLEX
    return qtype, patient_id, query_text
