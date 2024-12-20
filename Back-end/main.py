import os
from summarize import summarize
from validation import validate
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Text, desc
from sqlalchemy.orm import sessionmaker, declarative_base
from llama_cpp import Llama, LlamaTokenizer
from langfuse.decorators import langfuse_context, observe
import langchain

langchain.debug = True

# Load environment variables from .env file
load_dotenv()

# Get Langfuse environment variables
Secret_Key = os.getenv("LANGFUSE_SECRET_KEY")
Public_Key = os.getenv("LANGFUSE_PUBLIC_KEY")
Host = os.getenv("LANGFUSE_HOST")

langfuse_context.configure(
    secret_key=Secret_Key,
    public_key=Public_Key,
    host=Host
)

# Define the FastAPI app
app = FastAPI()

# SQLite database setup using SQLAlchemy
DATABASE_URL = "sqlite:///./chatbox.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Conversation Model for the database
class Chatbox(Base):
    __tablename__ = "chatbox"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    request = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    summarized_response = Column(Text, nullable=True)

# Create the table if it doesn't exist
Base.metadata.create_all(bind=engine)

# Initialize llama.cpp model
chat_model_path = os.getenv("MODEL_PATH")


llama_model = Llama(model_path=chat_model_path,
                    n_ctx=2048,
                    n_batch=512,
                    n_gpu_layers=-1,)

# Initialize the tokenizer
tokenizer = LlamaTokenizer(llama_model)

# Define model role
MODEL_ROLE = """You are an IoT project idea generator specializing in providing creative, practical, and achievable DIY IoT project ideas. \
Give your suggestions based on the user's interests, experience level, available tools, and desired platforms (e.g., Raspberry Pi, Arduino, ESP32). \
You must include a brief project description, a list of components, and potential use cases. \
The ideas must be innovative, educational, or solve real-world problems. \
You must be friendly, engaging, clear, and informative.
"""

# Define system prompt
# Remove <|begin_of_text|>
# RuntimeWarning: Detected duplicate leading "<|begin_of_text|>" in prompt, this will likely reduce response quality, consider removing it...
# warnings.warn(
SYSTEM_PROMPT = f"<|start_header_id|>system<|end_header_id|>\n\n{MODEL_ROLE}<|eot_id|>"

# Define request and response Models
class Request(BaseModel):
    session_id: str
    request: str
    
class Response(BaseModel):
    session_id: str
    request: str
    response: str
    summarized_response: Optional[str] = None
    context: Optional[List[str]] = None

class Summary(BaseModel):
    request: str
    summary: str
    
class SummaryRequest(BaseModel):
    mode: str
    request: str

class NumHisCon(BaseModel):
    num_conversations: int

# Helper function to retrieve context from the database
def get_conversation_context(db_session, session_id: str) -> List[str]:
    chatbox = db_session.query(Chatbox).filter(Chatbox.session_id == session_id).order_by(desc(Chatbox.id)).limit(5).all()
    #order_by(desc(Chatbox.id)): get the rows in descending order of id (the latest row is the last one)
    #limit(5): get 5 rows
    #reversed(chatbox): reverse the order of the rows (ensere the chronological order)
    #chatbox = db_session.query(Chatbox).filter(Chatbox.session_id == session_id).all()
    # Inside of the context, we have:
    #<|start_header_id|>user<|end_header_id|>
    #
    #{User_Prompt_1}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
    #
    #{Model_Response_1}<|eot_id|><|start_header_id|>user<|end_header_id|>
    # 
    #{User_Prompt_2}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
    # 
    #{Model_Response_2}<|eot_id|><|start_header_id|>user<|end_header_id|>
    #
    #...
    #
    #{Model_Response_N-1}<|eot_id|><|start_header_id|>user<|end_header_id|>
    # 
    #{User_Prompt_N}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
    #
    #{Model_Response_N}<|eot_id|>
    #
    # Which mean: CONTEXT_PROMPT = 
    #f"<|start_header_id|>user<|end_header_id|>\n\n{User_Prompt_1}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n{Model_Response_1}<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{User_Prompt_2}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n{Model_Response_2}<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n...\n\n{Model_Response_N-1}<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{User_Prompt_N}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n{Model_Response_N}<|eot_id|>"
    # -> TOO LONG. Using loops to get data from database and put in context, we have:
    # for chat in chatbox: (get user_prompt and response at every column in the 'chatbox' table - stored in the database)
    #      CONTEXT_PROMPT += f"<|start_header_id|>user<|end_header_id|>\n\n{chat.user_prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n{chat.response}<|eot_id|>"
    #
    # if there is a summarized_response in the chatbox, we replace the response by the summarized_response
    for chat in chatbox:
        if chat.summarized_response != None:
            chat.response = chat.summarized_response
            
    return [f"<|start_header_id|>user<|end_header_id|>\n\n{chat.request}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n{chat.response}<|eot_id|>" for chat in reversed(chatbox)]

@observe()
@app.post("/summarize", response_model=Summary)
async def summarize_text(request: SummaryRequest):
    try:
        summary = summarize(request.request, request.mode)
        print(len(tokenizer.encode(summary, False)))
        return Summary(
            request=request.request,
            summary=summary
        )
    
    except Exception as e:
        # General exception handling for unexpected errors
        raise HTTPException(status_code=500, detail=str(e))

@observe()    
@app.post("/validation", response_model=Summary)
async def validate_text(request: SummaryRequest):
    try:
        answer = validate(request.request)
        #print(len(tokenizer.encode(answer, False)))
        return Summary(
            request=request.request,
            summary=answer
        )
    
    except Exception as e:
        # General exception handling for unexpected errors
        raise HTTPException(status_code=500, detail=str(e))

# POST method to generate a response from the model
@app.post("/generate-response", response_model=Response)
@observe()
async def generate_response(request: Request):
    db_session = SessionLocal()
    try:
        # Define user prompt
        USER_PROMPT = f"<|start_header_id|>user<|end_header_id|>\n\n{request.request}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"
        
        # Retrieve previous context (if any in List[str]) for the session
        context = get_conversation_context(db_session, request.session_id)
        
        # Summarize the user prompt if it is too long
        if len(tokenizer.encode(f"{USER_PROMPT}", False)) > 64:
            request.request = summarize(request.request, "input")
            NEW_USER_PROMPT = f"<|start_header_id|>user<|end_header_id|>\n\n{request.request}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"
            full_prompt = f"{SYSTEM_PROMPT}{context}{NEW_USER_PROMPT}"
        else:
            full_prompt = f"{SYSTEM_PROMPT}{context}{USER_PROMPT}"
        
        # Combine system prompt with user 
        #full_prompt = f"{SYSTEM_PROMPT}{context}{NEW_USER_PROMPT}"
        #
        #<|begin_of_text|><|start_header_id|>system<|end_header_id|>
        #
        #{SYSTEM_PROMPT}<|eot_id|>{CONTEXT AKA HISTORY OR SOMETHING LIKE THAT}<|start_header_id|>user<|end_header_id|>
        #
        #{prompt_request.user_prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
        #
        #AKA:
        #full_prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{SYSTEM_PROMPT}<|eot_id|>{context}<|start_header_id|>user<|end_header_id|>\n\n{prompt_request.user_prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"
        
        # Generate the response using llama.cpp model with appropriate parameters
        Bot_Response = llama_model(
            prompt=full_prompt,
            max_tokens=-1,       # The number of tokens to generate in the response, -1 for unlimited
            temperature=0.5,      # The temperature for randomness, lower values are more deterministic
            top_p=0.5            # The nucleus sampling probability
        )
        
        # Extract the generated response
        bot_answer = Bot_Response["choices"][0]["text"].strip()
        # Check validation of the output
        validation_result = validate(bot_answer)
        
        # If the output is not validated, return a message
        if ("Not Validated" in validation_result) and ("Validated" not in validation_result):
            print("Validation Result: ", validation_result)
            return Response(
                session_id=request.session_id,
                request=request.request,
                response="I'm sorry, but I'm unable to generate a valid response.",
                summarized_response=None,
                context=context
            )
        
        # If the output is validated, begin checking the length of the response
        else :
            print("Validation Result: ", validation_result)
            # Summarize the response if it is too long
            if len(tokenizer.encode(f"{bot_answer}", False)) > 256:
                summarized_bot_answer = summarize(bot_answer, "output")
                
                # Save the conversation in the database
                new_chat = Chatbox(
                    session_id=request.session_id,
                    request=request.request,
                    response=bot_answer,
                    summarized_response=summarized_bot_answer
                )
                db_session.add(new_chat)
                db_session.commit()
                
                # Return the model's response
                print("Summarized Response: ", summarized_bot_answer)
                return Response(
                    session_id=request.session_id,
                    request=request.request,
                    response=bot_answer,
                    summarized_response=summarized_bot_answer,
                    context=context
                )
            
            # If the response is not too long
            else:
                # Save the conversation in the database
                new_chat = Chatbox(
                    session_id=request.session_id,
                    request=request.request,
                    response=bot_answer,
                    summarized_response=None
                )
                db_session.add(new_chat)
                db_session.commit()
                
                # Return the model's response
                print("Response: ", bot_answer)
                return Response(
                    session_id=request.session_id,
                    request=request.request,
                    response=bot_answer,
                    summarized_response=None,
                    context=context
                )
    
    except Exception as e:
        print(e)
    finally:
        db_session.close()

@observe()
# GET method to retrieve conversation history
@app.get("/history/{session_id}", response_model= NumHisCon)
def get_conversation_history(session_id: str):
    db_session = SessionLocal()
    try:
        chatbox = db_session.query(Chatbox).filter(Chatbox.session_id == session_id).all()
        return NumHisCon(
            num_conversations=len(chatbox)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()

@observe()
# DELETE method to delete conversation history
@app.delete("/delete-history/{session_id}")
def delete_context(session_id: str):
    db_session = SessionLocal()
    try:
        # Delete all conversations associated with the given session id
        deleted_rows = db_session.query(Chatbox).filter(Chatbox.session_id == session_id).delete()

        # Commit the transaction to make the change persistent
        db_session.commit()

        if deleted_rows == 0:
            raise HTTPException(status_code=404, detail="No conversations found for the given session_id")
        
        return {"message": f"Deleted {deleted_rows} conversation(s) for session_id: {session_id}"}

    except Exception as e:
        db_session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()

# Exception handler for invalid request format
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": "Invalid request format. Please check the request body."}
    )
    
#
#"""
#        return [
#            Response(
#                session_id=chat.session_id,
#                user_prompt=chat.user_prompt,
#                response=chat.response,
#                summarized_response=chat.summarized_response,
#                context=[]
#            )
#            for chat in chatbox
 #       ]
  #      """