import os
from summarize import summerize_user_prompt
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from llama_cpp import Llama
from llama_cpp import LlamaTokenizer

# Load environment variables from .env file
load_dotenv()

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
    user_prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=False)

# Create the table if it doesn't exist
Base.metadata.create_all(bind=engine)

MODEL_PATH = os.getenv('MODEL_PATH')

# Initialize llama.cpp model
llama_model = Llama(model_path=MODEL_PATH)
#llama_model = Llama(model_path="D:/Llama_local/llama.cpp/models/Llama-3.2-1B-Instruct-Q6_K.gguf")
#D:/Llama_local/llama.cpp/models/gemma-1.1-7b-it.Q4_K_M.gguf
#    

# Initialize the tokenizer
tokenizer = LlamaTokenizer(llama_model)

# Define model role
MODEL_ROLE = "You are Meta AI, a friendly AI Assistant. Your responses must be helpful, informative, and keeping it concise. You can perform various tasks such as: answering questions, translation, summarization. You are incapable of: making phone calls, sending emails, or accessing personal information, user data, real-time information or current events You must aim to convey a friendly, helpful, and informative tone in your responses. Be approachable, engaging, and professional. Make sure to keep the answer less than 40 words and 2 sentences.."

# Define system prompt
# Remove <|begin_of_text|>
# RuntimeWarning: Detected duplicate leading "<|begin_of_text|>" in prompt, this will likely reduce response quality, consider removing it...
#  warnings.warn(
SYSTEM_PROMPT = f"<|start_header_id|>system<|end_header_id|>\n\n{MODEL_ROLE}<|eot_id|>"

# Define request and response Models
class PromptRequest(BaseModel):
    session_id: str
    user_prompt: str
    
class BotResponse(BaseModel):
    session_id: str
    user_prompt: str
    response: str
    context: Optional[List[str]] = None

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
    return [f"<|start_header_id|>user<|end_header_id|>\n\n{chat.user_prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n{chat.response}<|eot_id|>" for chat in reversed(chatbox)]

# Helper function to truncate the context to fit so that the total number of tokens (system prompt + context + user prompt) does not exceed the max_tokens limit.
def truncate_context(system_prompt: str, user_prompt: str, context: List[str], max_tokens: int) -> List[str]:
    # Calculate the total tokens in the full prompt
    full_prompt = f"{system_prompt}{context}{user_prompt}"
    token_count = len(tokenizer.encode(full_prompt, False))
    #print(token_count)
    
    # If the total tokens exceed the max, start removing older context
    while token_count > max_tokens:
        # Remove the oldest element of the list (context)
        context.pop(0)
        full_prompt = f"{system_prompt}{context}{user_prompt}"
        token_count = len(tokenizer.encode(full_prompt, False))
    
    return context

# POST method to generate a response from the model
@app.post("/generate-response", response_model=BotResponse)
async def generate_response(prompt_request: PromptRequest):
    db_session = SessionLocal()
    try:
        # Define user prompt
        USER_PROMPT = f"<|start_header_id|>user<|end_header_id|>\n\n{prompt_request.user_prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"
        
        # Retrieve previous context (if any in List[str]) for the session
        context = get_conversation_context(db_session, prompt_request.session_id)
        print("Pre User token: ", len(tokenizer.encode(USER_PROMPT, False)))
        
        # Summerize the user prompt if it is too long
        if len(tokenizer.encode(f"{USER_PROMPT}", False)) > 64:
            prompt_request.user_prompt = summerize_user_prompt(prompt_request.user_prompt)
            NEW_USER_PROMPT = f"<|start_header_id|>user<|end_header_id|>\n\n{prompt_request.user_prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"
            print("Post User token: ", len(tokenizer.encode(NEW_USER_PROMPT, False)))
            print("Context token: ", len(tokenizer.encode(f"{context}", False)))
            print("system token: ", len(tokenizer.encode(SYSTEM_PROMPT, False)))
            print("Tokens: ", len(tokenizer.encode(f"{SYSTEM_PROMPT}{context}{NEW_USER_PROMPT}", False)))
        
        print("User Prompt: ", prompt_request.user_prompt)
        # Truncate the context to ensure it fits within the token limit
        #context = truncate_context(SYSTEM_PROMPT, USER_PROMPT, context, 512)
        
        # Combine system prompt with user 
        full_prompt = f"{SYSTEM_PROMPT}{context}{NEW_USER_PROMPT}"
        #
        #<|begin_of_text|><|start_header_id|>system<|end_header_id|>
        #
        #{SYSTEM_PROMPT}<|eot_id|>{CONTEXT AKA HISTORY OR SOMETHING LIKE THAT}<|start_header_id|>user<|end_header_id|>
        #
        #{prompt_request.user_prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
        #
        #AKA:
        #full_prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{SYSTEM_PROMPT}<|eot_id|>{context}<|start_header_id|>user<|end_header_id|>\n\n{prompt_request.user_prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"
        #
        #(OLD VER)full_prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{SYSTEM_PROMPT}<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{prompt_request.user_prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"
        #(OLD VER)full_prompt = f"{SYSTEM_PROMPT}\n\nUser: {prompt_request.user_prompt}\nBot:"
        print("Full prompt: ", full_prompt)
        #
        print("Tokens: ", len(tokenizer.encode(full_prompt, False)))

        # Generate the response using llama.cpp model with appropriate parameters
        Response = llama_model(
            prompt=full_prompt,
            max_tokens=32,       # The number of tokens to generate in the response, -1 for unlimited
            temperature=0.5,      # The temperature for randomness, lower values are more deterministic
            top_p=0.5            # The nucleus sampling probability
        )

        # Extract the generated response
        bot_answer = Response["choices"][0]["text"].strip()
        
        # Save the conversation in the database
        with SessionLocal() as db_session:
            new_chat = Chatbox(
                session_id=prompt_request.session_id,
                user_prompt=prompt_request.user_prompt,
                response=bot_answer
            )
            db_session.add(new_chat)
            db_session.commit()
        
        # Return the model's response
        return BotResponse(
            session_id=prompt_request.session_id,
            user_prompt=prompt_request.user_prompt,
            response=bot_answer,
            context=context
        )
    
    except Exception as e:
        # General exception handling for unexpected errors
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()

# GET method to retrieve conversation history
@app.get("/history/{session_id}", response_model=List[BotResponse])
def get_conversation_history(session_id: str):
    db_session = SessionLocal()
    try:
        chatbox = db_session.query(Chatbox).filter(Chatbox.session_id == session_id).all()
        return [
            BotResponse(
                session_id=chat.session_id,
                user_prompt=chat.user_prompt,
                response=chat.response,
                context=[]
            )
            for chat in chatbox
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()

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
        content={"detail": "Invalid request format. The content must be a JSON object with 2 keys: 'session_id' and 'user_prompt'."},
    )
