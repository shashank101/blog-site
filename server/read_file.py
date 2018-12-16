def retrieve_home_page():
	fread = open('./templates/home.html', 'r')
	output = ""
	body_flag = False
	script_flag = False
	nav_flag = False
	for line in fread:
		if line.strip().startswith("<body"):
			body_flag = True
		elif line.strip().startswith("</body"):
			body_flag = False
		if body_flag == True:
			
			output += line
#			if line.strip().startswith("<script"):
#				script_flag = True
			
#			if line.strip().endswith("</script"):
#				script_flag = False
			
#			elif line.strip().startswith("</script"):
#				script_flag = False
			
#			if line.strip().startswith("<nav"):
#				nav_flag = True
			
#			if line.strip().endswith("</nav"):
#				nav_flag = False
			
#			elif line.strip().startswith("</nav"):
#				nav_flag = False
			
#			elif script_flag == False and nav_flag == False:
#				output += line + "\n"
	print(output)
	fread.close()
	return output
	

def retrieve_no_body():
	fread = open('./templates/home.html', 'r')
	output = ""
	for line in fread:
		if line.strip().startswith("<body"):
			break
		output +=line
		
	for line in fread:
		output += "\n\n\nThis is getting printed now\n\n\n"
		output += line
		break
	
	print(output)

retrieve_no_body()
#retrieve_home_page()
