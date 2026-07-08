from dotenv import load_dotenv
from tools import schema
import os

from openai import OpenAI

print(repr(os.getenv("OPENAI_API_KEY")))
load_dotenv()
client = OpenAI()

context = []
context.append({"role":"developer","content":"you are a helpful tech developer asistant"})
while True:
    text = input("you: ")
    if text.lower() == "exit":
        break
    context.append({"role": "user", "content": text})

    response = client.chat.completions.create(
        model="gpt-5.4-mini",              
        messages=context
        tools=schema.tools_schema
    )

    reply = response.choices[0].message.content
    print(reply)
    context.append({"role": "assistant", "content": reply})

def user_compression():
    """this function is called when the user writes exit to give  a short inform 
    of what the user try to asked to the LLM in this session  befor closing the loop using a dict  comprenhention  """    
    pass
