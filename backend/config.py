import os                                                                      
from dotenv import load_dotenv                                                 
                                                                               
load_dotenv() # Loads environment variables from .env file if present          
                                                                               
class Settings:                                                                
    # Project ID for accessing BigQuery datasets (e.g., public data)
    BIGQUERY_PROJECT_ID: str = os.getenv("BIGQUERY_PROJECT_ID", "bigquery-public-data")  
    FHIR_DATASET_ID: str = os.getenv("FHIR_DATASET_ID", "fhir_synthea") # Dataset within the BIGQUERY_PROJECT_ID
    # Project ID where Vertex AI services are enabled and billed
    VERTEX_AI_PROJECT_ID: str = os.getenv("VERTEX_AI_PROJECT_ID", "your-gcp-project-for-vertex-ai") # Replace with your actual project
    GCP_REGION: str = os.getenv("GCP_REGION", "us-central1")
                                                                               
    # LLM Configuration (example)                                              
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "gemini-pro") # Or your preferred model                                                                                                                                        
                                                                              
settings = Settings()
