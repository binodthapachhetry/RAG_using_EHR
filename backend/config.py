import os                                                                      
from dotenv import load_dotenv                                                 
                                                                               
load_dotenv() # Loads environment variables from .env file if present          
                                                                               
class Settings:                                                                
    GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "bigquery-public-data")  
    FHIR_DATASET_ID: str = os.getenv("FHIR_DATASET_ID", "fhir_synthea")        
    GCP_REGION: str = os.getenv("GCP_REGION", "us-central1") # Default to us-central1, adjust as needed
                                                                               
    # LLM Configuration (example)                                              
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "gemini-pro") # Or your preferred model                                                                 
    # Add other relevant configurations like API keys if not handled by SDK defaults                                                                        
                                                                              
settings = Settings()
