from fastapi import FastAPI, HTTPException, Depends                            
from .api.models import ChatRequest, ChatResponse, QueryType                   
# from .services.query_router import route_query # No longer primary router
from .services.bigquery_handler import BigQueryHandler, get_bigquery_handler # May still be needed for RAG or direct execution
from .services.rag_llm_handler import RagLlmHandler, get_rag_llm_handler # May be used for RAG or complex summarization
from .services.vanna_handler import VannaHandler, get_vanna_handler # Keep for Vanna
from .services.langchain_sql_handler import LangchainSqlHandler, get_langchain_sql_handler # Add Langchain handler
from .config import settings # Import settings to choose handler
                                                                               
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
    # Specific handlers will be resolved based on config
):                                                                             
    """                                                                        
    Handles incoming chat requests, routes them, and returns a response.       
    Uses either Vanna.AI or Langchain for text-to-SQL and response generation based on configuration.
    """                                                                        
    nl_answer_str: str | None = None
    sql_query_str: str | None = None

    if settings.QUERY_HANDLER_TYPE == "langchain":
        print("Using Langchain SQL Handler")
        langchain_handler: LangchainSqlHandler = get_langchain_sql_handler()
        nl_answer_str, sql_query_str = await langchain_handler.get_response(
            natural_language_query=request.query,
            patient_id=request.patient_id
        )
    elif settings.QUERY_HANDLER_TYPE == "vanna":
        print("Using Vanna Handler")
        vanna_handler: VannaHandler = get_vanna_handler() # Get Vanna handler instance
        # Assuming vanna_handler.get_response now returns (nl_answer, sql_query)
        # This change in VannaHandler's signature is implied by the user's plan for main.py
        response_tuple = await vanna_handler.get_response(
            natural_language_query=request.query,
            patient_id=request.patient_id
        )
        # Check if response_tuple is indeed a tuple (nl_answer, sql_query)
        # or just nl_answer string as per original vanna_handler.py
        if isinstance(response_tuple, tuple) and len(response_tuple) == 2:
            nl_answer_str, sql_query_str = response_tuple
        elif isinstance(response_tuple, str): # Fallback if VannaHandler still returns only string
            nl_answer_str = response_tuple
            sql_query_str = None # Vanna might not always return SQL explicitly this way
            print("Warning: VannaHandler returned a single string. SQL query might not be available.")
        else: # Unexpected return type
            raise HTTPException(status_code=500, detail="Unexpected response type from VannaHandler.")

    else:
        raise HTTPException(status_code=500, detail=f"Invalid QUERY_HANDLER_TYPE: {settings.QUERY_HANDLER_TYPE}")

    response_query_type = QueryType.SIMPLE if sql_query_str else QueryType.UNDETERMINED 

    print(f"Handler ({settings.QUERY_HANDLER_TYPE}) SQL Query: {sql_query_str}")
    print(f"Handler ({settings.QUERY_HANDLER_TYPE}) NL Answer: {nl_answer_str}")

    return ChatResponse(
        answer=nl_answer_str or "No answer could be generated.", 
        patient_id=request.patient_id,
        query_type=response_query_type,
        sources=[{"sql_query": sql_query_str}] if sql_query_str else None
    )
