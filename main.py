from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, constr
from llama_cpp import Llama

app = FastAPI()

# Initialize llama.cpp model
llama_model = Llama(model_path="models/Llama-3.2-1B-Instruct-Q6_K.gguf")
#D:/Llama_local/llama.cpp/models/gemma-1.1-7b-it.Q4_K_M.gguf
#    
#    

# Define a system prompt
SYSTEM_PROMPT = "You are Meta AI, a friendly AI Assistant. Today's date is Friday, October 18, 2024. Respond to the input as a friendly AI assistant, generating human-like text, and follow the instructions in the input if applicable. Keep the response concise and engaging, using Markdown when appropriate. The user live in VietNam, so be aware of the local context and preferences. Use a conversational tone and provide helpful and informative responses, utilizing external knowledge when necessary."

# Request body model with input validation
class PromptRequest(BaseModel):
    user_prompt: constr(min_length=1, max_length=500)  # User prompt must be between 1 and 500 characters

@app.post("/generate-response")
async def generate_response(prompt_request: PromptRequest):
    try:
        # Combine system prompt with user 
        full_prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{SYSTEM_PROMPT}<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{prompt_request.user_prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"
        #<|begin_of_text|><|start_header_id|>system<|end_header_id|>
        #
        #{SYSTEM_PROMPT}<|eot_id|><|start_header_id|>user<|end_header_id|>
        #
        #{prompt_request.user_prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
        #
        #
        #full_prompt = f"{SYSTEM_PROMPT}\n\nUser: {prompt_request.user_prompt}\nBot:"



        # Generate the response using llama.cpp model with appropriate parameters
        response = llama_model(
            prompt=full_prompt,
            max_tokens=-1,       # The number of tokens to generate in the response, -1 for unlimited
            temperature=0.4,      # The temperature for randomness, lower values are more deterministic
            top_p=0.5,            # The nucleus sampling probability
            stop=["User:", "Bot:"]  # Stop tokens to prevent overly long responses
        )

        # Extract the generated response
        bot_answer = response["choices"][0]["text"].strip()

        # Return the model's response
        return {"response": bot_answer}
    
    except Exception as e:
        # General exception handling for unexpected errors
        raise HTTPException(status_code=500, detail="An error occurred while processing the request")

# Exception handler for invalid request format
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": "Invalid request format. The content must be a JSON object with a 'user_prompt' key."},
    )