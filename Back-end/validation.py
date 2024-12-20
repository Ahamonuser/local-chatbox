import os
from dotenv import load_dotenv
from langchain_community.llms import LlamaCpp
from langchain_core.prompts import PromptTemplate
from langfuse.callback import CallbackHandler
import langchain
langchain.debug = True

# Load environment variables from .env file
load_dotenv()

# Get validate model path
validate_model_path = os.getenv("MODEL_PATH")

# Get Langfuse environment variables
Secret_Key = os.getenv("LANGFUSE_SECRET_KEY")
Public_Key = os.getenv("LANGFUSE_PUBLIC_KEY")
Host = os.getenv("LANGFUSE_HOST")

# Initialize Langfuse
langfuse_handler = CallbackHandler(
    secret_key=Secret_Key,
    public_key=Public_Key,
    host=Host
)

# Define model roles
MODEL_ROLE = """You are a expert at validating technical answers and solutions related to IoT DIY projects. \
Make sure user iput is technically accurate, feasible, and align with best practices for IoT development \
If the input has any keywords that is not related to IoT, return 'Not Validated'. \
If the user input related to IoT DIY projects, return only in format 'Validated'. If not, return only in format 'Not Validated' \
Return only in 'Validated' or 'Not Validated' format, no further explanation. \
Do not return a statement or a question. \
Do not return any other information than 'Validated' or 'Not Validated'. \
"""

# Define system prompts
# Remove <|begin_of_text|>
# RuntimeWarning: Detected duplicate leading "<|begin_of_text|>" in prompt, this will likely reduce response quality, consider removing it...
#  warnings.warn(
SYSTEM_PROMPT = f"<|start_header_id|>system<|end_header_id|>\n\n{MODEL_ROLE}<|eot_id|>"

# Check validation of the text
def validate(text_input: str) -> str:
    USER_PROMPT = f"""<|start_header_id|>user<|end_header_id|>\n\nValidating the following text: {text_input}<|eot_id|><|start_header_id|>assistant<|end_header_id|> \Validation Result:\n"""
    llm=LlamaCpp(
        model_path=validate_model_path,
        temperature=0.1,
        n_ctx = 2048
    )
    
    # Define validate prompt
    validate_prompt = PromptTemplate.from_template(f"{SYSTEM_PROMPT}""{input_text}")
    chain = validate_prompt | llm
    result = chain.invoke(input={"input_text": USER_PROMPT}, config={"callbacks": [langfuse_handler]})
    return result