from langchain.callbacks.manager import CallbackManager
from langchain_core.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_community.llms import LlamaCpp
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
from langfuse.callback import CallbackHandler
import os
load_dotenv()
chat_model_path = os.getenv("MODEL_PATH")

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
# Callbacks support token-wise streaming
callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])

# Load the model with GPU support
def load_model():
    return LlamaCpp(
        model_path=chat_model_path,
        n_gpu_layers=-1,
        batch_size=64,
        n_batch=512,
        verbose=True,
        temperature=0.5,
        callback_manager=callback_manager,
        n_ctx = 2048
    )

# Run inference
llm = load_model()
prompt = PromptTemplate.from_template("{input_text}")
chain = prompt | llm
response = chain.invoke(input={"input_text": "What is the capital of France?"}, config={"callbacks": [langfuse_handler]})
#response = chain.invoke(input={"input_text": "What is the capital of France?"})
print(response)
