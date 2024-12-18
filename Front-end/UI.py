import langchain
import importlib.util
from async_tkinter_loop import async_handler, async_mainloop
from tkinter import *

langchain.debug = True

module_path = "/shared/modules.py"

# Load the modules
spec = importlib.util.spec_from_file_location("modules", module_path)
modules = importlib.util.module_from_spec(spec)
spec.loader.exec_module(modules)

# Create the main window
main_window = Tk()
main_window.title("Meta AI")
main_window.geometry("900x700")

# Create an input field
input = Entry(main_window, width=100, borderwidth=5)
input.grid(row=0, column=0)

# Funtion for button to run the model
async def generate():
    input_text = input.get()
    prompt_request = modules.Request(session_id="222", request=input_text)
    response = await modules.generate_response(prompt_request)
    print("Response: ", response.response)
    print("Summary: ", response.summarized_response)
    output.delete(1.0, END)
    output.insert(END, response.response)
    if response.summarized_response:
        summarize_output.delete(1.0, END)
        summarize_output.insert(END, response.summarized_response)
    else:
        summarize_output.delete(1.0, END)
        summarize_output.insert(END, "No summary available")

# Function to delete a conversation
def Delete():
    ans = modules.delete("222")
    output.delete(1.0, END)
    output.insert(END, f"Deleted: {ans}")

# Function to get the number of conversations
def Get_num_conversations():
    num = modules.get_num_history("222")
    output.delete(1.0, END)
    output.insert(END, f"Number of conversations: {num}")

# Create buttons
runButton = Button(main_window, text="Run", command=async_handler(generate), padx=50, pady=20)
runButton.grid(row=2, column=0)

deleteButton = Button(main_window, text="Delete", command=lambda:Delete(), padx=50, pady=20)
deleteButton.grid(row=8, column=0)

get_num_conversations = Button(main_window, text="Get number of conversations", command=lambda:Get_num_conversations(), padx=50, pady=20)
get_num_conversations.grid(row=10, column=0)

# Create output field
output = Text(main_window, height=10, width=100, borderwidth=5, wrap=WORD, xscrollcommand=True, yscrollcommand=True)
output.insert(END, "Output")
output.grid(row=4, column=0)

# Create summarize output field
summarize_output = Text(main_window, height=10, width=100, borderwidth=5, wrap=WORD, xscrollcommand=True, yscrollcommand=True)
summarize_output.insert(END, "Summary")
summarize_output.grid(row=6, column=0)

# Run the main loop
async_mainloop(main_window)