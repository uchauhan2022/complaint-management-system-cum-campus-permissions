import re
from requests.models import parse_url
from app import *
from flask import (Blueprint, Flask, flash, g, redirect, render_template,
                   request, send_file, session, url_for)
from flask_mysqldb import MySQL
import hashlib
import os
from datetime import date
from werkzeug.utils import secure_filename
from datetime import datetime
import subprocess
import string
import secrets
import json
from app.helperFunctions import *
import pytz 
IST = pytz.timezone('Asia/Kolkata')

configData = getConfigsFromJson()
main = Blueprint('main', __name__) 

BASE_URL = configData["BASE_URL"]

# Test route [ ALWAYS COMMENT AFTER USE ]
# @main.route('/test', methods=['GET','POST'])
# def test():
# 	return configData


# Login Page
@main.route('/', methods=['GET','POST'])
def home():
	user = getCurrentStudent()
	userIP = str(request.remote_addr)
	storeIP(userIP,"StudentLoginPage")
	try:
		# Logged in
		if user:
			return redirect(url_for('main.dashboard'))
		if request.method == 'POST':
			rollNumber = request.form['student-login-roll']
			password = hashlib.md5(request.form['student-login-password'].encode())
			result=None
			result = query_db("select * from login_student where rollNumber=%s;",(rollNumber,))
			if result:
				if result[0][2]==password.hexdigest():
					if str(result[0][3])=="1":
						session['rollNumber']=rollNumber
						return redirect(url_for('main.dashboard'))
					else:
						return render_template('login.html',loginFlag=2) # Flag 2 : Login not allowed
				else:
					return render_template('login.html',loginFlag=0) # Flag 0 : incorrect details
			else:
				return render_template('login.html',loginFlag=0) # Flag 0 : incorrect details (entry not found)
		else:
			return render_template('login.html',loginFlag=1) # Flag 1 : no alert displayed
	except Exception as e:
		return redirect(url_for('main.home'))
	
# Student Dashboard
@main.route('/dashboard', methods=['GET'])
def dashboard():
	user=getCurrentStudent()
	if user:
		# Dashboard not ready thus redirect to userProfile
		return redirect(url_for('main.userProfile'))
	else:
		return redirect(url_for('main.home'))

# Lodge a complaint (Student)
@main.route('/hostel-complaint', methods=['GET','POST'])
def studentCMS():
	user=getCurrentStudent()

	try:
		if user:
			userIP = str(request.remote_addr)
			storeIP(userIP,"StudentCMS",user[0][0])
			# Get user details
			userDetails = query_db("select userID, rollNumber, firstName, lastName from student_details where userID=%s;",(user[0][0],))

			if request.method == 'GET':

				# Get status flag if any
				appStatus = getAppStatusFlag()
	
				# Get complaints data
				getComplaintsUrl = BASE_URL + "getComplaintsStudent"
				getUpdatesUrl = BASE_URL + "getUpdatesStudent"
				AuthenticationHeader = {'Authorization':configData["AuthorizationToken"]}
				
				# Active Complaints 
				activeComplaintsParams = {'userID':userDetails[0][0], 'status':'0,2,3,4'}
				activeComplaintsResponse = requests.request("GET", getComplaintsUrl, headers=AuthenticationHeader, params=activeComplaintsParams)
				showActiveComplaints = activeComplaintsResponse.json()["complaints"]

				# Active Updates
				activeUpdatesResponse = requests.request("GET", getUpdatesUrl, headers=AuthenticationHeader, params=activeComplaintsParams)
				activeUpdates=activeUpdatesResponse.json()["updates"]

				# Verify Complaints 
				verifyComplaintsParams = {'userID':userDetails[0][0], 'status':'5'}
				verifyComplaintsResponse = requests.request("GET", getComplaintsUrl, headers=AuthenticationHeader, params=verifyComplaintsParams)
				showVerifyComplaints = verifyComplaintsResponse.json()["complaints"]

				# Verify Updates
				verifyUpdatesResponse = requests.request("GET", getUpdatesUrl, headers=AuthenticationHeader, params=verifyComplaintsParams)
				verifyUpdates=verifyUpdatesResponse.json()["updates"]

				# Past Complaints 
				pastComplaintsParams = {'userID':userDetails[0][0], 'status':'1,6,7,9'}
				pastComplaintsResponse = requests.request("GET", getComplaintsUrl, headers=AuthenticationHeader, params=pastComplaintsParams)
				showPastComplaints = pastComplaintsResponse.json()["complaints"]

				# Hostel log and complaint types
				hostelLog=query_db("select * from hostel_log where userID=%s and active=1;",(userDetails[0][0],))
				complaintTypes = query_db("select * from complaint_types;")	
				if hostelLog is not None:
					hostelRoomID=hostelLog[0][4]
					hostelDetails = query_db("select * from hostel_details where hostelRoomID=%s;",(hostelRoomID,))
					hostelData = query_db("select * from hostel_data where hostelID=%s;",(hostelDetails[0][1],))

					# When student has a room alloted
					return render_template('studentCMS.html',user=userDetails, activeComplaints = showActiveComplaints, verifyComplaints = showVerifyComplaints, pastComplaints = showPastComplaints, roomNo=hostelDetails[0][2], hostelName = hostelData[0][1], activeUpdates=activeUpdates,verifyUpdates=verifyUpdates, complaintTypes=complaintTypes, appStatus=appStatus)
				
				# When room is not alloted
				return render_template('studentCMS.html',user=userDetails, activeComplaints = showActiveComplaints, verifyComplaints = showVerifyComplaints, pastComplaints = showPastComplaints, roomNo="Not Applicable", hostelName="Not Applicable", activeUpdates=activeUpdates,verifyUpdates=verifyUpdates, complaintTypes=complaintTypes, appStatus=appStatus)
			
			
			if request.method=='POST':
				AuthenticationHeader = {'Authorization':configData["AuthorizationToken"]}

				# Submit a Complaint
				if request.form['submit']=='submitComplaint':

					complaintType = request.form['type-of-complaint']
					complaintSubject = request.form['complaint-subject']
					description = request.form['issue']
					date1 = request.form['date1']
					from1 = request.form['from1']
					to1 = request.form['to1']
					date2 = request.form['date2']
					from2 = request.form['from2']
					to2 = request.form['to2']
					date3 = request.form['date3']
					from3 = request.form['from3']
					to3 = request.form['to3']
					uploadedFile = request.files['filesComplaint']

					# Save file on server and get file path
					filePath = uploadFileOnServer(uploadedFile,"complaintImages",userDetails[0][0])
					
					# submit complaint
					submitComplaintUrl = BASE_URL + "submitComplaint"
					payload = { "userID" : userDetails[0][0], "type-of-complaint" : complaintType, "complaint-subject" : complaintSubject, "issue" : description, "date1" : date1, "from1" : from1, "to1" : to1, "date2" : date2, "from2" : from2, "to2" : to2, "date3" : date3, "from3" : from3, "to3" : to3, "filePath" : filePath, "severity" : "LOW", "room-number" : 0, "hostelID" : 0 }
					response  = requests.request("POST", submitComplaintUrl, headers=AuthenticationHeader, data=payload)
					
					# Response Status
					if response.status_code == 200:
						session["statusFlag"] = "Complaint Submitted"
					else :
						session["statusFlag"] = "Error"
					
					return redirect(url_for('main.studentCMS'))
					
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
					
					return redirect(url_for('main.studentCMS'))
				
				# Submit a feedback
				elif request.form['submit'].split(':')[0]=='feedbackSubmit':
					
					complaintID=request.form['submit'].split(':')[1]
					feedback = request.form['feedback']
					
					submitFeedbackUrl = BASE_URL + "submitFeedback"
					payload = {"complaintID" : complaintID, "feedback" : feedback}
					response = requests.request("POST", submitFeedbackUrl, headers=AuthenticationHeader, data=payload)
					
					# Response Status
					if response.status_code == 200:
						session["statusFlag"] = "Feedback Submitted"
					else :
						session["statusFlag"] = "Error"
					
					return redirect(url_for('main.studentCMS'))

		else:
			return redirect(url_for('main.home'))
	except Exception as e:
		return redirect(url_for('main.home'))


# User Profile        
@main.route('/user-profile', methods=['GET', 'POST'])
def userProfile():
	user=getCurrentStudent()
	
	if user:
		userIP = str(request.remote_addr)
		storeIP(userIP,"StudentUserProfile",user[0][0])
		userDetails = query_db("select userID, rollNumber, firstName, lastName, emailStudent, DOB, course, branch from student_details where userID=%s;",(user[0][0],))
		
		# Get status flag if any
		appStatus = getAppStatusFlag()

		# Get hostel specific data
		hostelLog = query_db("select hostelRoomID from hostel_log where userID=%s and active=1;",(user[0][0],))
		hostelDetails = query_db("select hostelID, roomNumber, type from hostel_details where hostelRoomID=%s",(hostelLog[0][0],))
		hostelData = query_db("select hostelName, caretakerID, nightCaretakerID, wardenID, securityID from hostel_data where hostelID=%s",(hostelDetails[0][0],))
		
		# Get Hostel staff data
		hostelStaffUrl = BASE_URL + "getHostelStaff"
		AuthenticationHeader = {'Authorization':configData["AuthorizationToken"]}
		params = {"wardenUserID" : hostelData[0][3], "ctUserID" : hostelData[0][1], "ntctUserID" : hostelData[0][2], "securityUserID" : hostelData[0][4],}
		response = requests.request("GET", hostelStaffUrl, headers=AuthenticationHeader, params=params)
		hostelStaff = response.json()["hostelStaff"]
		
		if request.method=='GET':

			return render_template('changePassword.html',user=userDetails,hostelDetails=hostelDetails,hostelPeeps=hostelStaff,hostelData=hostelData,appStatus=appStatus)
		
		if request.method=='POST':

			# Change Password
			if request.form['submit']=='Change Password':

				oldPassword = hashlib.md5(request.form['student-old-password'].encode())
				newPassword = hashlib.md5(request.form['student-new-password'].encode())

				changePasswordStudentUrl = BASE_URL + "changePasswordStudent"
				params = {"rollNumber" : user[0][1], "oldPassword" : oldPassword.hexdigest(), "newPassword" : newPassword.hexdigest()}
				response = requests.request("POST", changePasswordStudentUrl, headers=AuthenticationHeader, data=params)

				# Response Status	
				if response.status_code == 200:
					session["statusFlag"] = "Password Changed"
				elif response.status_code == 403:
					session["statusFlag"] = "Incorrect Password"
				else:
					session["statusFlag"] = "Error"

				return redirect(url_for("main.userProfile"))
	else:
		return redirect(url_for('main.home'))
		
# Permissions
@main.route('/permissions', methods=['GET','POST'])
def permissions():
	user=getCurrentStudent()
	
	if user:
		userIP = str(request.remote_addr)
		storeIP(userIP,"StudentPermissions",user[0][0])
		#getUserDetails
		userDetails = query_db("select userID, rollNumber, firstName, lastName from student_details where userID=%s;",(user[0][0],))
		
		#permissionsAdminControl
		permissionsAdminControlUrl = BASE_URL+"getPermissionsAdminControlls"
		permissionsAdminControlHeaders = {'Authorization': configData["AuthorizationToken"]}
		permissionsAdminControlResponse = requests.request("GET", permissionsAdminControlUrl, headers=permissionsAdminControlHeaders)
		permissionsAdminControls = json.loads(permissionsAdminControlResponse.text)
		permissionsAppActivated = permissionsAdminControls["activatePermissionsApp"]
		rulesInformation = permissionsAdminControls["informationToBeDisplayed"]
		inTime = permissionsAdminControls["inTime"]
		outTime = permissionsAdminControls["outTime"]

		#requestedPermissions
		requestedPermissionsUrl = BASE_URL+"getRequestedPermissions"
		requestedPermissionsparams = {'rollNumber': user[0][0]}
		requestedPermissionsheaders = {'Authorization':configData["AuthorizationToken"]}
		requestedPermissionsresponse = requests.request("GET", requestedPermissionsUrl, headers=requestedPermissionsheaders, params=requestedPermissionsparams)
		requestedPermissionsList = mapRequestedPermissionsToList(requestedPermissionsresponse.json())
		#activePermissions
		activePermissionsUrl = BASE_URL+"getActivePermissions"
		activePermissionsparams={'rollNumber': user[0][0]}
		activePermissionsheaders = {'Authorization':configData["AuthorizationToken"]}
		activePermissionsresponse = requests.request("GET", activePermissionsUrl, headers=activePermissionsheaders, params=activePermissionsparams)
		activePermissionsList = mapActivePermissionsToList(activePermissionsresponse.json())
		#expiredPermissions
		expiredPermissionsUrl = BASE_URL+"getExpiredPermissions"
		expiredPermissionsparams={'rollNumber': user[0][0]}
		expiredPermissionsheaders = {'Authorization':configData["AuthorizationToken"]}
		expiredPermissionsresponse = requests.request("GET", expiredPermissionsUrl, headers=expiredPermissionsheaders, params=expiredPermissionsparams)
		expiredPermissionsList = mapExpiredPermissionsToList(expiredPermissionsresponse.json())
		
		if request.method == 'GET':
			return render_template('permissions.html', user = userDetails, requestedPermissionsList = requestedPermissionsList, activePermissionsList = activePermissionsList, expiredPermissionsList = expiredPermissionsList, appActivation = permissionsAppActivated, rejectRequestFlag = 0, inTime = inTime, outTime = outTime, rulesInformation = rulesInformation)
		
		if request.method=='POST':
			#submit permission
			if request.form['submit']=='submitPermission':
				date = request.form['date']
				fromTime = request.form['fromTime']
				toTime = request.form['toTime']
				location = request.form['location']
				reason = request.form['reason']
				if not checkForValidTimestamp(toTime, fromTime, date, inTime, outTime):
					return render_template('permissions.html', user = userDetails, requestedPermissionsList = requestedPermissionsList, activePermissionsList = activePermissionsList, expiredPermissionsList = expiredPermissionsList, appActivation = permissionsAppActivated, rejectRequestFlag = 1,  inTime = inTime, outTime = outTime, rulesInformation = rulesInformation)
				if checkIfPermissionAlreadyExists(user[0][0],date):
					return render_template('permissions.html', user = userDetails, requestedPermissionsList = requestedPermissionsList, activePermissionsList = activePermissionsList, expiredPermissionsList = expiredPermissionsList, appActivation = permissionsAppActivated, rejectRequestFlag = 2,  inTime = inTime, outTime = outTime, rulesInformation = rulesInformation)
				url = BASE_URL+"setNewPermission"
				payload = {'submit': 'submitPermission','date': date,'fromTime': fromTime,'toTime': toTime,'location': location,'reason': reason,'rollNumber':user[0][0]}
				headers = {'Authorization': configData["AuthorizationToken"]}
				response = requests.request("POST", url, headers=headers, data=payload)
				return redirect(url_for("main.permissions"))
				
			#delete permission
			elif request.form['submit'].split(':')[0]=='deletePermission':
				permissionId = request.form['submit'].split(':')[1]
				url = BASE_URL+"deletePermission"
				payload={"permissionId":permissionId}
				headers = {'Authorization': configData["AuthorizationToken"]}
				response = requests.request("POST", url, headers=headers, data=payload)
				return redirect(url_for("main.permissions"))
	else:
		return redirect(url_for('main.home'))

# Forgot Password
@main.route('/forgot-password', methods=['GET','POST'])
def forgotPassword():
	cur = mysql.connection.cursor()
	userIP = str(request.remote_addr)
	storeIP(userIP,"StudentForgetPassword")
	if request.method=='GET':
		return render_template('forgotPassword.html',detailsCheck=0,success=0)
	if request.method=='POST':
		rollNumber = request.form['student-roll']
		emailX= request.form['student-email']
		rollResult = query_db("select * from login_student where rollNumber=%s;", (rollNumber,))
		if rollResult is not None:
			emailResult = None
			emailResult = query_db("select emailStudent from student_details where rollNumber=%s;", (rollNumber,))
			if emailResult and emailResult[0][0]==emailX:
				password=None
				alphabet = string.ascii_letters + string.digits
				while True:
					password = ''.join(secrets.choice(alphabet) for i in range(10))
					if (any(c.islower() for c in password)
            			and any(c.isupper() for c in password)
            			and sum(c.isdigit() for c in password) >= 3):
						break
				mailBody="Dear Student\n\nHere is your updated password for the hostel webkiosk.\n{}\nKindly change it as soon as possible.\nTHIS IS AN AUTOMATED MESSAGE- PLEASE DO NOT REPLY.\n\nThank You!".format(password)
				curDateTime = datetime.now(IST).strftime("%d-%m-%Y %H:%M:%S")
				mailSubject="Hostel Webkiosk Password Reset at "+str(curDateTime)
				if emailViaRollNumber(mailBody,mailSubject,rollNumber)=="OK":
					cur.execute("update login_student set password=%s where rollNumber=%s;", (hashlib.md5(password.encode()).hexdigest(),rollNumber,))
					mysql.connection.commit()
					return render_template('forgotPassword.html',detailsCheck=0,success=1)
				else:
					return render_template('forgotPassword.html',detailsCheck=0,success=0) 
			else:
				return render_template('forgotPassword.html',detailsCheck=1,success=0)
		else:
			return render_template('forgotPassword.html',detailsCheck=1,success=0)
	cur.close()

# Logout
@main.route('/logout')
def logout():
    user = getCurrentStudent()
    if user:
        session.pop('rollNumber', None)
        return redirect(url_for('main.home'))
    else:
        return redirect(url_for('main.home'))