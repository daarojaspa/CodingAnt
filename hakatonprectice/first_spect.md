p1: raw agent  + 3 basic  tools 
## What
a multiturn loop  where  the user interacts with the agent in the console ,  when is the agent turn  it most evaluate if it requires  any tool , if so  it needs to call it .  it will have 3 tools  on hand:
- read_file:A a python script that takes in  the file that most be read looks for it in the specify path if given or from the root where the agent was executed and charge it in to the context of the conversation
- write_file:a python script that allows the  agent to write and output in a specific location with an spesific name 
- run_bash: a python or bash script that enables the running of arbitrary shell commands  in to the console where the conversation is stablish. 
It has to have an explicit  stop conditions: 
- number of retryes: A failed tool calling or a failed  api call most be retwey abounded number of times in a geometric back of pattern. never keep looping indefinitly.
- a token budged: 6000 tokens  max per answer.
- max iteretions on the loop : Cant  iterate more than 10  times whith out giving an answer 

## why 
    The agent needs to failed gracefully,   the idea is that this phase of the basic tool calling loop inside the  main loop is robust .
## out of scope 
    - memory  between sessions. 
    -orchestration of a number of models or sub agents 
    - the  agent cant  edit or run  files outside of the folder where is runned.
## acceptance critiria 
- told to create a console  program that  asks for a  number a and a base b to calculate the log b of a.  creates a log.py file that acomplish the task .
-told to modify a file log.py to expand its capabilities to also  calculate  exponencial  of a b times, reads   re writtes and runs the file to  see if the new  feature is working   
-run_bash executes arbitrary shell commands, but only within the project directory, and is subject to the constitution's prohibitions and consent gates (rules 6–7). Commands that would act outside the project root are refused
- • When a tool raises an error mid-run, the agent recovers, or halts cleanly with a stated reason — it never spins. (isolates: failure handling)
• The agent always terminates within its max-iteration cap. (isolates: termination)
- when a call to the apior tool  fails it should output the number of retries and the time it wait it between each retry befor stoping.