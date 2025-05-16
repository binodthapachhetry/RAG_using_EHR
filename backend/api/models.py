from pydantic import BaseModel                                                 
from enum import Enum                                                          
                                                                              
class QueryType(str, Enum):                                                    
    SIMPLE = "simple"                                                          
    COMPLEX = "complex"                                                        
    UNDETERMINED = "undetermined"                                              
                                                                               
class ChatRequest(BaseModel):                                                  
    query: str                                                                 
    patient_id: str # Assuming patient_id is known and provided                
    session_id: str | None = None                                              
                                                                               
class ChatResponse(BaseModel):                                                 
    answer: str                                                                
    patient_id: str                                                            
    query_type: QueryType                                                      
    sources: list[dict] | None = None # For RAG, to cite sources               
    error_message: str | None = None                                           
                                      