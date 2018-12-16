#!/usr/bin/python3

from flask import Flask, request, jsonify, render_template, session, redirect, url_for, g
from flask_recaptcha import ReCaptcha
from validate_email import validate_email
import json
import mysql.connector
import random
import hashlib
import jwt
import datetime
import smtplib
import sys
import re
import requests
import subprocess
import getpass
import os

# These are the initial configurations
app = Flask(__name__)
recaptcha = ReCaptcha(app=app)
app.secret_key = os.urandom(128) #This generates a random alphanumeric characters of length 128. This is used as a secret key for the session
app.config['SALT'] = '8391JSDKjskajjfgajsO@91@!*>/' #This is the salt that is used to combine with the password adding another layer of security in the application

# This is a list of characters that will be used to generate a random password in generate_new_password function
LIST_OF_CHARACTERS = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
                      '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '@', '.', '_', '!', '(', ')', '-', '+', '*', '^',
                      'A', 'B', 'C', 'D','E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']


# This is a function to create a connection with MYSQL.
# Note: MYSQL Server should be running else this will fail
def create_connection():
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='authenticator',
            password='!@#Thisistheauthenticator123',
            database='blog')
        return conn
	
# MYSQL COnnection Error will be handled here
    except mysql.connector.Error as e:
        print(e)
    return None

# Support is an email where all the feedback from the users will be sent.
# This function connects to the database and retrieves the email and password of the support team.
# @return This returns the email and password pf support
def support_email():
	try:
		conn = create_connection() # Create a connection with the database
		cur = conn.cursor() #Create a cursor. Each connection can have multiple cursors. Cursors will be used to fetch results from database
		cur.execute('SELECT Email_ID, Password FROM support') #Execute query in MySQL
		result = cur.fetchone() # Fetch one row from the query executed
		cur.close() #Close the cursor connection
		conn.close() #Close connection with database
		return result[0], result[1] #Return email and password of support

# If connection cannot be made, the error will be handled here	
	except mysql.connector.Error as e:
		return None

#The support's email and password are stored in variables EMAIL_ADDRESS and PASSWORD
EMAIL_ADDRESS, PASSWORD = support_email()

# This function is used to send an email to the target.
# @param email address of the target, subject of the email, message is the body of the email
def send_email(target_email, subject, message):
    try:
        server = smtplib.SMTP('smtp.gmail.com:587') #This is the SMTP server of gmail operating on port 587
        server.ehlo()
        server.starttls() #Starts a secure SSL/TLS connection
        server.login(EMAIL_ADDRESS, PASSWORD) #Login to the server using the email address and password of the support
        msg = 'Subject: {}\n\n{}' .format(subject, message) #Write the subject and body.
        server.sendmail(EMAIL_ADDRESS, target_email, msg) #Send the email to the target
        server.quit() #Close the connection with the gmail SMTP server.
    except:
        return 'Server Error', 500 #If the server cannot be connected, return a server error with error code 500


# Check if the email already exists in the database
# @param email id
# @return return True if the email exists in the database, else return False
def check_duplicate_email(email_id):
	try:
		conn = create_connection()
		cur = conn.cursor()
		cur.execute("SELECT * FROM users WHERE Email_ID = %s", (email_id,))
		rows = cur.fetchall()
		cur.close()
		conn.close()
		if len(rows)>0:
			return True
		return False

# If the connection cannot be made with MySQL, Catch the error here and return error message 503	
	except mysql.connector.errors.ProgrammingError:
		return 503

# Create new user in the database
# Password in this will be recieved in clear text To store in the database the below login will be applied
# database_password = sha512(sha512(password) + salt)

# @param user email address, password, first name, last name
# @return return code 201 if user has been inserted into database
def create_new_user(user_email, password, fName, lName):
	try:
		password = hashlib.sha512(((hashlib.sha512(password.encode('UTF-8')).hexdigest()) + app.config['SALT']).encode('UTF-8')).hexdigest() # database_password = sha512(sha512(password) + salt)
		conn = create_connection()
		cur = conn.cursor()
		cur.execute('INSERT INTO users(Email_ID, Password, FName, LName) VALUES (%s, %s, %s, %s)', (user_email, password, fName, lName))
		conn.commit() 
		cur.close()
		conn.close()
		return 'Insert Operation Successful', 201
		
	except mysql.connector.errors.ProgrammingError:
		cur.close()
		conn.close()
		return "Database unavailable. Please try again", 503

# Update the log of the user. This function will be called when the user logs into the database successfully.
# Two fields will be updated in the database with the current times datetime stamp - Last_Login_Attempt and Successful_Login fields

# @param email address of the user
def update_correct_log(email):
	try:
		conn = create_connection()
		cur = conn.cursor()
		cur.execute("UPDATE users SET Incorrect_Login_Count = 0, Last_Login_Attempt = NOW(), Successful_Login = NOW(), Forgot_Password_Generated = NULL, Forgot_Password_Flag = 0 WHERE Email_ID=%s",(email,))
		conn.commit()
		cur.close()
		conn.close()
		return None
	
	except mysql.connector.errors.ProgrammingError:
		return 503


# This function will be called if the the user has logged in with the forgot password.
# If the password matches with the forgot_password_generated field in the database, then it returns the first name and value true indicating that it is the user's forgot password

# @param Email address of the user and the hashed password
# @return (first name and True) or (None and False)
def check_if_forgotten_password(email, password):
	try:
		conn = create_connection()
		cur = conn.cursor()
		cur.execute("SELECT FName FROM users WHERE Email_ID=%s AND Forgot_Password_Flag = 1 AND Forgot_Password_Generated=%s", (email, password))
		rows = cur.fetchall()
		cur.close()
		conn.close()
		if len(rows) == 1:
			return rows[0][0], True #Returns first name and true if it is the forgot password
		return None, False
		
	
	except mysql.connector.errors.ProgrammingError:
		return 503

# This function will be used to authenticate a users email and password
# The password when recieved will be hashed in HTML using SHA512 algorithm
# The email address and password will be checked in the database, if it exists, return firstname, True or False if the username and password is authentic or not

# @param email address and password of the user
# @return (First name, boolean True if the email and password is authentic, and code) or (First name, True and code 201 if it is a forgot password) or (None, False and 400 bad request error code)
def authenticate(email, password):
	try:
		conn = create_connection()
		cur = conn.cursor()
		password = hashlib.sha512((password + app.config['SALT']).encode('UTF-8')).hexdigest() # database password = sha512(hashed_password + salt)
		cur.execute("SELECT FName FROM users WHERE Email_ID = %s AND Password=%s", (email, password))
		rows = cur.fetchall()
		cur.close()
		conn.close()
		if len(rows) == 1: # If the email and password are authentic
			flag = update_correct_log(email) # Update the timestamps if the user is authenticated 
			if flag == 503: # An error occurred while connecting to the database
				return None, 503, None 
			return rows[0][0], True, 200
		else: #Check if it is a forgotten password
			name, flag = check_if_forgotten_password(email, password) 
			if flag == True: # Yes, it is a forgotten password
				return name, True, 201 
			if flag == 503: # An error occurred while connecting to the database
				return None, 503, None
		return None, False, 400 # No it was not forgot password, so the email and password are both not authentic
	
	except mysql.connector.errors.ProgrammingError:
		return None, 503


# User disabled function checks if the email address has been disabled by the system
# This is a security feature implemented in the website where the user can have atmost 3 consecutive incorrect login attempts
# If 3 consecutive incorrect login attempts are encountered, then the user is disabled for 5 minutes

# @param email address of the user
# @return True if disabled, else return False
def user_disabled(email):
	try:
		conn = create_connection()
		cur = conn.cursor()
		cur.execute("SELECT Disabled FROM users WHERE Email_ID = %s", (email,))
		rows = cur.fetchall()
		cur.close()
		conn.close()
		if len(rows) == 1: # Checks if the user exist
			if int(rows[0][0])  == 1: # Check if the user is disabled (1) or not (0)
				flag_last_login = check_last_login(email) # Check if 5 minutes has passed since the user has been disabled. If it has, then the user is not disabled anymore
				if flag_last_login == False: # User account has been disabled for less than 5 minutes
					return False
				if flag_last_login == 503: # Database error
					return 503
				return True # User is not disabled
			return False
		else: #If the user does not exist, send error 400 (Bad request)
			return 400
	
	except mysql.connector.errors.ProgrammingError:
		return 503
		

# Check if 5 minutes has passed since there has been an incorrect login attempt
# If it has passed, set the disabled and incorrect_count fields to 0 and return False, else True.

# @param Email address of the user
# @return False if the user is not disabled, True is the user is disabled.
def check_last_login(email):
	try:
		conn = create_connection()
		cur  = conn.cursor()
		cur.execute("SELECT TIME_TO_SEC(TIMEDIFF(NOW(),Last_Login_Attempt)) FROM users WHERE Email_ID = %s", (email,)) #Calculate the difference between the last incorrect login attempt and the current time
		rows = cur.fetchone()
		if int(rows[0]) > 300: # If 5 minutes have passed (5 * 60 seconds = 300)
			cur.execute("UPDATE users SET Incorrect_Login_Count = 0, Disabled = 0 WHERE Email_ID=%s", (email,)) # THe user is not disabled anymore. Set the incorrect login count and disabled flag to 0
			conn.commit()
			cur.close()
			conn.close()
			return False
		cur.close()
		conn.close()
		return True
		
	except mysql.connector.errors.ProgrammingError:
		return 503

# This function is used to update the incorrect_login_count, last_login_attempt and disabled fields for incorrect login attempt
# When there is an incorrect login attempt, increment the consecutive incorrect login field by 1 and the last_login_attempt field to the current timestamp
# If there have already been 3 consecutive login attempts, then disable the user by changing the disabled flag to 1

# @param email address of the user
def update_incorrect_login(email):
	try:
		conn = create_connection()
		cur = conn.cursor()
		cur.execute("SELECT Incorrect_Login_Count FROM users WHERE Email_ID=%s", (email,)) # Retrieve the incorrect login count of the user
		rows = cur.fetchone()
		if int(rows[0]) == 3: # Check if there are 3 consecutive incorrect login attempts
			cur.execute("UPDATE users SET Incorrect_Login_Count = 0, Disabled = 1, Last_Login_Attempt = NOW() WHERE Email_ID=%s", (email,)) # Update the disabled field to 1, the incorrect_login_count to 0 and last_login attempt to the current timestamp
		else: # There have been less than 3 consecutive login attempts
			cur.execute("UPDATE users SET Incorrect_Login_Count = Incorrect_Login_Count + 1, Last_Login_Attempt = NOW() WHERE Email_ID=%s", (email,)) # Increase the incorrect login count to 1
		conn.commit() # save the changes made to the database
		cur.close()
		conn.close()
		return None
	
	except mysql.connector.errors.ProgrammingError:
		return 503
	

# This is used to generate a random password. This functionality will be used to generate the a random password for the user during the forgot password module
# @return The random password generated
def generate_new_password():
	password = 'aA@1' # Hard code the first 4 characters to conform to the password policy
	for i in range(12): # Generate the next 12 characters. The random password will be 16 characters long
		password += random.choice(LIST_OF_CHARACTERS)
	return password

# This password will be used to set the random password generated during the forgot password module
# @param Email address of the user and the password
def set_forgot_password(email, password):
	try:
		conn = create_connection()
		cur = conn.cursor()
		rows = cur.fetchone()
		cur.execute("UPDATE users SET Incorrect_Login_Count=0, Forgot_Password_Generated=%s, Forgot_Password_Flag = 1 WHERE Email_ID=%s", (password, email)) #Set the forgot_password_flag to 1 stating the user has forgotten the password and generated a new temporary password
		conn.commit()
		cur.close()
		conn.close()
		return None
	
	except mysql.connector.errors.ProgrammingError:
		return 503

# This is used to validate/sanitize the fields we recieve from the user
# @param: s = value, var_name = name of the input field
# @return (True, 'Valid') If the field value is value, else (False, 'Invalid')
def validate_input(s, var_name):
	if len(s) <= 0: # Checks if the field is empty or not
		return False, "Please enter " + var_name
	
	if len(s) > 50 or (not re.match('^[a-zA-Z0-9#&]*$', s)): # Checks if the field is greater than 50 characters or does not conform to the rule
		return False, 'Invalid ' + var_name

	return True, 'Valid'

# This function validates/sanitizes the feedback field given by the user
# @param COntains the feedback from the user
# @return True after sanitizing the input, False if the feedback is blank
def validate_feedback(feedback):
	if len(feedback) <= 0: # Check if the feedback field is blank
		return False, "Please enter the feedback and then submit"
	
	feedback = feedback.replace('<', "&lt")
	feedback = feedback.replace('>', "&gt");
	feedback = feedback.replace('"', "&quot");
	feedback = feedback.replace("'", "&#x27");
	feedback = feedback.replace("/", "&#x2F");
	return True, feedback


# This function is used to validate the password to check if it conforms to the password rules.
# This function will be used during the user registration to validate the passwords given there
# @param Password given by the user during registration
# @return True if the password is valid, False if it isn't
def validate_password(password):
	if(len(password) < 8): #Checks if the password length is less than 8 characters
		return False
	if(re.search('.*[A-Z].*', password) and re.search('.*[a-z].*', password) and re.search('.*[0-9].*', password) and re.search('.*[@._!()-+*^].*', password)): #Checks if the password conforms to the password policy
		return True
	if(re.search('[^A-Za-z0-9.*@._!()-+*^]+', password)): #Checks if the password contains any characters that do not conform to the password policy
		print(re.search('[^A-Za-z0-9.*@._!()-+*^]+', password))
		return False
	return False

# This function will be used to validate the password that we obtain from the login page
# Since the password will be hashed with SHA512 algorithm, the hashed password will always only contain alphanumeric characters
# This function checks if the password recieved has only hashed passwords. If it does, return True, else return False
# @param password recieved from the login page
# @return Return True if it contains only alphanumeric characters, else return False
def validate_login_password(password):
	print(password)
	if password.isalnum():  # Checks if the string contains only alphanumeric characters
		return True
	return False

# This function is used to retrieve the user type from the database
# There are two user types in the database -'ADMIN', 'NORMAL'
# The home page is outputed based on the user type
# @param email address of the user
# @return (First name, user type) if the user exists, else None, None
def retrieve_name_user_type(email):
	try:
		conn = create_connection()
		cur = conn.cursor()
		cur.execute("SELECT FName, User_Type FROM users WHERE Email_ID = %s", (email,))
		rows = cur.fetchone()
		cur.close()
		conn.close()
		if len(rows)>0:
			return rows[0], rows[1]
		return None, None
	
	except mysql.connector.errors.ProgrammingError:
		return 503


# This function is used to check if the password and confirm password fields from registration page have the same values or not
# @param password and confirm password fields
# @return Return True if they are equal, else return False
def equal_passwords(password, confirm_password):
	if password != confirm_password:
		return False
	return True
	return 503

# This function will be used during page edit that is a module in the admin role
# This function opens the home.html file and retrieves the element in the body field to populate in the text area of the edit page
# @return Contents in <body> tag of home.html file
def retrieve_home_page():
	fread = open('./templates/home.html', 'r')
	output = ""
	body_flag = False
	nav_flag = False
	for line in fread:
		if line.strip().startswith("<body"):
			body_flag = True
		
		elif line.strip().startswith("</body"):
			body_flag = False
		
		elif body_flag == True:	
			if line.strip().startswith("<nav"):
				nav_flag = True
			
			if line.strip().endswith("</nav"):
				nav_flag = False
			
			elif line.strip().startswith("</nav"):
				nav_flag = False
			
			elif nav_flag == False:
				output += line
		
	fread.close()
	return output

# This function will be used to write the changes done in the edit-page.html file. 
# The contents given in the textarea will be written to the home.html and home-admin.html files
# @param content from the text area to be inserted into the home page
# @return True once the update is successful
def edit_home_page(new_content):
	files = ['./templates/home.html', './templates/home-admin.html'] # LIst of both the normal user and admin's home page files
	for filename in files:
		fread = open(filename, 'r') # Open the file in read mode
		output = "" # Ouput variable that will be later written into the file
		for line in fread: #Read line after line
			output += line # Add all the lines till it reaches it reaches the </nav> tag
			if line.strip().startswith("</nav"):
				break
		
		output += new_content # Add the new content
		after_body_flag = False
		for line in fread:
			if line.strip().startswith("</body"): # Check when the body ends
				output += line # Add the </body> tag
				after_body_flag = True # Flag that indicates that the next few lines will be after the body
		
			if after_body_flag == True: 
				output += line # Add the contents after the body ends if anything exists
		fread.close() # Close the file read handle
		
		fwrite = open(filename, 'w') # Open the hom page file in write mode
		fwrite.write(output) # Write the new content to the file
		fwrite.close() # Close the file write handle
	return True	
		

# This function will be called when the index or '/' path will be invoked
@app.route('/', methods=['GET'])
def root():
	if 'email' in session: # Check if the email is present in the session
		return redirect(url_for('home')) # if there is a session present, then redirect to the link that will be called by the function 'home()'
	g.user = None # If no session exists, set the global variable g.user to None
	return render_template('login.html') # Open login.html page

# This function is executed before any requests goes to the user
@app.before_request
def before_request():
	g.user = None # Set the global variable g.user to None
	if 'email' in session: #Check if there is a session present for the email
		g.user=session['email'] #If it is present, set the g.user variable to hold the session value

# This function will be used to generate a CSRF token for all the web pages
def generate_csrf_token():
	if '_csrf_token' not in session: #Check if a CSRF token was generated for user session
		session['_csrf_token'] = os.urandom(128) #If not generated, generate a 128 character random value and assign it to the session with key value '_csrf_token'
	return session['_csrf_token'] # CSRF Token
	
app.jinja_env.globals['csrf_token'] = generate_csrf_token #This will be called everytime a user goes to a page. There is a csrf_token() variable in all the web pages that will hold the CSRF token for the user
	

# This function will be used when the user sends the credentials to login into the website
@app.route('/login', methods=['POST', 'GET'])
def login():
	if request.method == 'GET': #Check the type of request. If it is a 'GET' request, then maybe the user is forcing the login request.
		if 'email' in session: # If a session exists, then redirect this request to the url for 'home()' function
			return redirect(url_for('home'))
	
	# Else it is a 'POST' request, which it is supposed to be.
	if 'email' in session:
		return redirect(url_for('home'))
	try: # This is used to handle the keyerror exception
		if request.form.get('_csrf_token') == None or request.form.get('_csrf_token') != str(session['_csrf_token']): # Check if the csrf token does not exist or if they are not equal. 
			print("Error 1")
			return redirect(url_for('error')) # redirect to the URL invoked by the function logout()

	except KeyError: #If a keyerror exists, then send the request to error() function
		print("Error 2")
		return redirect(url_for('error'))
	email = request.form.get('email') # Retrieve the email attribute from the login page
	if len(email) <= 0: # If email is blank
		message = "Please enter the email address" 
		return render_template('login.html', message=message) # Send the login.html page with the above message
	
	if len(email) > 50: # If the email address is greater than 50 characters, then send an error message
		print('1')
		message = "Invalid Email/Password"
		return render_template('login.html', message = message)
	
	if validate_email(email) == False: # Validate the email and check if the email is fine or not
		print('2')
		message = "Invalid Email/Password!"
		return render_template('login.html', message=message)
	
	disabled = user_disabled(email) # Check if the user is disabled
	if disabled == True: # User is disabled 
		message = "User has been disabled! Please try again later"
		return render_template('login.html', message=message)
	
	if disabled == 503: # Database error. Redirect to the url of error() function
		print("Error 3")
		return redirect(url_for('error'))
	
	if disabled == 400: # 400 means that it is a bad request. Keeping the errors as generic as possible to prevent fuzzing
		return render_template('login.html', message='Invalid Email/Password')
	
	password = request.form.get('password') # Retrieve the password attribute from the login page
	if len(password) <= 0: # If no password was entered
		message = "Please enter the password"
		return render_template('login.html', message=message)
	
	if validate_login_password(password) == False: # If the password does not contain alphanumeric characters
		print('3')
		return render_template('login.html', message="Invalid Email/Password")
	
	first_name, authenticity_flag, code = authenticate(email, password) #Authenticate the user
	if authenticity_flag == True and code == 200: # The user exists
		if recaptcha.verify(): #Check the captcha code
			session['email'] = email #Create a user session and store the email address of the user
			return redirect(url_for('home')) # Redirect to the home() function
		else:
			message = "Invalid CAPTCHA code"
			return render_template('login.html', message=message)
	
	elif authenticity_flag == True and code == 201: # The user is authenticated, but the forgot password was used
		session['email'] = email 
		return render_template('update_password.html', name=first_name) #Open the update_password page
	
	elif authenticity_flag == 503: # Database error occurred. So redirect the user to the URL of error() function
		print("Error 4")
		return redirect(url_for('error'))
	
	print('4')
	message = "Invalid Email Address/Password!" 
	code = update_incorrect_login(email) #The user exists but the password was incorrect
	if code != None and code == 503: # If database error occurs, redirect to URL of error() function
		print("Error 5")
		return redirect(url_for('error'))
	return render_template('login.html', message=message) #open login.html page and display the error message


# This function is the URL for home page
@app.route('/home', methods=['GET'])
def home():
	if 'email' in session: #If a session exists for the user email
		first_name, user_type = retrieve_name_user_type(session['email']) #Retrieve the user's first name and user type
		if first_name != None:
			if user_type.upper() == 'NORMAL': # If the user is a normal user, display the normal user's home page
				return render_template('/home.html', name=first_name.capitalize())
			
			elif user_type.upper() == 'ADMIN': #If it is an admin page, display the admin home page
				return render_template('/home-admin.html', name=first_name.capitalize())
			return redirect(url_for("error")) # If the user type is neither admin or normal, then there is an error. So redirect to error page
		else: #If the user does not have a first name
			return redirect(url_for('error')) # Redirect to the error page
	else:
		return redirect(url_for('root')) # If user session does not exist, then redirect to the login page

# This function is the URL for error page
@app.route('/error', methods=['GET'])
def error():
	return render_template('error.html') #Display the error.html page

# This function will recieve the feedback from the user
@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
	if request.method == 'GET': # The 'GET' request will occur if a user in session tries to force a user to the feedback page. The user will be automatically redirected to the URL of the home() function
		if g.user: # If a user session exists
			return redirect(url_for('home')) # Redirect to the URL of home() function
		else: # User session does not exisst
			return redirect(url_for('error')) # Redirect to error page 
	
	# This is for 'POST' request, which should be the right kind of request as we are posting the contents of a feedback from a user
	if g.user: # If the user session exists
		try:
			if request.form.get('_csrf_token') == None or request.form.get('_csrf_token') != str(session['_csrf_token']): #If the CSRF Token is either None or doesn't match, display the error page
				return redirect(url_for('error'))

		except KeyError:
			return redirect(url_for('error'))
		feedback = request.form.get('feedback') # Get the user feedback
		flag, feedback = validate_feedback(feedback) #Validate the user feedback and sanitize it
		first_name, user_type = retrieve_name_user_type(session['email']) # Retrieve the user's first name and user type
		if flag == False: #If the feedback if not valid
			message = "Feedback is Invalid. Please check your input and try again" # Error message
			if user_type.upper() == 'NORMAL': # If the user_type is normal
				return render_template('home.html', name=first_name, message=message) # Display home.html page
			
			elif user_type.upper() == 'ADMIN': # If the user is admin
				return render_template('home-admin.html', name=first_name, message=message) # Display home-admin.html page
			
			else: # If the user is neither normal or an admin, display the error page
				return redirect(url_for('error'))
		
		# Send the feedback of the website to the support team
		subject = "Feedback from " + session['email'] # Subject of the email
		message = 'Hello,\n\You have recieved the following review from the ' + first_name + '(' + session['email'] + ')\n\n"' + feedback + '"\n\nThanks and Regards,\nSecurity Blog' # Body of the email containing the feedback of the user
		send_email(EMAIL_ADDRESS, subject, message) # Send the email to the support team
		return render_template('feedback_received.html') # Show the feedback_recieved.html page
	else:
		return render_template('login.html', message = "Invalid session") #If the session is invalid, then display that the session is invalid
	

# This function will be used to display the registration page
@app.route('/registration', methods=['GET'])
def registration():
	if g.user: #If a user exists and is trying to force himself to the registration page without logging out
		return redirect(url_for('home')) # Redirect the user to the home page
	return render_template('registration.html') #If a user session does not exist, then the user is free to register himself on the website

# This function will be invoked when the user wants to send the registration information to the server
@app.route('/register-user', methods=['GET', 'POST'])
def register_user():
	if request.method == 'GET': # If a user invokes the 'GET' method instead of 'POST'
		if g.user: # If a user session exists
			return redirect(url_for('home')) # Redirect to the home page
		else: # If a user session does not exist
			return redirect(url_for('root')) # Redirect to the login page
			
	try:
		if request.form.get('_csrf_token') == None or request.form.get('_csrf_token') != str(session['_csrf_token']): 
			return redirect(url_for('error'))

	except KeyError:
		return redirect(url_for('error'))
	email = request.form.get('reg_email') # Retrieve the registration email attribute from the registration page
	fName = request.form.get('reg_fname') # Retrieve first name
	flag, result = validate_input(fName, 'First Name') # Validate the first name
	if flag == False: # If the First name is invalid
		return render_template('registration.html', message = result) #Send the error message to the registration page
	lName = request.form.get('reg_lname') # Get the Last name
	flag, result = validate_input(lName, 'Last Name') # Validate the Last name
	if flag == False: # If last name is invalid
		return render_template('registration.html', message = result) #send the error message to the registration page
	
	if validate_email(email) == False: # If email is invalid [ Note: validate_email is a python library that checks for the emails validity ] 
		message= "Invalid Email. Please enter a valid email address"
		return render_template('registration.html', message=message) # Send the error message to the registration Page
	
	password = request.form.get('password') # Retrieve the password
	if validate_password(password) == False: # If password is invalid
		message = "Invalid Password. Please conform to the password rules"
		return render_template('registration.html', message=message) # send the error message to the registration page
	
	confirm_password=request.form.get('confirm_password') # Retrieve the confirm password field from the registration page
	if validate_password(confirm_password) == False: # If confirm password is not valid
		message = "Invalid Confirm Password. Please conform to the password rules"
		return render_template('registration.html', message=message) # Send the error message to the registration page
		
	if equal_passwords(password, confirm_password) == False: #If both the password and confirm password values are not equal
		message = "Both passwords are not equal. Please try again"
		return render_template('registration.html', message=message) # Send the error message to the registration page
		
	email_flag = check_duplicate_email(email)
	if email_flag == False: # If the user email does not exist in the database
		result, code = create_new_user(email, password, fName, lName) # Insert the user into the database
		if code == 503: # Database error occurred during the create_new_user function
			return redirect(url_for('error')) # Redirect to theerror page
		result = "Successful"
		message = "Email Address has been registered successfully. Please go to the login page and log in with your email and password. Thank you for joining us!"
		return render_template('registration_msg.html', result=result, message=message) # Display registration successful page
	
	elif email_flag == True: # If email address already exists in the database
		message = "Email Address already exists"
		
	elif email_flag == 503: # If there is a database error during check_duplicate_email function redirect to the error page
		return redirect(url_for('error'))
	return render_template('registration.html', message=message) # This will be executed if the email address already exists in the database


# This function will be used to display the forgot-password page
@app.route('/forgot-password', methods=['GET'])
def forgot_password():
	if g.user: #If a session already exists and the user is trying to force himself/herself into this page
		return redirect(url_for('home')) # Redirect to the home screen
	return render_template('forgot_password.html') # If a user session does not exist, then display this page
	
@app.route('/send-recovery-password', methods=['GET', 'POST'])
def send_recovery_password():
	if g.user: # If a user session already exists and the user is trying to force himself/herself into this page
		return redirect(url_for('home')) # Redirect to the home page
	
	
	if request.method == 'GET': # If a user is trying to force himself/herself into this page
			return redirect(url_for('root')) # Redirect to the login page
			
	try:
		if request.form.get('_csrf_token') == None or request.form.get('_csrf_token') != str(session['_csrf_token']):
			return redirect(url_for('error'))

	except KeyError:
		return redirect(url_for('error'))
	email = request.form.get('forgot_email') # Retrieve the user email who seems to have forgotten his/her password
	email_is_valid = validate_email(email) # Check if the email is valid
	if email_is_valid: # If the email is valid
		email_flag = check_duplicate_email(email) # Check if the email exists in the database
		if email_flag: #If the email exists
			password = generate_new_password() # Generate a 16 character length random password
			hashed_password = hashlib.sha512(((hashlib.sha512(password.encode('UTF-8')).hexdigest()) + app.config['SALT']).encode('UTF-8')).hexdigest() # database password = SHA512(SHA512(generated_password) + salt)
			flag = set_forgot_password(email, hashed_password) # Set the flags for forgot password in the database
			if flag == 503: # If a database error occurs in set_forgot_password function
				return redirect(url_for('error')) # Redirect to the error page
			subject = "Security Blog Forgot Password Steps" #Subject of the email
			email_message = "Hello there!\n\nLooks like you forgot your password. Don't you worry! Login with this password:" + password + '\n\nThanks and Regards,\nSecurity Blog' #Body of the email containing the randomly generated password to be known only to the user
			send_email(email, subject, email_message) # Send the email
			message = "A recovery password has been sent to your email address! Please follow the steps mentioned in the mail." # message to be displayed on the recovery_password_sent.html page
			return render_template('recovery_password_sent.html', message=message) # Display the recovery_password_sent page with the success message
		
		elif email_flag == False: # If the email does not exist in the database
			message = "This email has not been registered" # Ask the user to register
			return render_template('recovery_password_sent.html', message=message) # Display the prompt asking for user to register his/her email on the website
		
		elif email_flag == 503: # If check_duplicate_email throws a database error, redirect to the error page
			return redirect(url_for('error'))
	message = "Invalid Email. Please try again" # If the email is not valid
	return render_template('forgot_password.html', message=message) # Display the error message on forgot_password page

# This function displays the update password page	
@app.route('/change-password', methods=['GET'])
def change_password():
	if g.user: # If a user session already exists and the user is trying to force himself/herself into this page
		return redirect(url_for('home')) # redirect the user to the home page
	return render_template('update_password.html') # If a user session does not exist, then display the update_password.html page

# This function is used to change the password of a user
@app.route('/update-password', methods=['GET', 'POST'])
def update_password():
	if request.method == 'GET': # If a user is trying to force himself/herself into this page
		if g.user: # If a session exists
			return redirect(url_for('home')) # Redirect the user to the home page
		else: # If a session does not exist
			return redirect(url_for('root')) # Redirect the user to the login page
		
	# This code is used when the request is a 'POST' method.
	if g.user: # If a user session exists
		try:
			if request.form.get('_csrf_token') == None or request.form.get('_csrf_token') != str(session['_csrf_token']):
				return redirect(url_for('error'))

		except KeyError:
			return redirect(url_for('error'))
		password = request.form.get('update_password') # Retrieve the update_password field from the web page
		confirm_password = request.form.get('update_confirm_password') # Retrieve the update_confirm_password field from the webpage
		if password != confirm_password: # If both fields are not equal
			message = "The password fields do not match"
			return render_template('update_password.html', message=message) # Display the error message on update_password page
		if validate_password(password) == False: # If password is not valid
			message = "Invalid password. Please conform to the password policy and try again."
			return render_template('update_password.html', message=message) # Display the error message on update_password page
		try:
			password = hashlib.sha512(((hashlib.sha512(password.encode('UTF-8')).hexdigest()) + app.config['SALT']).encode('UTF-8')).hexdigest() # Database password = SHA512(SHA512(password) + salt)
			conn = create_connection() # Connect to the database
			cur = conn.cursor()
			cur.execute("UPDATE users SET Password = %s, Forgot_Password_Generated=NULL, Forgot_Password_Flag = 0, Incorrect_Login_Count = 0 WHERE Email_ID = %s", (password, session['email'])) # Update the user's password in the database
			conn.commit() # Commit the changes
			cur.close()
			conn.close()
			
		except mysql.connector.errors.ProgrammingError:
			return redirect(url_for('error')) 
			
			g.user = None # Remove the user session from the global variable
			session.pop('email', None) # Remove the email id from the session
			session.pop('_csrf_token', None) # Remove the csrf token value from the session
		return render_template('password_changed.html', message='Password Changed Successfully!') # Display the password changed successfully message on password_changed page


# This function is used to populate the textarea in edit homepage page used by the admin user
@app.route('/edit-page', methods=['GET'])
def edit_page():
	if g.user: # If a user session exists
		first_name, user_type = retrieve_name_user_type(session['email']) # Retrieve the user_type and firstname
		if user_type.upper() == 'ADMIN': # As edit-page is an admin's privilege, only the admin should be able to view this page
			content = retrieve_home_page() # Retrieve the contents of the homepage
			return render_template('edit_page.html', content=content) # Display the edit-page webpage and populate the contents of the textarea with the contents of the home page to be edited
		
		elif user_type.upper() == 'NORMAL': # If a normal user is trying to force open this page, he/she will be redirected to the home page
			redirect(url_for('home'))
		
		else: # If the user type is neither admin nor normal, then redirect to the error page
			redirect(url_for('error'))
	return redirect(url_for('root'))
	
# This page will be displayed when the home page is to be edited
@app.route('/edit-page-successful', methods=['GET', 'POST'])
def edit_page_successful():
	first_name, user_type = retrieve_name_user_type(session['email']) # Retrieve the user_type and firstname
	if user_type.upper() == 'NORMAL': # If a normal user is trying to force open this link
		if g.user: # If the user has a session
			return redirect(url_for('home')) # Redirect to the home page
		else: # If the user does not have any session
			return redirect(url_for('root')) # Redirect to the login page
	
	if user_type != 'NORMAL' or user_type != 'ADMIN': # If the user is neither a normal user, nor an admin
		return redirect(url_for('error')) # Redirect the user to the error page
	if g.user: # If a user session exists
		if request.method == 'GET': # Check if the user is trying to force himself/herself into this webpage using 'GET' request
			return redirect(url_for('home')) #If yes, then redirect to the home page
		
		# This body is for 'POST' request, as it is supposed to be.
		try:
			if request.form.get('_csrf_token') == None or request.form.get('_csrf_token') != str(session['_csrf_token']): # Check if the CSRF Token is invalid
				return redirect(url_for('error'))

		except KeyError:
			return redirect(url_for('error'))
		result = edit_home_page(request.form.get('edit_page_content')) # Get the contents from the textarea of the edit page and edit the home pages
		if result == True: # If the home pages was edited successfully
			return render_template('edit_page_successful.html') # Display home page edited successfully page
		
		elif result == False: # If there was a problem in editing the home page
			return redirect(url_for('edit_page_failed')) # Redirect to the edit_page_failed function below
			
		return redirect(url_for('error')) # Else some other error occurred. Just display the error page to keep it generic and avoid fuzzing and catching all the errors.
	
	return redirect(url_for('root')) # If a user session does not exist, then redirect to the login page
		

# This function will be called if for some reason, the page edit was unsuccessful
@app.route('/edit-page-failed', methods=['GET'])
def edit_page_failed():
	if g.user: # If a user session exists
		return render_template('edit_page.html', message="Page edit was unsuccessful. Please try again") # Display the edit_page with the error message stating the page edit was unsuccessful
	
	else: # If a user session does not exist
		return redirect(url_for('root')) # Redirect to the login page
	
# This function will be invoked when the user wants to log out
@app.route('/logout',methods=['GET', 'POST'])
def logout():
	if g.user:
		try:
			if request.form.get('_csrf_token') == None or request.form.get('_csrf_token') != str(session['_csrf_token']):
				return redirect(url_for('error'))

		except KeyError:
			return redirect(url_for('error'))
		g.user = None # Remove the user from the global session variable
		session.pop('email', None) # Remove the user's email ID from the session
		session.pop('_csrf_token', None) # Remove the CSRF Token value from the session
		
	
	return render_template('login.html', message='User has been logged out') # Show the login page with message "User has been logged out"




