import os
from summarize import summarize
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Text, desc
from sqlalchemy.orm import sessionmaker, declarative_base
from llama_cpp import Llama, LlamaTokenizer

# Load environment variables from .env file
load_dotenv()

# SQLite database setup using SQLAlchemy
DATABASE_URL = "sqlite:///./idea_generator.db"
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
llama_model = Llama(model_path=chat_model_path, n_ctx=2048)

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

# Helper function to retrieve context from the database
def get_conversation_context(db_session, session_id: str) -> List[str]:
    chatbox = db_session.query(Chatbox).filter(Chatbox.session_id == session_id).order_by(desc(Chatbox.id)).limit(5).all()
    for chat in chatbox:
        if chat.summarized_response != None:
            chat.response = chat.summarized_response
            
    return [f"<|start_header_id|>user<|end_header_id|>\n\n{chat.request}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n{chat.response}<|eot_id|>" for chat in reversed(chatbox)]

# Generate a response from the model
async def generate_response(request: Request):
    db_session = SessionLocal()
    try:
        # Define user prompt
        USER_PROMPT = f"<|start_header_id|>user<|end_header_id|>\n\n{request.request}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"
        
        # Retrieve previous context (if any in List[str]) for the session
        context = get_conversation_context(db_session, request.session_id)
        
        # Summarize the user prompt if it is too long
        if len(tokenizer.encode(f"{USER_PROMPT}", False)) > 128:
            request.request = summarize(request.request, "input")
            NEW_USER_PROMPT = f"<|start_header_id|>user<|end_header_id|>\n\n{request.request}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"
            full_prompt = f"{SYSTEM_PROMPT}{context}{NEW_USER_PROMPT}"
        else:
            full_prompt = f"{SYSTEM_PROMPT}{context}{USER_PROMPT}"
        Bot_Response = llama_model(
            prompt=full_prompt,
            max_tokens=-1,       # The number of tokens to generate in the response, -1 for unlimited
            temperature=0.5,      # The temperature for randomness, lower values are more deterministic
            top_p=0.5            # The nucleus sampling probability
        )
        
        # Extract the generated response
        bot_answer = Bot_Response["choices"][0]["text"].strip()
        
        # Summarize the response if it is too long
        if len(tokenizer.encode(f"{bot_answer}", False)) > 128:
            summarized_bot_answer = summarize(bot_answer, "output")
            
            # Save the conversation in the database
            with SessionLocal() as db_session:
                new_chat = Chatbox(
                    session_id=request.session_id,
                    request=request.request,
                    response=bot_answer,
                    summarized_response=summarized_bot_answer
                )
                db_session.add(new_chat)
                db_session.commit()
            
            # Return the model's response
            return Response(
                session_id=request.session_id,
                request=request.request,
                response=bot_answer,
                summarized_response=summarized_bot_answer,
                context=context
            )
            
        else:
            # Save the conversation in the database
            with SessionLocal() as db_session:
                new_chat = Chatbox(
                    session_id=request.session_id,
                    request=request.request,
                    response=bot_answer,
                    summarized_response=None
                )
                db_session.add(new_chat)
                db_session.commit()
            
            # Return the model's response
            return Response(
                session_id=request.session_id,
                request=request.request,
                response=bot_answer,
                context=context
            )
    
    except Exception as e:
        print(e)
    finally:
        db_session.close()

# Retrieve number of conversations in history
def get_num_history(session_id: str) -> int:
    db_session = SessionLocal()
    try:
        chatbox = db_session.query(Chatbox).filter(Chatbox.session_id == session_id).all()
        return len(chatbox)
    
    except Exception as e:
        print(e)
    finally:
        db_session.close()

# Delete all conversations
def delete(session_id: str) -> str:
    db_session = SessionLocal()
    try:
        # Delete all conversations associated with the given session id
        deleted_rows = db_session.query(Chatbox).filter(Chatbox.session_id == session_id).delete()

        # Commit the transaction to make the change persistent
        db_session.commit()

        if deleted_rows == 0:
            return "No conversations found for the given session_id"
        else:
            return {"message": f"Deleted {deleted_rows} conversation(s) for session_id: {session_id}"}

    except Exception as e:
        db_session.rollback()
        print(e)
    finally:
        db_session.close()
