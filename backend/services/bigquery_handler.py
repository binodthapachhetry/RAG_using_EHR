from google.cloud import bigquery                                              
from ..config import settings                                                  
import asyncio # For running synchronous client calls in a thread
                                                                               
class BigQueryHandler:
    def __init__(self, job_exec_project_id: str, data_source_project_id: str, dataset_id: str):
        # Client configured to run/bill jobs in the user's project
        self.client = bigquery.Client(project=job_exec_project_id)
        # Storing data source project and dataset for constructing table paths
        self.data_source_project_id = data_source_project_id
        self.dataset_id = dataset_id
        # Table names are PascalCase in FHIR BigQuery datasets
        self.fhir_base_tables = {
            "patient": f"{data_source_project_id}.{dataset_id}.Patient",
            "medicationrequest": f"{data_source_project_id}.{dataset_id}.MedicationRequest",
            "condition": f"{data_source_project_id}.{dataset_id}.Condition",
            "observation": f"{data_source_project_id}.{dataset_id}.Observation", # For lab results, vitals
            "allergyintolerance": f"{data_source_project_id}.{dataset_id}.AllergyIntolerance",
        }
                                                                               
    async def handle_simple_query(self, patient_id: str, query_text: str) -> list[dict]:                                                                     
        """                                                                    
        Handles simple, direct queries to BigQuery based on parsed intent from query_text.                                                                     
        This is a placeholder for specific query construction logic.           
        """                                                                    
        # Example: "List medications for patient X"                            
        # This would be further parsed to identify the target resource (MedicationRequest)                                                             
        # and construct the appropriate SQL query.                             
                                                                               
        # Placeholder logic - replace with actual query construction           
        # based on query_text analysis (e.g. identify "medications","allergies")                                                                    
        if "medication" in query_text.lower():                                 
            # IMPORTANT: Always use parameterized queries to prevent SQL injection                                                                       
            sql_query = f"""                                                   
                SELECT M.medication.codeableConcept.text                        
                FROM `{self.fhir_base_tables['medicationrequest']}` AS M       
                WHERE M.subject.patientId = @patient_id                        
            """                                                                
            query_params = [bigquery.ScalarQueryParameter("patient_id","STRING", patient_id)]   
            print("SQL_query:", sql_query)   
            print("Query_params:", query_params) 

        elif "allergies" in query_text.lower():                                
            sql_query = f"""                                                  
                SELECT A.code.text                                             
                FROM `{self.fhir_base_tables['allergyintolerance']}` AS A      
                WHERE A.patient.patientId = @patient_id                        
            """                                                                
            query_params = [bigquery.ScalarQueryParameter("patient_id","STRING", patient_id)]                                                          
        else:                                                                  
            return [{"error": "Unsupported simple query type."}]               
                                                                               
        # Use the _run_query helper to execute the query asynchronously
        return await self._run_query(sql_query, query_params)

    async def _run_query(self, sql_query: str, query_params: list[bigquery.ScalarQueryParameter] | None = None) -> list[dict]:
        """
        Helper to run a BigQuery query asynchronously using asyncio.to_thread.
        """
        job_config = bigquery.QueryJobConfig(query_parameters=query_params) if query_params else bigquery.QueryJobConfig()
        
        # Explicitly set the location for the query job to US, as public data is there.
        # This helps ensure the job runs in the same general location as the data.
        job_config.location = "US"
        
        # This is the synchronous part that will be run in a separate thread
        def sync_bq_call():
            query_job = self.client.query(sql_query, job_config=job_config)
            return [dict(row) for row in query_job.result()]

        # For Python 3.9+. For older versions, use loop.run_in_executor(None, sync_bq_call)
        results = await asyncio.to_thread(sync_bq_call)
        return results

    async def fetch_comprehensive_patient_summary(self, patient_id: str) -> str:
        """
        Fetches a comprehensive summary for a given patient_id from BigQuery.
        This includes demographics, active conditions, active medications, allergies,
        and recent observations.
        """
        summary_parts = []
        patient_query_param = [bigquery.ScalarQueryParameter("patient_id", "STRING", patient_id)]

        # 1. Patient Demographics
        patient_sql = f"""
            SELECT
                (SELECT name_item.text FROM UNNEST(P.name) AS name_item LIMIT 1) AS patient_name,
                P.gender,
                P.birthDate
            FROM `{self.fhir_base_tables['patient']}` AS P
            WHERE P.id = @patient_id
        """
        patient_results = await self._run_query(patient_sql, patient_query_param)
        if patient_results:
            patient_data = patient_results[0]
            summary_parts.append(f"Patient Name: {patient_data.get('patient_name', 'N/A')}")
            summary_parts.append(f"Gender: {patient_data.get('gender', 'N/A')}")
            summary_parts.append(f"Birth Date: {patient_data.get('birthDate', 'N/A')}")
            summary_parts.append("") # Newline for separation

        # 2. Active Conditions
        conditions_sql = f"""
            SELECT C.code.text AS condition_text
            FROM `{self.fhir_base_tables['condition']}` AS C
            WHERE C.subject.patientId = @patient_id
            AND (
                EXISTS (SELECT 1 FROM UNNEST(C.clinicalStatus.coding) AS cs WHERE cs.code = 'active') OR
                EXISTS (SELECT 1 FROM UNNEST(C.verificationStatus.coding) AS vs WHERE vs.code = 'confirmed')
            )
        """
        condition_results = await self._run_query(conditions_sql, patient_query_param)
        if condition_results:
            summary_parts.append("Active Conditions:")
            for row in condition_results:
                summary_parts.append(f"- {row.get('condition_text', 'N/A')}")
            summary_parts.append("")

        # 3. Active Medications
        medications_sql = f"""
            SELECT M.medicationCodeableConcept.text AS medication_text
            FROM `{self.fhir_base_tables['medicationrequest']}` AS M
            WHERE M.subject.patientId = @patient_id AND M.status = 'active'
        """
        medication_results = await self._run_query(medications_sql, patient_query_param)
        if medication_results:
            summary_parts.append("Current Medications:")
            for row in medication_results:
                summary_parts.append(f"- {row.get('medication_text', 'N/A')}")
            summary_parts.append("")

        # 4. Allergies
        allergies_sql = f"""
            SELECT A.code.text AS allergy_text
            FROM `{self.fhir_base_tables['allergyintolerance']}` AS A
            WHERE A.patient.patientId = @patient_id
            AND EXISTS (SELECT 1 FROM UNNEST(A.clinicalStatus.coding) AS cs WHERE cs.code = 'active')
        """ # Note: Synthea often doesn't populate clinicalStatus for AllergyIntolerance, verificationStatus might be better
          # but for simplicity, sticking to clinicalStatus: active. This might yield few results for Synthea.
        allergy_results = await self._run_query(allergies_sql, patient_query_param)
        if allergy_results:
            summary_parts.append("Allergies:")
            for row in allergy_results:
                summary_parts.append(f"- {row.get('allergy_text', 'N/A')}")
            summary_parts.append("")

        # 5. Recent Observations (e.g., last 5)
        observations_sql = f"""
            SELECT
                COALESCE(O.code.text, (SELECT c.display FROM UNNEST(O.code.coding) c WHERE c.system = 'http://loinc.org' LIMIT 1)) AS observation_text,
                O.valueQuantity.value AS observation_value,
                O.valueQuantity.unit AS observation_unit,
                O.valueString,
                (SELECT vc.text FROM UNNEST(O.valueCodeableConcept.coding) vc LIMIT 1) AS value_codeable_concept_text,
                O.effectiveDateTime
            FROM `{self.fhir_base_tables['observation']}` AS O
            WHERE O.subject.patientId = @patient_id
            ORDER BY O.effectiveDateTime DESC
            LIMIT 5
        """
        observation_results = await self._run_query(observations_sql, patient_query_param)
        if observation_results:
            summary_parts.append("Recent Observations:")
            for row in observation_results:
                obs_text = row.get('observation_text') or "Observation"
                value_str = "N/A"
                if row.get('observation_value') is not None and row.get('observation_unit') is not None:
                    value_str = f"{row['observation_value']} {row['observation_unit']}"
                elif row.get('valueString') is not None:
                    value_str = row['valueString']
                elif row.get('value_codeable_concept_text') is not None:
                    value_str = row['value_codeable_concept_text']
                
                date_str = row.get('effectiveDateTime', 'N/A')
                # Ensure date_str is a string, as it might be a datetime object from BigQuery
                summary_parts.append(f"- {obs_text}: {value_str} (Recorded: {str(date_str)})")
            summary_parts.append("")

        return "\n".join(summary_parts).strip()
                                                                               
def get_bigquery_handler():                                                    
    # This could involve more complex setup or pooling in a real app           
    return BigQueryHandler(
        job_exec_project_id=settings.VERTEX_AI_PROJECT_ID, # Project where jobs run & are billed
        data_source_project_id=settings.BIGQUERY_PROJECT_ID, # Project where FHIR data resides
        dataset_id=settings.FHIR_DATASET_ID
    )
