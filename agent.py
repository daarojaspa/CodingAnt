from dotenv import load_dotenv
import json
import subprocess          # <-- was missing; your except referenced it
from tools import schema
import os
from openai import OpenAI
from tools.files import read_file, write_file
from tools.shell import run_in_shell

DISPATCH = {
    "read_file": read_file,
    "write_file": write_file,
    "run_in_shell": run_in_shell,
}

load_dotenv()              # <-- MOVED above the getenv print; it did nothing after
client = OpenAI()

# Responses API keeps history as a list of "input items", not chat messages
context = [
    {"role": "developer", "content": "you are a helpful tech developer asistant"}
]

while True:
    text = input("you: ")
    if text.lower() == "exit":
        break
    context.append({"role": "user", "content": text})

    while True:
        response = client.responses.create(
            model="gpt-5-nano",         # confirm an ID your key can call
            input=context,                 # 'input', not 'messages'
            tools=schema.tools_schema
        )

        # Append everything the model emitted (reasoning, text, tool calls)
        # straight back into context. No hand-rebuilding = no null bug.
        context += response.output

        tool_calls = [item for item in response.output
                      if item.type == "function_call"]
##insted of iterating  in the original object  it created  a object with the toolcalls to iterate it
        if tool_calls:
            for call in tool_calls:
                name = call.name
                args = json.loads(call.arguments)
                try:
                    result = DISPATCH[name](**args)
                except subprocess.TimeoutExpired:
                    result = "Error timeout"
                    #this because subprocess can hang  and never sais anithing
                except Exception as e:
                    result = f"Error: {type(e).__name__}: {e}"   # <-- was missing 'result ='
                context.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": str(result)
                })
        else:
            print(f"coding ant: {response.output_text}")
            break