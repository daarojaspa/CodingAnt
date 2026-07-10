import subprocess,shlex
def what_shell():
    return 0
##i got an error calling this tool because shell=¡True and model somehow thougth  that was active 
#figure out why 
def run_in_shell(commands:str):
    """takes in the commands to run as a list and rundrundem
    giving back  standar  output , standar error and error code """
    commands=shlex.split(commands) #force the comands to be ina  list format
    process=subprocess.run(commands,text=True,capture_output=True)
    stdout=process.stdout
    returncode=process.returncode
    stderror=process.stderr
    out=f"""the standar output was {stdout},the return code {returncode}
    the standar error {stderror}"""
    return out