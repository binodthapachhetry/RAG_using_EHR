from ..api.models import QueryType
import vertexai
from vertexai.generative_models import GenerativeModel

# System prompt for LLM-based routing
ROUTER_PROMPT = """
You are a medical Q&A routing assistant.

# HIGH-LEVEL SCHEMA OVERVIEW  ── bigquery-public-data.fhir_synthea ────────────
Patient                ─ Demographics for each patient (id, name, gender, DOB).
AllergyIntolerance     ─ Recorded drug/food/environment allergies per patient.
Condition              ─ Diagnoses and clinical conditions with onset/status.
MedicationRequest      ─ Prescriptions ordered for the patient (active, stopped).
MedicationDispense     ─ Fills actually dispensed by a pharmacy.
MedicationAdministration─ In-hospital administrations of medications.
Observation            ─ Labs, vitals, and other observations (value, unit, time).
DiagnosticReport       ─ Summaries of related observations (e.g., lab panels).
Procedure              ─ Surgical or clinical procedures performed.
Encounter              ─ Individual visits, admissions, encounters (start/end).
Immunization           ─ Vaccines given to the patient.
CarePlan               ─ Planned treatments, goals, and activities.
DocumentReference      ─ Unstructured documents (notes, imaging reports, etc.).
Practitioner           ─ Clinician directory (id, name, specialty).
PractitionerRole       ─ Links practitioners to organizations & specialties.
Organization           ─ Healthcare organizations/facilities.
Location               ─ Physical locations (wards, clinics).
Provenance             ─ Metadata about who/what generated other resources.
Device                 ─ Medical devices associated with the patient.

# QUICK GUIDELINES FOR ROUTING
• “One-table / one-where” look-ups (simple):
    Patient, AllergyIntolerance, Condition, MedicationRequest,
    Observation (single measurement list or latest value),
    Encounter (list or count of visits), Procedure.

• Likely multi-table joins (complex):
    - “Summaries”, “trends”, or “correlations” across labs & meds.
    - Time-oriented analytics (e.g., change in HbA1c after medication).
    - Questions combining different resource types (e.g., “conditions
      diagnosed during the last inpatient encounter” → Encounter + Condition).
    - Anything needing Practitioner / Organization context.

Use this schema snippet in the router-classifier prompt (few-shot or system message) so the LLM can reason about table granularity without full DDLs.

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
