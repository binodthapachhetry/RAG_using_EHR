from google.cloud import bigquery                                              
from ..config import settings                                                  
                                                                               
class BigQueryHandler:                                                         
    def __init__(self, project_id: str, dataset_id: str):                      
        self.client = bigquery.Client(project=project_id)                      
        self.project_id = project_id                                           
        self.dataset_id = dataset_id                                           
        self.fhir_base_tables = {                                              
            "patient": f"{project_id}.{dataset_id}.Patient",                   
            "medicationrequest": f"{project_id}.{dataset_id}.MedicationRequest",                                 
            "condition": f"{project_id}.{dataset_id}.Condition",               
            "observation": f"{project_id}.{dataset_id}.Observation", # For lab results, vitals                                                                 
            "allergyintolerance": f"{project_id}.{dataset_id}.AllergyIntolerance",                                
        }                                                                      
                                                                               
    async def handle_simple_query(self, patient_id: str, query_text: str) ->   list[dict]:                                                                     
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
                SELECT M.medicationCodeableConcept.text                        
                FROM `{self.fhir_base_tables['medicationrequest']}` AS M       
                WHERE M.subject.patientId = @patient_id                        
            """                                                                
            query_params = [bigquery.ScalarQueryParameter("patient_id","STRING", patient_id)]                                                          
        elif "allergies" in query_text.lower():                                
            sql_query = f"""                                                  
                SELECT A.code.text                                             
                FROM `{self.fhir_base_tables['allergyintolerance']}` AS A      
                WHERE A.patient.patientId = @patient_id                        
            """                                                                
            query_params = [bigquery.ScalarQueryParameter("patient_id","STRING", patient_id)]                                                          
        else:                                                                  
            return [{"error": "Unsupported simple query type."}]               
                                                                               
        job_config = bigquery.QueryJobConfig(query_parameters=query_params)    
        query_job = self.client.query(sql_query, job_config=job_config)        
        results = [dict(row) for row in query_job.result()] # Convert to list of dicts                                                                        
        return results                                                         
                                                                               
def get_bigquery_handler():                                                    
    # This could involve more complex setup or pooling in a real app           
    return BigQueryHandler(project_id=settings.BIGQUERY_PROJECT_ID,dataset_id=settings.FHIR_DATASET_ID) 
