tools_schema= [
    { "type": "function", "name": "read_file",
	 "description": "it recives a file path returns in one string all the lines in the file" },
    { "type": "function", "name": "write_file",
	 "description": """"it recives the file path and the content it should go 
    in it and overwrites the file , is the lazy option to edit one file , i think les tokens are need it
     just  be aware the path is right """
    " },
    { "type": "function", "name": "run_in_shell",
	 "description": """"takes in the commands to run as a string  and run them
    giving back  standar  output , standar error and error code """
    " }
  ]
