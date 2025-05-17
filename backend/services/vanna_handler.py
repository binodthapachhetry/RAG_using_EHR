import vanna
from vanna.google import VannaGoogleVertexAI
from vanna.google.bigquery import VannaBigQuery
from ..config import settings

# Vanna needs to be "trained" on your schema.
# This is a simplified representation. In a real scenario, you would provide
# more comprehensive DDLs, documentation strings, and potentially sample SQL queries.
# IMPORTANT: Use PascalCase for table names as in fhir_synthea.
TRAINING_DDLS = [
    """
    CREATE TABLE Patient (
        id STRING,
        name JSON, -- Actually an ARRAY<STRUCT<text STRING, ...>>
        gender STRING,
        birthDate DATE
        -- ... other relevant columns
        -- For Vanna: Patient ID is typically 'id'. If queries use 'patient_id', ensure Vanna knows 'id' is the patient identifier.
        -- You can add documentation: vn.add_documentation(table="Patient", doc="Table for patient demographic data. Use 'id' to filter by patient.")
    );
    """,
    """
    CREATE TABLE MedicationRequest (
        id STRING,
        status STRING,
        medicationCodeableConcept JSON, -- Actually a STRUCT<text STRING, coding ARRAY<STRUCT<...>>>
        subject JSON -- Actually a STRUCT<patientId STRING, type STRING, ...>
        -- ... other relevant columns
        -- For Vanna: vn.add_documentation(table="MedicationRequest", doc="Table for medication orders. Filter by patient using subject.patientId = :patient_id.")
    );
    """,
    # Add DDLs for Condition, Observation, AllergyIntolerance etc.
    # Example for making patient_id parameter work:
    # vn.add_documentation(table="Condition", column="subject.patientId", doc="Filter this column using the 'patient_id' parameter provided in the question context.")
]

class VannaHandler:
    def __init__(self):
        # Configure Vanna to use Google Vertex AI (Gemini) for LLM tasks
        # VannaGoogleVertexAI handles both SQL generation and Natural Language generation
        self.vn = VannaGoogleVertexAI(project=settings.VERTEX_AI_PROJECT_ID, region=settings.GCP_REGION, model=settings.LLM_MODEL_NAME)
        
        # Configure Vanna to connect to BigQuery
        # It uses Application Default Credentials (ADC)
        self.vn.connect_to_bigquery(project_id=settings.VERTEX_AI_PROJECT_ID, dataset_id=settings.FHIR_DATASET_ID)
        # Note: Vanna's BigQuery connector might run jobs in settings.VERTEX_AI_PROJECT_ID
        # and query data from settings.BIGQUERY_PROJECT_ID.FHIR_DATASET_ID if its internal
        # logic correctly handles fully qualified table names from training.
        # If not, you might need to ensure Vanna is trained with fully qualified names
        # or that the default project for the BigQuery client it instantiates is VERTEX_AI_PROJECT_ID.

        # Basic training (idempotent, Vanna typically stores training data)
        # In a production setup, you might manage training data more robustly.
        existing_training_data = self.vn.get_training_data()
        if not existing_training_data or len(existing_training_data) < len(TRAINING_DDLS):
             for ddl in TRAINING_DDLS:
                 self.vn.train(ddl=ddl)
             # Add specific documentation for patient_id if needed for your Vanna version/setup
             self.vn.train(documentation="When a question refers to 'the patient' or provides a 'patient_id', ensure SQL queries filter data for that specific patient. For example, in the MedicationRequest table, use subject.patientId = :patient_id. In the Patient table, use id = :patient_id.")

    async def get_response(self, natural_language_query: str, patient_id: str) -> tuple[str | None, str | None]:
        # Use patient_id as a parameter that Vanna can potentially use in SQL
        # The vn.ask method attempts to generate SQL, run it, and generate a natural language response.
        # It can also return charts, but we're interested in the text response and SQL.
        try:
            # Pass patient_id as a context variable that Vanna might use if trained for it
            # The key 'patient_id' here must match how you've trained Vanna to expect it (e.g., in documentation strings)
            nl_answer = self.vn.ask(question=natural_language_query, patient_id=patient_id, print_results=False)
            # vn.ask usually returns a string (NL answer) or a Vanna.AskResponse object depending on version/config
            # For simplicity, assuming it returns the NL answer directly or we extract it.
            # If nl_answer is an object, you might need nl_answer.text or similar.
            # Let's assume nl_answer is the string response for now.
            # Getting the last generated SQL query
            sql_query = vanna.get_last_sql_query() # Utility to get the last SQL query Vanna generated
            return str(nl_answer) if nl_answer else "I could not generate an answer.", sql_query
        except Exception as e:
            print(f"Error during Vanna interaction: {e}")
            return f"An error occurred while processing your request with Vanna: {str(e)}", None

def get_vanna_handler():
    # This could involve more complex setup or singleton pattern in a real app
    return VannaHandler()
