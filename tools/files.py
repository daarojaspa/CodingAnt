import os
"""The paths are relative to the folder  where the agent runs """
def write_file(path, content):
    """overwrites the file , is the lazy option to edit one file , i think les tokens are need it
     just  be aware the path is right """
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)


def read_file(path):
    """returns in one string all the lines in the file"""
    with open(path,'r') as f:
        content =f.read()
    return content