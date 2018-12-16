# Create the database
CREATE DATABASE IF NOT EXISTS blog;

USE blog;

# Drop the tables if they exist
DROP TABLE IF EXISTS login_log;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS logs;
DROP TABLE IF EXISTS support;
DROP TABLE IF EXISTS version;


# Create tables
CREATE DATABASE IF NOT EXISTS blog;
USE blog;
CREATE TABLE IF NOT EXISTS users(
	Email_ID VARCHAR(50) NOT NULL PRIMARY KEY,
	Password VARCHAR(128) NOT NULL,
	FName VARCHAR(50) NOT NULL,
	LName VARCHAR(50) NOT NULL,
	User_Type VARCHAR(50) NOT NULL DEFAULT 'NORMAL',
	Forgot_Password_Generated VARCHAR(128) DEFAULT NULL,
	Forgot_Password_Flag INTEGER DEFAULT 0,
	Incorrect_Login_Count INTEGER NOT NULL DEFAULT 0,
	Last_Login_Attempt datetime DEFAULT NULL,
	Successful_Login datetime DEFAULT NULL,
	Disabled NUMERIC NOT NULL DEFAULT 0);

CREATE TABLE IF NOT EXISTS logs(
	IP_Address VARCHAR(50) NOT NULL,
	Code INTEGER NOT NULL,
	Message TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS support(
	Email_ID VARCHAR(50) NOT NULL PRIMARY KEY,
	Password VARCHAR(64) NOT NULL);

CREATE TABLE IF NOT EXISTS version(
	Version_ID VARCHAR(128) PRIMARY KEY);


# Insert a value for your user
USE blog;
INSERT INTO users VALUES ('blog.email056@gmail.com', 'd133fe0badc737b62bce86ca3bc268c6d95c72c56ebbae3f90e2cbd66dec58f7b41d50cde31433000f201b526baea04ae2a007b86377cb4053734592560fd0fc', 'blog', 'email', 'ADMIN', NULL, 0, 0, NULL, NULL, 0);

INSERT INTO support VALUES ('blog.info056@gmail.com', 'f9961c3abc7a217da2b5372e0c9b7f7fc04ddf6d4ceb4cf378a17af26b1b8dac');



# Create authenticator role
USE mysql;
DROP USER IF EXISTS 'authenticator'@'localhost';
CREATE USER IF NOT EXISTS 'authenticator'@'localhost' IDENTIFIED BY '!@#Thisistheauthenticator123';

# Grant privileges to authenticator
GRANT ALL PRIVILEGES ON blog.* TO 'authenticator'@'localhost';

















































































































































































































	

