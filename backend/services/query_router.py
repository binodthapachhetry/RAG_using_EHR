from ..api.models import QueryType
from .query_classifier import classify_query

def route_query(query_text: str, patient_id: str) -> tuple[QueryType, str, str]:
    label = classify_query(query_text)
    qtype = QueryType.SIMPLE if label == "simple" else QueryType.COMPLEX
    return qtype, patient_id, query_text
