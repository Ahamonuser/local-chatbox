from langchain_community.chat_models import ChatLlamaCpp
from langchain_core.prompts import ChatPromptTemplate




summerize_model = "D:/Llama_local/llama.cpp/models/Hermes-2-Pro-Llama-3-8B-Q6_K.gguf"
#systemprompt = """You are a friendly AI Assistant. Your answer must be only in 1 sentence. \
#he output must be in a manner that a 5 year old would understand. \
#You must write summary of the following:\n\n{input_text}."""
systemprompt = """You are a expert at summarizing. Your task is summarizing user input delimited by triple backquotes.  \
The output must be in a manner that a 5 year old would understand. \
Prohibit to answer the question, return the summary only.
```user input: {input_text}```
"""
summerize_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            systemprompt
        )
    ]
)
#"You are a friendly AI Assistant. Your answer must be less than 30 words. The output must be in a manner that a 5 year old would understand. You must write summary of the following:\n\n{input_text}."



def summerize_user_prompt(user_prompt: str) -> str:
    # Get the summary of the user prompt
    llm=ChatLlamaCpp(
        model_path=summerize_model,
        temperature=0.7,
        #stop=["\n", "."],
        top_p=0.5)
    chain = summerize_prompt | llm
    summary = chain.invoke(input={"input_text": user_prompt}).content
    print("Summary: ", summary)
    return summary
