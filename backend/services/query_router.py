from ..api.models import QueryType                                             
                                                                              
# Keywords that might indicate a simple, direct query                          
SIMPLE_QUERY_KEYWORDS = [                                                       
    "list medications", "show medications", "what medications",                
    "list allergies", "show allergies", "what allergies",                      
    "list conditions", "show conditions", "what conditions",                   
    "latest labs", "recent labs", "lab results for",                           
    "patient details for", "demographics for"]                                                                              
                                                                               
def route_query(query_text: str, patient_id: str) -> tuple[QueryType, str,str]:                                                                           
    """                                                                        
    Determines if a query is simple or complex based on keywords.              
    Returns the query type, patient_id, and the original query_text.           
    This is a basic implementation and can be expanded with more sophisticated logic.                                                                          
    """                                                                        
    lower_query = query_text.lower()                                           
                                                                               
    for keyword in SIMPLE_QUERY_KEYWORDS:                                      
        if keyword in lower_query:                                             
            return QueryType.SIMPLE, patient_id, query_text                    
                                                                               
    return QueryType.COMPLEX, patient_id, query_text 