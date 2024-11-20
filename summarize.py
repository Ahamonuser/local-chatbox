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

# Define model roles
MODEL_ROLE_SUM_INPUT = """You are a expert at summarizing. \
Prohibit to answer the question. \
If the user input contains a question, summarize the question and return it in the form of a question; do not return a statement or an answer. \
The response must be a short paragraph, under 50 words. \
"""

MODEL_ROLE_SUM_OUTPUT = """You are a expert at summarizing. \
Do not return the summary in the form of a question; you must return a statement or an answer. \
The response must be a short paragraph, under 50 words. \
"""

# Define system prompts
# Remove <|begin_of_text|>
# RuntimeWarning: Detected duplicate leading "<|begin_of_text|>" in prompt, this will likely reduce response quality, consider removing it...
#  warnings.warn(
SYSTEM_PROMPT_INPUT = f"<|start_header_id|>system<|end_header_id|>\n\n{MODEL_ROLE_SUM_INPUT}<|eot_id|>"
SYSTEM_PROMPT_OUTPUT = f"<|start_header_id|>system<|end_header_id|>\n\n{MODEL_ROLE_SUM_OUTPUT}<|eot_id|>"

# Get the summary of the text
def summarize(text_input: str, mode: str) -> str:
    USER_PROMPT = f"""<|start_header_id|>user<|end_header_id|>\n\nSummarizing the following text: {text_input}<|eot_id|><|start_header_id|>assistant<|end_header_id|> \nSummary:\n"""
    llm=LlamaCpp(
        model_path=summarize_model_path,
        temperature=0.1
    )
    # Define summarize prompt
    if mode == "input":
        summarize_prompt = PromptTemplate.from_template(f"{SYSTEM_PROMPT_INPUT}""{input_text}")
    elif mode == "output":
        summarize_prompt = PromptTemplate.from_template(f"{SYSTEM_PROMPT_OUTPUT}""{input_text}")
    chain = summarize_prompt | llm
    summary = chain.invoke(input={"input_text": USER_PROMPT})
    return summary