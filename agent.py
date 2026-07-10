from dotenv import load_dotenv
import json 
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
print(repr(os.getenv("OPENAI_API_KEY")))
load_dotenv()
client = OpenAI()

context = []
context.append({"role":"developer","content":"you are a helpful tech developer asistant"})
while True:
#your turn
    text = input("you: ")
    if text.lower() == "exit":
        break
    context.append({"role": "user", "content": text})
#agents turn?
    while True:
        response = client.chat.completions.create(
            model="gpt-5.4-mini",              
            messages=context,
            tools=schema.tools_schema
        )

        reply = response.choices[0].message
        context.append({"role": "assistant", "content": reply.content})
        if reply.tool_calls:
            for call in reply.tool_calls:
                print(f"callin tools call{call}")
                name=call.function.name
                args=json.loads(call.function.arguments)
                try:
                    result=DISPATCH [name](**args)
                except subprocess.TimeoutExpired:
                    result="Error timeout"
                except Exception as e :
                    f"Error:{type(e).__name__}:{e}"
                context.append({"role":"tool","tool_call_id":call.id,"content":str(result)})
        else:        
            print(f"coding ant :{reply.content}")
            break

def user_compression():
    """this function is called when the user writes exit to give  a short inform 
    of what the user try to asked to the LLM in this session  befor closing the loop using a dict  comprenhention  """    
    pass
