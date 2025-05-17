import vanna
# Corrected imports for Vanna Vertex AI and BigQuery connectors
from vanna.google import GoogleGeminiChat # Changed from vanna.vertex
from vanna.google import BigQuery_VectorStore # Assuming this is available after pip install "vanna[google]"

from ..config import settings

# Fully qualified table names for training
PATIENT_TABLE_FQ = f"`{settings.BIGQUERY_PROJECT_ID}.{settings.FHIR_DATASET_ID}.Patient`"
MED_REQ_TABLE_FQ = f"`{settings.BIGQUERY_PROJECT_ID}.{settings.FHIR_DATASET_ID}.MedicationRequest`"
CONDITION_TABLE_FQ = f"`{settings.BIGQUERY_PROJECT_ID}.{settings.FHIR_DATASET_ID}.Condition`"
OBSERVATION_TABLE_FQ = f"`{settings.BIGQUERY_PROJECT_ID}.{settings.FHIR_DATASET_ID}.Observation`"
ALLERGY_TABLE_FQ = f"`{settings.BIGQUERY_PROJECT_ID}.{settings.FHIR_DATASET_ID}.AllergyIntolerance`"

# Vanna needs to be "trained" on your schema.
# This is a simplified representation. In a real scenario, you would provide
# more comprehensive DDLs, documentation strings, and potentially sample SQL queries.
# IMPORTANT: Use PascalCase for table names as in fhir_synthea.
# Use fully qualified table names in DDLs for clarity with Vanna.
TRAINING_DDLS = [
    f"""
    CREATE TABLE {PATIENT_TABLE_FQ} (
        id STRING,
        name JSON, -- To get first text name: (SELECT n.text FROM UNNEST(name) AS n LIMIT 1)
        gender STRING,
        birthDate DATE,
        address JSON -- To get first city: (SELECT a.city FROM UNNEST(address) AS a LIMIT 1)
    );
    """,
    f"""
    CREATE TABLE {MED_REQ_TABLE_FQ} (
        id STRING,
        status STRING,
        medicationCodeableConcept JSON, -- To get medication name: medicationCodeableConcept.text
        subject JSON, -- To get patientId: subject.patientId
        authoredOn TIMESTAMP
    );
    """,
    f"""
    CREATE TABLE {CONDITION_TABLE_FQ} (
        id STRING,
        clinicalStatus JSON, -- Example: clinicalStatus.coding[OFFSET(0)].code
        verificationStatus JSON, -- Example: verificationStatus.coding[OFFSET(0)].code
        code JSON, -- To get condition name: code.text
        subject JSON -- To get patientId: subject.patientId
    );
    """,
    f"""
    CREATE TABLE {OBSERVATION_TABLE_FQ} (
        id STRING,
        status STRING,
        code JSON, -- To get observation name: code.text or code.coding[OFFSET(0)].display
        subject JSON, -- To get patientId: subject.patientId
        effectiveDateTime TIMESTAMP,
        valueQuantity JSON, -- For numeric values: valueQuantity.value, valueQuantity.unit
        valueString STRING,
        valueCodeableConcept JSON -- For coded values: valueCodeableConcept.text
    );
    """,
    f"""
    CREATE TABLE {ALLERGY_TABLE_FQ} (
        id STRING,
        clinicalStatus JSON, -- Example: clinicalStatus.coding[OFFSET(0)].code
        verificationStatus JSON,
        code JSON, -- To get allergy name: code.text
        patient JSON -- To get patientId: patient.patientId
    );
    """,
]
# Create a new class that inherits from the specific LLM and Database connectors
# These specific connectors (GoogleGeminiChat, GoogleBigQuery) already inherit from VannaBase.
class VannaBigQueryGemini(GoogleGeminiChat, BigQuery_VectorStore):
    def __init__(self, gemini_config: dict, bigquery_config: dict):
        # Initialize GoogleGeminiChat for LLM (Vertex AI Gemini)
        # It expects project, location (region), and model.
        GoogleGeminiChat.__init__(self, config=gemini_config)
        
        # Initialize GoogleBigQuery for database connection
        # It expects project_id where jobs will run.
        BigQuery_VectorStore.__init__(self, config=bigquery_config)

class VannaHandler: # VannaHandler does not need to inherit from Vanna classes
    def __init__(self):
        gemini_llm_config = {
            'project_id': settings.VERTEX_AI_PROJECT_ID,
            'location': settings.GCP_REGION, # GCP_REGION from your config.py
            'model_name': settings.LLM_MODEL_NAME,
            'google_credentials': settings.JSON_FILE_PATH,
            'api_key': settings.LLM_API_KEY
        }
        # The project_id for BigQuery is where the BQ jobs will run.
        # Vanna uses fully qualified table names from training data for queries.
        bigquery_db_config = {'project_id': settings.VERTEX_AI_PROJECT_ID}
        self.vn = VannaBigQueryGemini(gemini_config=gemini_llm_config, bigquery_config=bigquery_db_config)
        
        # Basic training (idempotent, Vanna typically stores training data)
        # In a production setup, you might manage training data more robustly.
        existing_training_data = self.vn.get_training_data()
        if existing_training_data.empty or len(existing_training_data) < len(TRAINING_DDLS): # Simple check
            print("Training Vanna with DDLs, documentation, and SQL samples...")
            for ddl in TRAINING_DDLS:
                self.vn.train(ddl=ddl)
            
            # General Documentation
            self.vn.train(documentation="When a question refers to 'the patient' or includes a 'patient_id', filter data for that specific patient. Use the patient_id in a WHERE clause.")

            # Table/Column Specific Documentation
            self.vn.train(documentation=f"Patient data is in {PATIENT_TABLE_FQ}. Filter by patient ID using 'id = :patient_id'. Get name from 'name' JSON field, e.g., (SELECT n.text FROM UNNEST(name) AS n LIMIT 1).")
            self.vn.train(documentation=f"Medication orders are in {MED_REQ_TABLE_FQ}. Filter by patient using 'subject.patientId = :patient_id'. Get medication name from 'medicationCodeableConcept.text'. Active medications have 'status = \"active\"'.")
            self.vn.train(documentation=f"Patient conditions are in {CONDITION_TABLE_FQ}. Filter by patient using 'subject.patientId = :patient_id'. Get condition name from 'code.text'.")
            self.vn.train(documentation=f"Patient observations (labs, vitals) are in {OBSERVATION_TABLE_FQ}. Filter by patient using 'subject.patientId = :patient_id'. Get observation name from 'code.text'. Numeric values are in 'valueQuantity.value' with units in 'valueQuantity.unit'.")
            self.vn.train(documentation=f"Patient allergies are in {ALLERGY_TABLE_FQ}. Filter by patient using 'patient.patientId = :patient_id'. Get allergy name from 'code.text'.")

            # SQL Samples (using fully qualified names)
            self.vn.train(
                question="What are the active medications for patient 'patient123'?",
                sql=f"SELECT T1.medicationCodeableConcept.text FROM {MED_REQ_TABLE_FQ} AS T1 WHERE T1.subject.patientId = 'patient123' AND T1.status = 'active'"
            )
            self.vn.train(
                question="List all conditions for patient 'patient456'.",
                sql=f"SELECT T1.code.text FROM {CONDITION_TABLE_FQ} AS T1 WHERE T1.subject.patientId = 'patient456'"
            )
            self.vn.train(
                question="What is the gender of patient 'patient789'?",
                sql=f"SELECT T1.gender FROM {PATIENT_TABLE_FQ} AS T1 WHERE T1.id = 'patient789'"
            )
            self.vn.train(
                question="Show me the name of patient 'patient001'.",
                sql=f"SELECT (SELECT n.text FROM UNNEST(T1.name) AS n LIMIT 1) AS patient_name FROM {PATIENT_TABLE_FQ} AS T1 WHERE T1.id = 'patient001'"
            )
            self.vn.train(
                question="What was the last recorded systolic blood pressure for patient 'patient002'?",
                sql=f"SELECT T1.valueQuantity.value FROM {OBSERVATION_TABLE_FQ} AS T1 WHERE T1.subject.patientId = 'patient002' AND T1.code.text = 'Systolic blood pressure' ORDER BY T1.effectiveDateTime DESC LIMIT 1"
            )
            print("Vanna training submitted.")

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
            # Getting the last generated SQL query
            sql_query = vanna.get_last_sql_query() # Utility to get the last SQL query Vanna generated
            return str(nl_answer) if nl_answer else "I could not generate an answer.", sql_query
        except Exception as e:
            print(f"Error during Vanna interaction: {e}")
            return f"An error occurred while processing your request with Vanna: {str(e)}", None

def get_vanna_handler():
    # This could involve more complex setup or singleton pattern in a real app
    return VannaHandler()
