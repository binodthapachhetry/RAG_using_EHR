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

    # Validate patient_id is present and not empty
    if not request.patient_id or not request.patient_id.strip():
        raise HTTPException(status_code=400, detail="Patient ID is required")
    
    # Check if this is a simple query that can be handled directly by BigQuery handler
    if any(keyword in request.query.lower() for keyword in [
        "medication", "allergy", "allergies", "condition", "diagnosis", 
        "lab", "test", "result", "vital", "bp", "blood pressure"
    ]):
        try:
            # Try to handle as a simple query first
            results = await bq_handler.handle_simple_query(
                patient_id=request.patient_id,
                query_text=request.query
            )
            
            # If we got results (not an error), generate a natural language answer
            if results and not (isinstance(results, list) and results and "error" in results[0]):
                nl_answer_str = await rag_handler.generate_summary_from_data(
                    structured_data=results,
                    original_query=request.query
                )
                # Extract the SQL query from the BigQuery handler if possible
                # This would require adding a method to track the last query
                sql_query_str = "Simple query handled by BigQuery handler"
                
                return ChatResponse(
                    answer=nl_answer_str, 
                    patient_id=request.patient_id,
                    query_type=QueryType.SIMPLE,
                    sources=[{"sql_query": sql_query_str, "result_count": len(results)}]
                )
        except Exception as e:
            print(f"Error in simple query handling: {e}")
            # Continue to advanced handlers if simple query fails

    # If simple query handling didn't return, proceed with advanced handlers
    try:
        if settings.QUERY_HANDLER_TYPE == "langchain":
            print("Using Langchain SQL Handler")
            langchain_handler: LangchainSqlHandler = get_langchain_sql_handler()
            try:
                nl_answer_str, sql_query_str = await langchain_handler.get_response(
                    natural_language_query=request.query,
                    patient_id=request.patient_id
                )
            except PermissionError as e:
                # Handle security violations by returning a safe error message
                return ChatResponse(
                    answer="I'm sorry, but I cannot process this request due to security constraints. All queries must be limited to the specified patient's data.",
                    patient_id=request.patient_id,
                    query_type=QueryType.UNDETERMINED,
                    sources=None
                )
        elif settings.QUERY_HANDLER_TYPE == "vanna":
            print("Using Vanna Handler")
            vanna_handler: VannaHandler = get_vanna_handler() # Get Vanna handler instance
            try:
                # VannaHandler.get_response now returns (nl_answer, sql_query)
                nl_answer_str, sql_query_str = await vanna_handler.get_response(
                    natural_language_query=request.query,
                    patient_id=request.patient_id
                )
            except PermissionError as e:
                # Handle security violations by returning a safe error message
                return ChatResponse(
                    answer="I'm sorry, but I cannot process this request due to security constraints. All queries must be limited to the specified patient's data.",
                    patient_id=request.patient_id,
                    query_type=QueryType.UNDETERMINED,
                    sources=None
                )
        else:
            raise HTTPException(status_code=500, detail=f"Invalid QUERY_HANDLER_TYPE: {settings.QUERY_HANDLER_TYPE}")

        response_query_type = QueryType.COMPLEX if sql_query_str else QueryType.UNDETERMINED 

        print(f"Handler ({settings.QUERY_HANDLER_TYPE}) SQL Query: {sql_query_str}")
        print(f"Handler ({settings.QUERY_HANDLER_TYPE}) NL Answer: {nl_answer_str}")

        return ChatResponse(
            answer=nl_answer_str or "I couldn't find specific information to answer your question.", 
            patient_id=request.patient_id,
            query_type=response_query_type,
            sources=[{"sql_query": sql_query_str}] if sql_query_str else None
        )
    except Exception as e:
        print(f"Error processing chat request: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while processing your request")
