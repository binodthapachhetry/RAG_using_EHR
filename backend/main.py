from fastapi import FastAPI, HTTPException, Depends                            
from .api.models import ChatRequest, ChatResponse, QueryType                   
# from .services.query_router import route_query # No longer primary router
from .services.bigquery_handler import BigQueryHandler, get_bigquery_handler # May still be needed for RAG or direct execution
from .services.rag_llm_handler import RagLlmHandler, get_rag_llm_handler # May be used for RAG or complex summarization
from .services.vanna_handler import VannaHandler, get_vanna_handler
                                                                               
app = FastAPI(                                                                 
    title="Physician Chat API",                                                
    description="API for querying patient data from FHIR BigQuery dataset.",   
    version="0.1.0"                                                            
)                                                                              
                                                                               
@app.post("/chat", response_model=ChatResponse)                                
async def handle_chat_request(                                                 
    request: ChatRequest,                                                      
    bq_handler: BigQueryHandler = Depends(get_bigquery_handler),               
    rag_handler: RagLlmHandler = Depends(get_rag_llm_handler),
    vanna_handler: VannaHandler = Depends(get_vanna_handler)
):                                                                             
    """                                                                        
    Handles incoming chat requests, routes them, and returns a response.       
    Primarily uses Vanna.AI for text-to-SQL and response generation.
    """                                                                        
    # For now, all queries go through Vanna.
    # The old query_router and simple/complex distinction is bypassed.
    # Future: Could re-introduce a router if some queries are better for RAG.

    nl_answer = await vanna_handler.get_response(
        natural_language_query=request.query,
        patient_id=request.patient_id
    )

    # Determine a QueryType for the response, Vanna primarily does SQL generation.
    # If SQL was generated, we can consider it a "data query" type.
    # This is a simplification; Vanna might do more complex things.
    # response_query_type = QueryType.SIMPLE if sql_query else QueryType.COMPLEX 

    # print(f"Vanna SQL Query: {sql_query}")
    print(f"Vanna NL Answer: {nl_answer}")
    print("Type", type(nl_answer))

    return ChatResponse(answer=nl_answer, 
                        patient_id=request.patient_id)
