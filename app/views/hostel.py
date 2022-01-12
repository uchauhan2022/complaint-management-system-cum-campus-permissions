from os import stat
from werkzeug import utils
from app import *
from app.helperFunctions import *
from flask import (Blueprint, Flask, flash, g, redirect, render_template,
                   request, send_file, session, url_for)
from flask_mysqldb import MySQL
import hashlib
from werkzeug.utils import secure_filename
from datetime import datetime
from flask_mail import Mail, Message  
import re
import csv
from datetime import date
import time
import string
import secrets
import pandas as pd
import pytz 
IST = pytz.timezone('Asia/Kolkata')

configData = getConfigsFromJson()
hostel = Blueprint('hostel', __name__, url_prefix='/hostel') 
BASE_URL = configData["BASE_URL"]


# Login page for Hostel
@hostel.route('/', methods=['GET','POST'])
def home():
	user = getCurrentHostelUser()
	userIP = str(request.remote_addr)
	storeIP(userIP,"hostelLoginPage")
	try:
		if user:
			return redirect(url_for('hostel.dashboard'))
		if request.method == 'POST':
			employeeID = request.form['hostel-login-employeeID']
			password = hashlib.md5(request.form['hostel-login-password'].encode())
			result=None
			result = query_db("select * from login_hostel where employeeID=%s;",(employeeID,))
			if result:
				if result[0][1]==password.hexdigest():
					session['employeeID']=employeeID
					session['whatIsMyRole']=configData["hostelRole"]
					return redirect(url_for('hostel.dashboard'))
				else:
					return render_template('hostel/login.html',loginFlag=0)
			else:
				return render_template('hostel/login.html',loginFlag=0)
		else:
			return render_template('hostel/login.html',loginFlag=1)
	except Exception as e:
		return redirect(url_for('hostel.home'))
	

# Dashboard
@hostel.route('/dashboard', methods=['GET'])
def dashboard():
	user=getCurrentHostelUser()
	if user:
		return redirect(url_for('hostel.hostelCMS'))
	else:
		return redirect(url_for('hostel.home'))

# Lodge a complaint from hostel
@hostel.route('/lodge-complaint', methods=['GET','POST'])
def lodgeComplaint():
	user = getCurrentHostelUser()
	
	if user:
		userIP = str(request.remote_addr)
		storeIP(userIP,"HostelLodgeComplaint",user[0][0])
		# Get status flag if any
		appStatus = getAppStatusFlag()
		
		# Get Hostel Employee Details
		AuthenticationHeader = {'Authorization':configData["AuthorizationToken"]}
		getHostelEmployeeDetailsUrl = BASE_URL + "getHostelEmployeeDetails"
		params = {"userID":user[0][0]}
		response = requests.request("GET", getHostelEmployeeDetailsUrl, headers=AuthenticationHeader, params=params)
		userData = response.json()["userData"]

		# Get hostel Details
		hostelID = userData[8]
		hostelName = query_db("select * from hostel_data where hostelID=%s;",(hostelID,))[0][1]
		
		# Get Hostel Room Data
		getHostelRoomDataUrl = BASE_URL + "getHostelRoomData"
		params = {"hostelID" : hostelID}
		response = requests.request("GET", getHostelRoomDataUrl, headers=AuthenticationHeader, params=params)
		hostelRoomData = response.json()["hostelRoomData"]
		roomDict = dict(response.json()["roomDict"])
		
		if request.method=="GET":
			
			getHostelComplaintsUrl = BASE_URL + "getHostelComplaintsAndUpdates"

			# Get active complaints and updates
			params = {"hostelID":hostelID, "status":"3,4", "deleted":"2", "student-details":0, "limit":-1}
			response = requests.request("GET", getHostelComplaintsUrl, headers=AuthenticationHeader, params=params)
			activeComplaints = response.json()["complaints"]
			activeUpdates = response.json()["updates"]

			# Get past complaints and updates
			params = {"hostelID":hostelID, "status":"8", "deleted":"2", "student-details":0, "limit":20}
			response = requests.request("GET", getHostelComplaintsUrl, headers=AuthenticationHeader, params=params)
			pastComplaints = response.json()["complaints"]
			pastUpdates = response.json()["updates"]

			# Get complaint types
			getComplaintTypesUrl = BASE_URL + "getComplaintTypes"
			response = requests.request("GET", getComplaintTypesUrl, headers=AuthenticationHeader)
			complaintTypes = response.json()["complaintTypes"]

			return render_template('hostel/lodgeComplaint.html',user=userData, activeUpdates=activeUpdates, pastUpdates=pastUpdates, activeComplaints=activeComplaints,  pastComplaints=pastComplaints, hostelRoomData = hostelRoomData, hostelName=hostelName,roomDict=roomDict, complaintTypes=complaintTypes, appStatus=appStatus)
		
		if request.method=="POST":

			submittedReq = request.form['submit']
			
			# Submit complaint 
			if submittedReq =='submitComplaint':

				complaintType = request.form['type-of-complaint']
				complaintSubject = request.form['complaint-subject']
				description = request.form['issue']
				uploadedFile = request.files['filesComplaint']
				severity = request.form['sev-of-complaint']
				hostelRoomID = request.form['room-number']

				# Save file on server and get file path
				filePath = uploadFileOnServer(uploadedFile,"complaintImages",userData[0])
				
				# submit complaint
				submitComplaintUrl = BASE_URL + "submitComplaint"
				payload = { "userID" : userData[0], "type-of-complaint" : complaintType, "complaint-subject" : complaintSubject, "issue" : description, "date1" : "#", "from1" : "#", "to1" : "#", "date2" : "#", "from2" : "#", "to2" : "#", "date3" : "#", "from3" : "#", "to3" : "#", "filePath" : filePath, "severity" : severity, "room-number" :  hostelRoomID, "hostelID" : userData[8] }
				response  = requests.request("POST", submitComplaintUrl, headers=AuthenticationHeader, data=payload)

				# Response Status
				if response.status_code == 200:
					session["statusFlag"] = "Complaint Submitted"
				else :
					session["statusFlag"] = "Error"	

			# Post an update
			elif submittedReq.split(':')[0]=="update":
				
				complaintID = submittedReq.split(':')[1]
				update = request.form['updateNew']
				
				# Post request
				postUpdateUrl = BASE_URL + "postComplaintUpdate"
				payload = {"userID" : userData[0], "complaintID" : complaintID, "update" : update}
				response  = requests.request("POST", postUpdateUrl, headers=AuthenticationHeader, data=payload)
				
				# Response Status
				if response.status_code == 200:
					session["statusFlag"] = "Update Submitted"
				else :
					session["statusFlag"] = "Error"	

			# Mark complaint as completed
			elif submittedReq.split(':')[0]=="markCompleted":
				
				complaintID = submittedReq.split(':')[1]
				update = request.form['updateNew']
				
				# Post request
				markComplaintCompletedUrl = BASE_URL + "markComplaintCompleted"
				payload = {"userID" : userData[0], "complaintID" : complaintID, "update" : update, "status" : 8}
				response  = requests.request("POST", markComplaintCompletedUrl, headers=AuthenticationHeader, data=payload)
				
				# Response Status
				if response.status_code == 200:
					session["statusFlag"] = "Update Submitted"
				else :
					session["statusFlag"] = "Error"	
				
			# Delete a complaint
			elif request.form['submit'].split(':')[0]=='deleteComplaint':
				
				complaintID=request.form['submit'].split(':')[1]
				
				deleteComplaintUrl = BASE_URL + "deleteComplaint"
				payload = {"complaintID" : complaintID}
				response = requests.request("POST", deleteComplaintUrl, headers=AuthenticationHeader, data=payload)
				
				# Response Status
				if response.status_code == 200:
					session["statusFlag"] = "Complaint Deleted"
				else :
					session["statusFlag"] = "Error"
			
			return redirect(url_for('hostel.lodgeComplaint'))
	else:
		return redirect(url_for('hostel.home'))	

# View hostel complaints
@hostel.route('/hostel-complaint', methods=['GET','POST'])
def hostelCMS():
	user=getCurrentHostelUser()
	
	if user:
		userIP = str(request.remote_addr)
		storeIP(userIP,"HostelComplaintsView",user[0][0])
		# Get status flag if any
		appStatus = getAppStatusFlag()
		print("started :" + str(time.perf_counter()))

		# Get Hostel Employee Details
		AuthenticationHeader = {'Authorization':configData["AuthorizationToken"]}
		getHostelEmployeeDetailsUrl = BASE_URL + "getHostelEmployeeDetails"
		params = {"userID":user[0][0]}
		response = requests.request("GET", getHostelEmployeeDetailsUrl, headers=AuthenticationHeader, params=params)
		userData = response.json()["userData"]
		print("1 :" + str(time.perf_counter()))

		hostelID=userData[8]

		# Get Hostel Room Data
		getHostelRoomDataUrl = BASE_URL + "getHostelRoomData"
		params = {"hostelID" : hostelID}
		response = requests.request("GET", getHostelRoomDataUrl, headers=AuthenticationHeader, params=params)
		roomDict = dict(response.json()["roomDict"])
		print("2 :" + str(time.perf_counter()))

		if request.method == 'GET':

			getHostelComplaintsUrl = BASE_URL + "getHostelComplaintsAndUpdates"

			# Get pending complaints and updates
			params = {"hostelID":hostelID, "status":"0", "deleted":"0", "student-details":1, "limit":-1}
			response = requests.request("GET", getHostelComplaintsUrl, headers=AuthenticationHeader, params=params)
			pendingComplaints = response.json()["complaints"]
			print("3 :" + str(time.perf_counter()))

			# Get active complaints and updates
			params = {"hostelID":hostelID, "status":"2,3,4", "deleted":"0", "student-details":1, "limit":-1}
			response = requests.request("GET", getHostelComplaintsUrl, headers=AuthenticationHeader, params=params)
			activeComplaints = response.json()["complaints"]
			activeUpdates = response.json()["updates"]
			print("4 :" + str(time.perf_counter()))

			# Get resolved complaints 
			params = {"hostelID":hostelID, "status":"6,7,5", "deleted":"0", "student-details":1, "limit":20}
			response = requests.request("GET", getHostelComplaintsUrl, headers=AuthenticationHeader, params=params)
			resolvedComplaints = response.json()["complaints"]
			print("5 :" + str(time.perf_counter()))

			# Get rejected complaints 
			params = {"hostelID":hostelID, "status":"1,9", "deleted":"0", "student-details":1, "limit":20}
			response = requests.request("GET", getHostelComplaintsUrl, headers=AuthenticationHeader, params=params)
			rejectedComplaints = response.json()["complaints"]
			print("6 :" + str(time.perf_counter()))

			return render_template('hostel/hostelCMS.html',user=userData, pendingComplaints=pendingComplaints, activeComplaints=activeComplaints, resolvedComplaints=resolvedComplaints, rejectedComplaints=rejectedComplaints, activeUpdates=activeUpdates, roomDict=roomDict, appStatus=appStatus)	
		
		if request.method=="POST":

			submittedReq = request.form["submit"]

			# Accept complaint
			if submittedReq.split(':')[0]=="accepted":
				
				complaintID = submittedReq.split(':')[1]
				update = request.form['update']
				msg = "Complaint Approved"
				
				# Actions on complaint
				actionsOnComplaintUrl = BASE_URL + "actionsOnComplaint"
				payload = {"userID" : userData[0], "complaintID" : complaintID, "update" : update, "msg" : msg, "status" : 3, "inHouse" : 0}
				response  = requests.request("POST", actionsOnComplaintUrl, headers=AuthenticationHeader, data=payload)
				
				# Response Status
				if response.status_code == 200:
					session["statusFlag"] = "Complaint Approved"
				else :
					session["statusFlag"] = "Error"

			# Reject complaint	
			elif submittedReq.split(':')[0]=="rejected":
				
				complaintID = submittedReq.split(':')[1]
				update = request.form['update']
				msg = "Complaint Rejected"

				# actions on complaint
				actionsOnComplaintUrl = BASE_URL + "actionsOnComplaint"
				payload = {"userID" : userData[0], "complaintID" : complaintID, "update" : update, "msg" : msg, "status" : 1, "inHouse" : 0}
				response  = requests.request("POST", actionsOnComplaintUrl, headers=AuthenticationHeader, data=payload)
				
				# Response Status
				if response.status_code == 200:
					session["statusFlag"] = "Complaint Rejected"
				else :
					session["statusFlag"] = "Error"
			
			# Handle complaint In house
			elif submittedReq.split(':')[0]=="inhouse":
				
				complaintID = submittedReq.split(':')[1]
				update = request.form['update']
				msg = "Complaint In-house"

				# actions on complaint
				actionsOnComplaintUrl = BASE_URL + "actionsOnComplaint"
				payload = {"userID" : userData[0], "complaintID" : complaintID, "update" : update, "msg" : msg, "status" : 2, "inHouse" : 1}
				response  = requests.request("POST", actionsOnComplaintUrl, headers=AuthenticationHeader, data=payload)
				
				# Response Status
				if response.status_code == 200:
					session["statusFlag"] = "Complaint Handled Inhouse"
				else :
					session["statusFlag"] = "Error"

			# Post an update
			elif submittedReq.split(':')[0]=="update":
				
				complaintID = submittedReq.split(':')[1]
				update = request.form['update']
				
				# Post request
				postUpdateUrl = BASE_URL + "postComplaintUpdate"
				payload = {"userID" : userData[0], "complaintID" : complaintID, "update" : update}
				response  = requests.request("POST", postUpdateUrl, headers=AuthenticationHeader, data=payload)
				
				# Response Status
				if response.status_code == 200:
					session["statusFlag"] = "Update Submitted"
				else :
					session["statusFlag"] = "Error"	

			# Mark complaint as completed
			elif submittedReq.split(':')[0]=="markCompleted":
				
				complaintID = submittedReq.split(':')[1]
				update = request.form['update']
				
				# Post request
				approveAllComplaintsUrl = BASE_URL + "markComplaintCompleted"
				payload = {"userID" : userData[0], "complaintID" : complaintID, "update" : update, "status" : 5}
				response  = requests.request("POST", approveAllComplaintsUrl, headers=AuthenticationHeader, data=payload)
				
				# Response Status
				if response.status_code == 200:
					session["statusFlag"] = "Complaint Marked Completed"
				else :
					session["statusFlag"] = "Error"	
	
			# Approve all complaints
			elif submittedReq.split(':')[0]=="markAllApproved":
				
				# Post request
				approveAllComplaintsUrl = BASE_URL + "approveAllComplaints"
				payload = {"userID" : userData[0], "hostelID" : hostelID}
				response  = requests.request("POST", approveAllComplaintsUrl, headers=AuthenticationHeader, data=payload)
				
				# Response Status
				if response.status_code == 200:
					session["statusFlag"] = "All Complaints Approved"
				else :
					session["statusFlag"] = "Error"	
			
			return redirect(url_for('hostel.hostelCMS'))

	else:
		return redirect(url_for('hostel.home'))



# User Profile
@hostel.route('/user-profile', methods=['GET', 'POST'])
def userProfile():
	user=getCurrentHostelUser()
	
	if user:
		userIP = str(request.remote_addr)
		storeIP(userIP,"HostelUserProfile",user[0][0])

		AuthenticationHeader = {'Authorization':configData["AuthorizationToken"]}

		# Get status flag if any
		appStatus = getAppStatusFlag()

		# Get employee details
		getHostelEmployeeDetailsUrl = BASE_URL + "getHostelEmployeeDetails"
		params = {"userID":user[0][0]}
		response = requests.request("GET", getHostelEmployeeDetailsUrl, headers=AuthenticationHeader, params=params)
		userDetails = response.json()["userData"]
		userRole = response.json()["userRole"]

		hostelID = userDetails[8]
		
		# Get hostel Data
		getHostelDataUrl = BASE_URL + "getHostelData"
		params = {"hostelID" : hostelID}
		response = requests.request("GET", getHostelDataUrl, headers=AuthenticationHeader, params=params)
		hostelData = response.json()["hostelData"]
		
		if request.method=='GET':
			
			return render_template('hostel/userProfile.html', userRole = userRole, user=userDetails, hostelData=hostelData, appStatus=appStatus)
		
		if request.method=='POST':
			
			# Change password
			if request.form['submit']=='Change Password':

				oldPassword = hashlib.md5(request.form['employee-old-password'].encode())
				newPassword = hashlib.md5(request.form['employee-new-password'].encode())

				changePasswordHostelUrl = BASE_URL + "changePasswordHostel"
				params = {"employeeID" : user[0][0], "oldPassword" : oldPassword.hexdigest(), "newPassword" : newPassword.hexdigest()}
				response = requests.request("POST", changePasswordHostelUrl, headers=AuthenticationHeader, data=params)

				# Response Status	
				if response.status_code == 200:
					session["statusFlag"] = "Password Changed"
				elif response.status_code == 403:
					session["statusFlag"] = "Incorrect Password"
				else:
					session["statusFlag"] = "Error"
			
			return redirect(url_for("hostel.userProfile"))	
	else:
		return redirect(url_for('hostel.home'))

# Generate report
@hostel.route('/generate-report', methods=["POST","GET"])
def generateReport():
	user=getCurrentHostelUser()
	
	if user:
		userIP = str(request.remote_addr)
		storeIP(userIP,"HostelGenerateReport",user[0][0])
		
		AuthenticationHeader = {'Authorization':configData["AuthorizationToken"]}
		
		# Get employee details
		getHostelEmployeeDetailsUrl = BASE_URL + "getHostelEmployeeDetails"
		params = {"userID":user[0][0]}
		response = requests.request("GET", getHostelEmployeeDetailsUrl, headers=AuthenticationHeader, params=params)
		userDetails = response.json()["userData"]
		
		hostelID = userDetails[8]

		# Get complaint types
		getComplaintTypesUrl = BASE_URL + "getComplaintTypes"
		response = requests.request("GET", getComplaintTypesUrl, headers=AuthenticationHeader)
		complaintTypes = response.json()["complaintTypes"]
		
		if request.method=="GET":
			
			return render_template('hostel/generateReport.html', user=userDetails, complaintTypes=complaintTypes)
		
		elif request.method=="POST":
			
			startDate=request.form['startDate']
			endDate=request.form['endDate']
			typeOfComplaint = request.form['type-of-complaint']
			statusCheck = request.form['status']
			
			status = "0,1,2,3,4,5,6,7,8,9"
			if statusCheck == "Active":
				status = "2,3,4"
			elif statusCheck == "Pending Approval":
				status = "0"
			elif statusCheck == "Completed":
				status = "5,6,7,8"
			elif statusCheck == "Discarded":
				status = "1,9"

			curDateTime = datetime.now(IST).strftime("%d-%m-%Y-%H-%M-%S")
			fileName = "complaintsReport-" + str(curDateTime) + ".csv"

			createComplaintsReportUrl = BASE_URL + "createComplaintsReportOnServer"
			payload={'startDate': startDate,'endDate': endDate,'hostelID' : hostelID,'typeOfComplaint': typeOfComplaint,'status': status,'inHouse': '-1','hostelComplaint': '-1','fileName': fileName,'reportFormat': '1'}
			response = requests.request("POST", createComplaintsReportUrl, headers=AuthenticationHeader, data=payload)
        
			return send_file('static/complaintReports/'+fileName, mimetype='text/csv', attachment_filename='complaintsReport.csv',as_attachment=True)	
	else:
		return redirect(url_for('hostel.home'))
		

@hostel.route('/forgot-password', methods=['GET','POST'])
def forgotPassword():
	cur = mysql.connection.cursor()
	userIP = str(request.remote_addr)
	storeIP(userIP,"HostelForgotPassword")
	if request.method=='GET':
		return render_template('hostel/forgotPassword.html',detailsCheck=0,success=0)
	if request.method=='POST':
		employeeID = request.form['employee-id']
		emailX= request.form['employee-email']
		employeeResult = query_db("select * from login_hostel where employeeID=%s;", (employeeID,))
		if employeeResult is not None:
			emailResult = None
			employee=query_db("select * from hostel_employee_mapping where employeeID=%s;",(employeeID,))
			emailResult = []
			if(employee[0][1]==0):
				emailResult=query_db("select email from warden_details where userID=%s;",(employee[0][2],))
			elif(employee[0][1]==1):
				emailResult=query_db("select email from caretaker_details where userID=%s;",(employee[0][2],))
			elif(employee[0][1]==2):
				emailResult=query_db("select email from night_caretaker_details where userID=%s;",(employee[0][2],))
			if emailResult and emailResult[0][0]==emailX:
				password=None
				alphabet = string.ascii_letters + string.digits
				while True:
					password = ''.join(secrets.choice(alphabet) for i in range(10))
					if (any(c.islower() for c in password)
            			and any(c.isupper() for c in password)
            			and sum(c.isdigit() for c in password) >= 3):
						break
				mailBody="Dear User\nHere is your updated password for the hostel webkiosk.\n{}\nKindly change it as soon as possible.".format(password)
				curDateTime = datetime.now(IST).strftime("%d-%m-%Y %H:%M:%S")
				mailSubject="Hostel Webkiosk Password Reset Requested at "+str(curDateTime)
				if email(mailBody,mailSubject,emailX)=="OK":
					cur.execute("update login_hostel set password=%s where employeeID=%s;", (hashlib.md5(password.encode()).hexdigest(),employeeID,))
					mysql.connection.commit()
					return render_template('hostel/forgotPassword.html',detailsCheck=0,success=1)
				else:
					return render_template('hostel/forgotPassword.html',detailsCheck=0,success=0) 
			else:
				return render_template('hostel/forgotPassword.html',detailsCheck=1,success=0)
		else:
			return render_template('hostel/forgotPassword.html',detailsCheck=1,success=0)
	cur.close()
	
# Logout
@hostel.route('/logout')
def logout():
	user = getCurrentHostelUser()
	if user:
		session.pop('employeeID', None )
		session.pop('whatIsMyRole', None )
		return redirect(url_for('hostel.home'))
	else:
		return redirect(url_for('hostel.home'))

