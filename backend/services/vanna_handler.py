import vanna
# Corrected imports for Vanna Vertex AI and BigQuery connectors
from vanna.google import GoogleGeminiChat # Changed from vanna.vertex
from vanna.google import BigQuery_VectorStore # Assuming this is available after pip install "vanna[google]"

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

# Vanna needs to be "trained" on your schema.
# This is a simplified representation. In a real scenario, you would provide
# more comprehensive DDLs, documentation strings, and potentially sample SQL queries.
# IMPORTANT: Use PascalCase for table names as in fhir_synthea.
# Use fully qualified table names in DDLs for clarity with Vanna.
TRAINING_DDLS = [
    f"""
    CREATE TABLE {PATIENT_TABLE_FQ} (
        id STRING, -- Primary patient identifier
        active BOOLEAN, -- Whether this patient record is in active use.
        name JSON, -- ARRAY<STRUCT<use STRING, text STRING, family STRING, given ARRAY<STRING>>>. For official name text: (SELECT n.text FROM UNNEST(name) AS n WHERE n.use = 'official' LIMIT 1). For usual name: (SELECT n.text FROM UNNEST(name) AS n WHERE n.use = 'usual' LIMIT 1).
        gender STRING,
        birthDate DATE,
        deceasedBoolean BOOLEAN, -- True if patient is deceased.
        deceasedDateTime TIMESTAMP, -- Date and time of death if deceasedBoolean is true.
        maritalStatus JSON, -- STRUCT<text STRING, coding ARRAY<STRUCT<system STRING, code STRING, display STRING>>>. Get marital status text from maritalStatus.text.
        multipleBirthBoolean BOOLEAN, -- True if patient was part of a multiple birth.
        address JSON -- ARRAY<STRUCT<use STRING, type STRING, text STRING, city STRING, state STRING, postalCode STRING, country STRING>>. For home city: (SELECT a.city FROM UNNEST(address) AS a WHERE a.use = 'home' LIMIT 1).
    );
    """,
    f"""
    CREATE TABLE {MED_REQ_TABLE_FQ} (
        id STRING,
        status STRING, -- e.g., 'active', 'completed', 'stopped', 'on-hold', 'cancelled', 'draft', 'entered-in-error', 'unknown'.
        intent STRING, -- e.g., 'order', 'plan', 'proposal'.
        priority STRING, -- e.g., 'routine', 'urgent', 'asap', 'stat'.
        medicationCodeableConcept JSON, -- STRUCT<text STRING, coding ARRAY<STRUCT<system STRING, code STRING, display STRING>>>. To get medication name: medicationCodeableConcept.text.
        subject JSON, -- STRUCT<reference STRING, type STRING, patientId STRING>. To get patientId: subject.patientId.
        encounter JSON, -- STRUCT<reference STRING, type STRING, encounterId STRING>. Reference to the encounter during which the medication was requested.
        authoredOn TIMESTAMP, -- Date medication was prescribed.
        requester JSON -- STRUCT<agent JSON, onBehalfOf JSON>. Information about the prescriber.
    );
    """,
    f"""
    CREATE TABLE {CONDITION_TABLE_FQ} (
        id STRING,
        clinicalStatus JSON, -- STRUCT<coding ARRAY<STRUCT<system STRING, code STRING, display STRING>>>. Example: clinicalStatus.coding[OFFSET(0)].code can be 'active', 'recurrence', 'relapse', 'inactive', 'remission', 'resolved'.
        verificationStatus JSON, -- STRUCT<coding ARRAY<STRUCT<system STRING, code STRING, display STRING>>>. Example: verificationStatus.coding[OFFSET(0)].code can be 'unconfirmed', 'provisional', 'differential', 'confirmed', 'refuted', 'entered-in-error'.
        category JSON, -- ARRAY<STRUCT<coding ARRAY<STRUCT<system STRING, code STRING, display STRING>>>>. e.g. 'encounter-diagnosis', 'problem-list-item'.
        severity JSON, -- STRUCT<text STRING, coding ARRAY<STRUCT<system STRING, code STRING, display STRING>>>. e.g. 'mild', 'moderate', 'severe'.
        code JSON, -- STRUCT<text STRING, coding ARRAY<STRUCT<system STRING, code STRING, display STRING>>>. To get condition name: code.text.
        subject JSON, -- STRUCT<reference STRING, patientId STRING>. To get patientId: subject.patientId.
        onsetDateTime TIMESTAMP, -- Estimated date/time of condition onset.
        abatementDateTime TIMESTAMP, -- If applicable, when condition resolved.
        recordedDate DATE -- Date condition was first recorded.
    );
    """,
    f"""
    CREATE TABLE {OBSERVATION_TABLE_FQ} (
        id STRING,
        status STRING, -- e.g., 'final', 'amended', 'corrected', 'preliminary'.
        category JSON, -- ARRAY<STRUCT<coding ARRAY<STRUCT<system STRING, code STRING, display STRING>>>>. E.g. 'vital-signs', 'laboratory', 'social-history'. To get category: category[OFFSET(0)].coding[OFFSET(0)].code.
        code JSON, -- STRUCT<text STRING, coding ARRAY<STRUCT<system STRING, code STRING, display STRING>>>. To get observation name: code.text or code.coding[OFFSET(0)].display.
        subject JSON, -- STRUCT<reference STRING, patientId STRING>. To get patientId: subject.patientId.
        effectiveDateTime TIMESTAMP, -- Clinically relevant time of the observation.
        issued TIMESTAMP, -- Date this version was released.
        valueQuantity JSON, -- STRUCT<value DECIMAL, unit STRING, system STRING, code STRING>. For numeric values: valueQuantity.value, valueQuantity.unit.
        valueString STRING, -- For string values.
        valueCodeableConcept JSON, -- STRUCT<text STRING, coding ARRAY<STRUCT<system STRING, code STRING, display STRING>>>. For coded values: valueCodeableConcept.text.
        interpretation JSON -- STRUCT<coding ARRAY<STRUCT<system STRING, code STRING, display STRING>>>. e.g. 'H' for high, 'L' for low. interpretation.coding[OFFSET(0)].code.
    );
    """,
    f"""
    CREATE TABLE {ALLERGY_TABLE_FQ} (
        id STRING,
        clinicalStatus JSON, -- STRUCT<coding ARRAY<STRUCT<system STRING, code STRING, display STRING>>>. Example: clinicalStatus.coding[OFFSET(0)].code can be 'active', 'inactive', 'resolved'.
        verificationStatus JSON, -- STRUCT<coding ARRAY<STRUCT<system STRING, code STRING, display STRING>>>. Example: verificationStatus.coding[OFFSET(0)].code can be 'unconfirmed', 'confirmed', 'refuted', 'entered-in-error'.
        type STRING, -- e.g., 'allergy', 'intolerance'.
        category ARRAY<STRING>, -- e.g. 'food', 'medication', 'environment'.
        criticality STRING, -- e.g. 'low', 'high', 'unable-to-assess'.
        code JSON, -- STRUCT<text STRING, coding ARRAY<STRUCT<system STRING, code STRING, display STRING>>>. To get allergy name: code.text.
        patient JSON, -- STRUCT<reference STRING, patientId STRING>. To get patientId: patient.patientId.
        onsetDateTime TIMESTAMP, -- Date/time of first manifestation.
        recordedDate DATE -- Date allergy was first recorded.
    );
    """,
    f"""
    CREATE TABLE {ENCOUNTER_TABLE_FQ} (
        id STRING,
        status STRING, -- e.g., 'finished', 'in-progress', 'cancelled'.
        class JSON, -- STRUCT<system STRING, code STRING, display STRING>. e.g. code 'AMB' for ambulatory, 'IMP' for inpatient.
        type JSON, -- ARRAY<STRUCT<text STRING, coding ARRAY<STRUCT<system STRING, code STRING, display STRING>>>>. Encounter type description: type[OFFSET(0)].text.
        priority JSON, -- STRUCT<coding ARRAY<STRUCT<system STRING, code STRING, display STRING>>>.
        subject JSON, -- STRUCT<reference STRING, patientId STRING>. To get patientId: subject.patientId.
        period JSON -- STRUCT<start TIMESTAMP, end TIMESTAMP>. For encounter duration. period.start and period.end.
    );
    """,
    f"""
    CREATE TABLE {PROCEDURE_TABLE_FQ} (
        id STRING,
        status STRING, -- e.g., 'completed', 'in-progress', 'preparation', 'on-hold', 'stopped', 'entered-in-error'.
        category JSON, -- STRUCT<text STRING, coding ARRAY<STRUCT<system STRING, code STRING, display STRING>>>.
        code JSON, -- STRUCT<text STRING, coding ARRAY<STRUCT<system STRING, code STRING, display STRING>>>. To get procedure name: code.text.
        subject JSON, -- STRUCT<reference STRING, patientId STRING>. To get patientId: subject.patientId.
        performedDateTime TIMESTAMP, -- Single point in time.
        performedPeriod JSON -- STRUCT<start TIMESTAMP, end TIMESTAMP>. For procedure duration. performedPeriod.start and performedPeriod.end.
    );
    """,
]
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
        if existing_training_data.empty or len(existing_training_data) < len(TRAINING_DDLS): # Simple check
            print("Training Vanna with DDLs, documentation, and SQL samples...")
            for ddl in TRAINING_DDLS:
                self.vn.train(ddl=ddl)
            
            # General Documentation
            self.vn.train(documentation="When a question refers to 'the patient' or includes a 'patient_id', filter data for that specific patient. Use the patient_id in a WHERE clause.")

            # Table/Column Specific Documentation
            self.vn.train(documentation=f"Table {PATIENT_TABLE_FQ}: Contains patient demographic information. Primary key and patient identifier is 'id'. Filter by patient ID using 'id = :patient_id'.")
            self.vn.train(documentation=f"From {PATIENT_TABLE_FQ}: Get official name text using (SELECT n.text FROM UNNEST(name) AS n WHERE n.use = 'official' LIMIT 1). Get usual name text using (SELECT n.text FROM UNNEST(name) AS n WHERE n.use = 'usual' LIMIT 1). Get home city using (SELECT a.city FROM UNNEST(address) AS a WHERE a.use = 'home' LIMIT 1). 'birthDate' is the date of birth. 'deceasedBoolean' indicates if patient is deceased.")
            self.vn.train(documentation=f"Table {MED_REQ_TABLE_FQ}: Lists medication orders. Filter by patient using 'subject.patientId = :patient_id'.")
            self.vn.train(documentation=f"From {MED_REQ_TABLE_FQ}: Get medication name from 'medicationCodeableConcept.text'. Active medications have 'status = \"active\"'. 'authoredOn' is the prescription date. 'intent' field often 'order'.")
            self.vn.train(documentation=f"Table {CONDITION_TABLE_FQ}: Lists patient health conditions. Filter by patient using 'subject.patientId = :patient_id'. Get condition name from 'code.text'.")
            self.vn.train(documentation=f"From {CONDITION_TABLE_FQ}: Confirmed conditions often have 'EXISTS (SELECT 1 FROM UNNEST(verificationStatus.coding) AS vs WHERE vs.code = 'confirmed')'. Active conditions often have 'EXISTS (SELECT 1 FROM UNNEST(clinicalStatus.coding) AS cs WHERE cs.code = 'active')'. 'onsetDateTime' is when the condition started. 'recordedDate' is when it was recorded.")
            self.vn.train(documentation=f"Table {OBSERVATION_TABLE_FQ}: Contains patient observations (labs, vitals, social history). Filter by patient using 'subject.patientId = :patient_id'. Get observation name from 'code.text' or 'code.coding[OFFSET(0)].display'.")
            self.vn.train(documentation=f"From {OBSERVATION_TABLE_FQ}: Numeric values are in 'valueQuantity.value' with units in 'valueQuantity.unit'. String values are in 'valueString'. Coded values are in 'valueCodeableConcept.text'. 'effectiveDateTime' is when the observation was made. Common categories are 'vital-signs', 'laboratory', 'social-history' (check category[OFFSET(0)].coding[OFFSET(0)].code). Observation status is in 'status' field (e.g. 'final'). Interpretation (e.g. High/Low) is in 'interpretation.coding[OFFSET(0)].code'.")
            self.vn.train(documentation=f"Table {ALLERGY_TABLE_FQ}: Lists patient allergies and intolerances. Filter by patient using 'patient.patientId = :patient_id'. Get allergy name from 'code.text'. 'type' can be 'allergy' or 'intolerance'. 'criticality' indicates severity. 'recordedDate' is when it was recorded.")
            self.vn.train(documentation=f"Table {ENCOUNTER_TABLE_FQ}: Describes patient encounters (visits, admissions). Filter by patient using 'subject.patientId = :patient_id'. Encounter type is in 'type[OFFSET(0)].text'. Encounter class (e.g. ambulatory, inpatient) is in 'class.code'. Encounter duration is in 'period.start' and 'period.end'.")
            self.vn.train(documentation=f"Table {PROCEDURE_TABLE_FQ}: Lists procedures performed on patients. Filter by patient using 'subject.patientId = :patient_id'. Procedure name is in 'code.text'. Procedure date/time can be in 'performedDateTime' (single point) or 'performedPeriod.start' and 'performedPeriod.end' (duration).")

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
                question="What is the birth date of patient 'patient001'?",
                sql=f"SELECT T1.birthDate FROM {PATIENT_TABLE_FQ} AS T1 WHERE T1.id = 'patient001'"
            )
            self.vn.train(
                question="Find confirmed conditions for patient 'patient456'.",
                sql=f"SELECT T1.code.text FROM {CONDITION_TABLE_FQ} AS T1 WHERE T1.subject.patientId = 'patient456' AND EXISTS (SELECT 1 FROM UNNEST(T1.verificationStatus.coding) AS vs WHERE vs.code = 'confirmed')"
            )
            self.vn.train(
                question="What was the last recorded systolic blood pressure for patient 'patient002'?",
                sql=f"SELECT T1.valueQuantity.value FROM {OBSERVATION_TABLE_FQ} AS T1 WHERE T1.subject.patientId = 'patient002' AND T1.code.text = 'Systolic blood pressure' ORDER BY T1.effectiveDateTime DESC LIMIT 1"
            )
            self.vn.train(
                question="How many active medications does patient 'patient123' have?",
                sql=f"SELECT COUNT(T1.medicationCodeableConcept.text) FROM {MED_REQ_TABLE_FQ} AS T1 WHERE T1.subject.patientId = 'patient123' AND T1.status = 'active'"
            )
            self.vn.train(
                question="What is the usual name of patient 'patient001'?",
                sql=f"SELECT (SELECT n.text FROM UNNEST(T1.name) AS n WHERE n.use = 'usual' LIMIT 1) AS patient_name FROM {PATIENT_TABLE_FQ} AS T1 WHERE T1.id = 'patient001'"
            )
            self.vn.train(
                question="What allergies does patient 'patient123' have?",
                sql=f"SELECT T1.code.text FROM {ALLERGY_TABLE_FQ} AS T1 WHERE T1.patient.patientId = 'patient123'"
            )
            self.vn.train(
                question="List encounters for patient 'patient456' in the last year.",
                sql=f"SELECT T1.type[OFFSET(0)].text AS encounter_type, T1.period.start AS encounter_start FROM {ENCOUNTER_TABLE_FQ} AS T1 WHERE T1.subject.patientId = 'patient456' AND T1.period.start >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 YEAR)"
            )
            self.vn.train(
                question="What procedures has patient 'patient789' undergone?",
                sql=f"SELECT T1.code.text AS procedure_name FROM {PROCEDURE_TABLE_FQ} AS T1 WHERE T1.subject.patientId = 'patient789'"
            )
            self.vn.train(
                question="Find lab results for patient 'patient001'.",
                sql=f"SELECT O.code.text AS lab_test, O.valueQuantity.value AS result_value, O.valueQuantity.unit AS result_unit, O.effectiveDateTime FROM {OBSERVATION_TABLE_FQ} AS O WHERE O.subject.patientId = 'patient001' AND EXISTS (SELECT 1 FROM UNNEST(O.category) AS cat JOIN UNNEST(cat.coding) AS cat_coding WHERE cat_coding.code = 'laboratory') AND O.status = 'final' ORDER BY O.effectiveDateTime DESC"
            )
            # Removed the duplicate SQL sample for systolic blood pressure that was here.
            print("Vanna training submitted.")

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
            if sql_query and patient_id not in sql_query:
                print(f"WARNING: Generated SQL does not contain patient ID filter: {sql_query}")
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
