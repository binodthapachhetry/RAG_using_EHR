from langchain_google_vertexai import ChatVertexAI
from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from ..utils.schema_loader import get_fhir_synthea_schema

from ..config import settings

# Fully qualified table names
PATIENT_TABLE_FQ = f"`{settings.BIGQUERY_PROJECT_ID}.{settings.FHIR_DATASET_ID}.Patient`"
MED_REQ_TABLE_FQ = f"`{settings.BIGQUERY_PROJECT_ID}.{settings.FHIR_DATASET_ID}.MedicationRequest`"
CONDITION_TABLE_FQ = f"`{settings.BIGQUERY_PROJECT_ID}.{settings.FHIR_DATASET_ID}.Condition`"
OBSERVATION_TABLE_FQ = f"`{settings.BIGQUERY_PROJECT_ID}.{settings.FHIR_DATASET_ID}.Observation`"
ALLERGY_TABLE_FQ = f"`{settings.BIGQUERY_PROJECT_ID}.{settings.FHIR_DATASET_ID}.AllergyIntolerance`"
ENCOUNTER_TABLE_FQ = f"`{settings.BIGQUERY_PROJECT_ID}.{settings.FHIR_DATASET_ID}.Encounter`"
PROCEDURE_TABLE_FQ = f"`{settings.BIGQUERY_PROJECT_ID}.{settings.FHIR_DATASET_ID}.Procedure`"

ANSWER_PROMPT = PromptTemplate.from_template(
    """Given the following user question, corresponding SQL query, and SQL result, answer the user question.
If the SQL result is empty or contains no relevant information, state that no information was found for the specific request.

Question: {question}
SQL Query: {query}
SQL Result: {result}
Answer:"""
)

class LangchainSqlHandler:
    def __init__(self):
        self.llm = ChatVertexAI(
            project=settings.VERTEX_AI_PROJECT_ID,
            location=settings.GCP_REGION,
            model_name=settings.LLM_MODEL_NAME
        )
        # Connection URI for BigQuery using SQLAlchemy
        # Jobs will run in VERTEX_AI_PROJECT_ID (where client is initialized), data is read from BIGQUERY_PROJECT_ID.FHIR_DATASET_ID
        db_uri = f"bigquery://{settings.BIGQUERY_PROJECT_ID}/{settings.FHIR_DATASET_ID}"

        # Pull full authoritative DDLs for every table in the dataset
        custom_table_info_dict = get_fhir_synthea_schema(
            settings.BIGQUERY_PROJECT_ID,
            settings.FHIR_DATASET_ID
        )
        
        self.db = SQLDatabase.from_uri(
            db_uri,
            sample_rows_in_table_info=0, # Do not include sample rows in table info
            custom_table_info=custom_table_info_dict,
            include_tables=list(custom_table_info_dict.keys())
        )

        self.generate_query_chain = create_sql_query_chain(self.llm, self.db)
        # Using RunnablePassthrough to ensure the query string is passed to db.run
        self.execute_query_chain = RunnablePassthrough.assign(result=lambda x: self.db.run(x["query"]))
        self.answer_chain = ANSWER_PROMPT | self.llm | StrOutputParser()

        # Full chain: Generate SQL, execute SQL, then use result to answer question
        self.full_chain = (
            RunnablePassthrough.assign(query=self.generate_query_chain).assign(
                result= lambda x: self.db.run(x["query"]) # Execute the generated query
            )
            | self.answer_chain
        )

    async def get_response(self, natural_language_query: str, patient_id: str) -> tuple[str | None, str | None]:
        system_message = f"""You MUST include 'WHERE subject.patientId = '{patient_id}' 
        in all queries. Never query other patients."""
        question_with_context = f"For patient ID '{patient_id}': {natural_language_query}. Ensure all SQL queries explicitly filter for this patient ID using the correct patient identifier column for each table (e.g., Patient.id='{patient_id}', MedicationRequest.subject.patientId='{patient_id}', Condition.subject.patientId='{patient_id}', Observation.subject.patientId='{patient_id}', AllergyIntolerance.patient.patientId='{patient_id}', Encounter.subject.patientId='{patient_id}', Procedure.subject.patientId='{patient_id}'). Only query tables relevant to the question."
        question_with_context = system_message + question_with_context

        try:
            # To get the SQL query separately for logging/returning:
            sql_query = self.generate_query_chain.invoke({"question": question_with_context})
            print(f"Langchain Generated SQL: {sql_query}")
            
            # Execute the full chain to get the NL answer
            # The full_chain internally regenerates the query and executes it.
            # To avoid re-generating query, we can invoke parts of the chain:
            # sql_result = self.db.run(sql_query)
            # print(f"Langchain SQL Result: {sql_result}")
            # nl_answer = self.answer_chain.invoke({"question": question_with_context, "query": sql_query, "result": sql_result})

            # Using the pre-defined full_chain for simplicity, though it might re-run query generation.
            # For more control and to ensure the logged SQL is the one used for the result:
            chain_input = {"question": question_with_context}
            # First, get the SQL query
            generated_sql_query = self.generate_query_chain.invoke(chain_input)
            print(f"Langchain Generated SQL: {generated_sql_query}")
            
            if not self._validate_sql(generated_sql_query, patient_id):
                raise ValueError(f"Query validation failed for patient {patient_id}")

            # Then, execute the query
            sql_result = self.db.run(generated_sql_query)
            print(f"Langchain SQL Result: {sql_result}")
            
            # Finally, generate the natural language answer
            nl_answer = self.answer_chain.invoke({
                "question": question_with_context, # Pass original question with context
                "query": generated_sql_query,
                "result": sql_result
            })

            return nl_answer, generated_sql_query
        except Exception as e:
            print(f"Error during Langchain SQL interaction: {e}")
            if 'generated_sql_query' in locals() and "patientId" not in str(generated_sql_query):
                raise PermissionError("Query security violation")
            error_message = f"An error occurred while processing your request with Langchain SQL: {str(e)}"
            # Attempt to get the LLM to phrase the error to the user
            try:
                error_prompt = f"An internal error occurred: {str(e)}. Please inform the user politely that their request could not be completed due to this error."
                nl_error_answer = self.llm.predict(error_prompt) # predict is a shorthand
                return nl_error_answer, None
            except Exception: # Fallback if LLM fails during error reporting
                 return error_message, None


    def _validate_sql(self, sql_query: str, patient_id: str) -> bool:
        """
        Validates that the SQL query contains proper patient ID filtering.
        """
        sql_lower = sql_query.lower()
        # Check for patient ID filtering in various forms
        patient_filters = [
            f"patient.id = '{patient_id}'",
            f"patient.patientid = '{patient_id}'", 
            f"subject.patientid = '{patient_id}'",
            f"p.id = '{patient_id}'",
            f"t1.id = '{patient_id}'",
            f"t1.subject.patientid = '{patient_id}'",
            f"t1.patient.patientid = '{patient_id}'"
        ]
        
        # Also check for parameterized queries
        param_filters = [
            "patient.id = @patient_id",
            "patient.patientid = @patient_id",
            "subject.patientid = @patient_id",
            "p.id = @patient_id",
            "t1.id = @patient_id",
            "t1.subject.patientid = @patient_id",
            "t1.patient.patientid = @patient_id"
        ]
        
        # Check for any of the filter patterns
        has_direct_filter = any(filter_text.lower() in sql_lower for filter_text in patient_filters)
        has_param_filter = any(filter_text.lower() in sql_lower for filter_text in param_filters)
        
        # Log validation results for security auditing
        if not (has_direct_filter or has_param_filter):
            print(f"SQL SECURITY VIOLATION: Query does not contain proper patient filtering: {sql_query}")
        
        return has_direct_filter or has_param_filter

def get_langchain_sql_handler():
    return LangchainSqlHandler()
