import os                                                                      
from dotenv import load_dotenv                                                 
                                                                               
load_dotenv() # Loads environment variables from .env file if present          
                                                                               
class Settings:                                                                
    GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "bigquery-public-data")  
    FHIR_DATASET_ID: str = os.getenv("FHIR_DATASET_ID", "fhir_synthea")        
    GCP_REGION: str = os.getenv("GCP_REGION", "us-central1")
                                                                               
    # LLM Configuration (example)                                              
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "gemini-pro") # Or your preferred model                                                                                                                                        
                                                                              
settings = Settings()
