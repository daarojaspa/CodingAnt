## CONSTITUTION
1. Language & deps: Python 3.11+, standard library + the official 
   Anthropic SDK only. No agent frameworks (LangChain, etc.). 
   Rationale: the point is to learn the primitives.

2. Architecture: a single explicit agent loop. Every step 
   (model call, tool call, tool result) is visible and traceable 
   in the code — no hidden abstraction.

3. Tools: start with exactly three — read_file, write_file, 
   run_bash. Each tool validates its input before acting.

4. Safety: run_bash never executes without the change being 
   shown first. No writes outside the project directory.

5. Errors: every tool returns a structured result the model can 
   read on failure — never crash the loop on a bad tool call.

6. Testing: each tool has a unit test before it's wired into 
   the loop.

7. Simplicity: prefer the most obvious implementation. If a 
   feature needs a new dependency, it needs a written reason.
