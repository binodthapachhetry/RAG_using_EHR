import vanna
# Corrected imports for Vanna Vertex AI and BigQuery connectors
from vanna.google import GoogleGeminiChat # Changed from vanna.vertex
from vanna.google import BigQuery_VectorStore
from ..utils.schema_loader import get_fhir_synthea_schema

from ..config import settings
from google.oauth2 import service_account

# Fully qualified table names for training
PATIENT_TABLE_FQ = f"`{settings.BIGQUERY_PROJECT_ID}.{settings.FHIR_DATASET_ID}.Patient`"
MED_REQ_TABLE_FQ = f"`{settings.BIGQUERY_PROJECT_ID}.{settings.FHIR_DATASET_ID}.MedicationRequest`" # Corrected Casing
CONDITION_TABLE_FQ = f"`{settings.BIGQUERY_PROJECT_ID}.{settings.FHIR_DATASET_ID}.Condition`"
OBSERVATION_TABLE_FQ = f"`{settings.BIGQUERY_PROJECT_ID}.{settings.FHIR_DATASET_ID}.Observation`"
ALLERGY_TABLE_FQ = f"`{settings.BIGQUERY_PROJECT_ID}.{settings.FHIR_DATASET_ID}.AllergyIntolerance`"
ENCOUNTER_TABLE_FQ = f"`{settings.BIGQUERY_PROJECT_ID}.{settings.FHIR_DATASET_ID}.Encounter`"
PROCEDURE_TABLE_FQ = f"`{settings.BIGQUERY_PROJECT_ID}.{settings.FHIR_DATASET_ID}.Procedure`"

# Static TRAINING_DDLS removed – replaced by runtime-extracted DDLs.
# Create a new class that inherits from the specific LLM and Database connectors
# These specific connectors (GoogleGeminiChat, GoogleBigQuery) already inherit from VannaBase.
class VannaBigQueryGemini(GoogleGeminiChat, BigQuery_VectorStore):
    def __init__(self, gemini_config: dict, bigquery_config: dict) :
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
        bigquery_db_config = {
            'project_id': settings.VERTEX_AI_PROJECT_ID,
            'bigquery_dataset_name': settings.VANNA_STORAGE_DATASET
        }
        
        self.vn = VannaBigQueryGemini(gemini_config=gemini_llm_config, bigquery_config=bigquery_db_config)

        credentials = service_account.Credentials.from_service_account_file(
            settings.JSON_FILE_PATH,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )

        self.vn.connect_to_bigquery(
            project_id= settings.VERTEX_AI_PROJECT_ID,
            dataset_id= settings.FHIR_DATASET_ID,
            credentials=credentials
            )
        
        # Basic training (idempotent, Vanna typically stores training data)
        # In a production setup, you might manage training data more robustly.
        existing_training_data = self.vn.get_training_data()
        dynamic_ddls = list(
            get_fhir_synthea_schema(
                settings.BIGQUERY_PROJECT_ID,
                settings.FHIR_DATASET_ID
            ).values()
        )
        if existing_training_data.empty or len(existing_training_data) < len(dynamic_ddls):
            print("Training Vanna with full dynamically extracted DDLs...")
            for ddl in dynamic_ddls:
                self.vn.train(ddl=ddl)

    async def get_response(self, natural_language_query: str, patient_id: str) -> tuple[str, str | None]: # Return type changed to tuple[str, str | None]
        # Use patient_id as a parameter that Vanna can potentially use in SQL
        # The vn.ask method attempts to generate SQL, run it, and generate a natural language response.
        # It can also return charts, but we're interested in the text response and SQL.
        try:
            # Include patient_id in the question string for Vanna to use.
            # Vanna's training should be set up to recognize and use this patient_id.
            question_with_context = f"For patient ID '{patient_id}': {natural_language_query}"
            
            # Validate that the question is about the specified patient
            if "patient" in natural_language_query.lower() and str(patient_id) not in natural_language_query:
                # Add explicit patient context if not already present
                question_with_context = f"For patient ID '{patient_id}' only: {natural_language_query}"
            
            # The vn.ask method in recent Vanna versions (especially with GoogleGeminiChat)
            # often returns the SQL query as the first element of a tuple if successful,
            # and the natural language answer or DataFrame as other elements.
            response_content = self.vn.ask(question=question_with_context, print_results=False)
            
            final_nl_answer = "Could not retrieve an answer from Vanna."
            sql_query = None

            if isinstance(response_content, str):
                final_nl_answer = response_content
            elif isinstance(response_content, tuple) and len(response_content) > 0:
                # Vanna often returns (natural_language_answer, sql_query, dataframe, chart_url)
                # We are interested in the natural_language_answer.
                if isinstance(response_content[0], str):
                    final_nl_answer = response_content[0]
                    # If there's a second element and it's a string, it might be the SQL query
                    if len(response_content) > 1 and isinstance(response_content[1], str):
                        sql_query = response_content[1]
                # If the second element is a DataFrame and we want to format it
                elif len(response_content) > 1 and response_content[1] is not None and hasattr(response_content[1], 'empty') and not response_content[1].empty:
                    df_results = response_content[1]
                    final_nl_answer = f"Here are the results I found:\n{df_results.to_string(index=False, max_rows=10)}"
                    if len(df_results) > 10:
                        final_nl_answer += "\n(Showing top 10 results)"

            # Try to extract SQL query from Vanna's response if not already found
            if sql_query is None and hasattr(self.vn, 'get_last_sql'):
                try:
                    sql_query = self.vn.get_last_sql()
                except Exception as sql_extract_error:
                    print(f"Error extracting SQL from Vanna: {sql_extract_error}")
            
            # Validate that the SQL query contains the patient ID filter
            if sql_query:
                if patient_id not in sql_query and "patientId" not in sql_query:
                    print(f"WARNING: Generated SQL does not contain patient ID filter: {sql_query}")
                    # Reject the query as it doesn't contain proper patient filtering
                    raise PermissionError(f"Query security violation: Missing patient filter for {patient_id}")
                
                # Add safety message to the answer
                final_nl_answer = f"I found information for patient {patient_id}: {final_nl_answer}"
            
            return final_nl_answer, sql_query
        except Exception as e:
            print(f"Error during Vanna interaction: {e}")
            # Ensure the return type matches the function signature
            return f"I'm sorry, I couldn't process your request at this time. Please try again or rephrase your question.", None

def get_vanna_handler():
    # This could involve more complex setup or singleton pattern in a real app
    return VannaHandler()
