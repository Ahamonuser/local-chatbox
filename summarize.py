import os
from dotenv import load_dotenv
from langchain_community.chat_models import ChatLlamaCpp
from langchain_core.prompts import ChatPromptTemplate

# Load environment variables from .env file
load_dotenv()

SUMMARIZE_MODEL = os.getenv('SUMMARIZE_MODEL_PATH')

summerize_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a friendly AI Assistant. Your answer must be less than 30 word. The output must be in a manner that a 5 year old would understand. You must write a concise summary of the following:\n\n{input_text}."
        )
    ]
)

def summerize_user_prompt(user_prompt: str) -> str:
    # Get the summary of the user prompt
    llm=ChatLlamaCpp(
        model_path=SUMMARIZE_MODEL,
        temperature=0,
        stop=["\n", "."],
        top_p=0.5)
    chain = summerize_prompt | llm
    summary = chain.invoke(input={"input_text": user_prompt}).content
    print("Summary: ", summary)
    return summary
