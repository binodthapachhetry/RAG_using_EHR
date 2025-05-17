from fastapi import FastAPI, HTTPException, Depends                            
from .api.models import ChatRequest, ChatResponse, QueryType                   
from .services.query_router import route_query                                 
from .services.bigquery_handler import BigQueryHandler, get_bigquery_handler   
from .services.rag_llm_handler import RagLlmHandler, get_rag_llm_handler       
                                                                               
app = FastAPI(                                                                 
    title="Physician Chat API",                                                
    description="API for querying patient data from FHIR BigQuery dataset.",   
    version="0.1.0"                                                            
)                                                                              
                                                                               
@app.post("/chat", response_model=ChatResponse)                                
async def handle_chat_request(                                                 
    request: ChatRequest,                                                      
    bq_handler: BigQueryHandler = Depends(get_bigquery_handler),               
    rag_handler: RagLlmHandler = Depends(get_rag_llm_handler)                  
):                                                                             
    """                                                                        
    Handles incoming chat requests, routes them, and returns a response.       
    """                                                                        
    query_type, patient_id, query_text_for_handler = route_query(request.query, request.patient_id)
    llm_generated_answer: str
                                                                               
    if query_type == QueryType.SIMPLE:                                         
        retrieved_data = await bq_handler.handle_simple_query(patient_id, query_text_for_handler)
        print("Retrieved data for simple query:", retrieved_data) # User's existing print
        # Pass the original request.query to the summarization function
        llm_generated_answer = await rag_handler.generate_summary_from_data(retrieved_data, request.query)
    elif query_type == QueryType.COMPLEX:                                      
        llm_generated_answer = await rag_handler.handle_complex_query(patient_id, query_text_for_handler)
    else:                                                                      
        raise HTTPException(status_code=400, detail="Could not determine query type.")                                                                         
                                                                               
    return ChatResponse(answer=llm_generated_answer, patient_id=request.patient_id, session_id=request.session_id, query_type=query_type) 
