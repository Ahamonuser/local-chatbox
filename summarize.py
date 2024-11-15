import os
from dotenv import load_dotenv
from langchain_community.llms import LlamaCpp
from langchain_core.prompts import PromptTemplate
import langchain
langchain.debug = True

# Load environment variables from .env file
load_dotenv()

# Get summarize model path
summarize_model_path = os.getenv("MODEL_PATH")

# Define model role
MODEL_ROLE = """You are a expert at summarizing. \
Prohibit to answer the question. \
If the user input contains a question, summarize the question and return it in the form of a question; do not return a statement or an answer. \
The answer must be a short paragraph, under 50 words. \
"""

# Define system prompt
# Remove <|begin_of_text|>
# RuntimeWarning: Detected duplicate leading "<|begin_of_text|>" in prompt, this will likely reduce response quality, consider removing it...
#  warnings.warn(
SYSTEM_PROMPT = f"<|start_header_id|>system<|end_header_id|>\n\n{MODEL_ROLE}<|eot_id|>"

# Define summarize prompt
summarize_prompt = PromptTemplate.from_template(f"{SYSTEM_PROMPT}""{input_text}")

# Get the summary of the user input
def summerize_user_prompt(user_prompt: str) -> str:
    USER_PROMPT = f"""<|start_header_id|>user<|end_header_id|>\n\nSummarizing the following text: {user_prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|> \nSummary:\n"""
    llm=LlamaCpp(
        model_path=summarize_model_path,
        temperature=0.1
    )
    chain = summarize_prompt | llm
    summary = chain.invoke(input={"input_text": USER_PROMPT})
    return summary