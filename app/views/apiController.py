from ctypes import resize
from os import stat
from requests import api
from requests.models import Response
from app import *
from flask import (Blueprint, Flask, flash, g, redirect, render_template,
                   request, send_file, session, url_for)
from flask_mysqldb import MySQL
import hashlib
from werkzeug.utils import secure_filename
from datetime import datetime
import re
import csv
from datetime import date
import time
import json
from flask_httpauth import HTTPBasicAuth
import hashlib
from app.helperFunctions import *
import pytz 
IST = pytz.timezone('Asia/Kolkata')

configData = getConfigsFromJson()
apiController = Blueprint('apiController', __name__, url_prefix='/api') 
auth = HTTPBasicAuth()

@auth.get_user_roles
def get_user_roles(username):
	if username == configData["AuthorizationUsername"]:
		return "admin"
	return "temp"

# Verify Authentication
@auth.verify_password
def verify_password(username, password):
	hashedPass = hashlib.md5(password.encode())
	if username==configData["AuthorizationUsername"] and configData["AuthorizationPassword"]==hashedPass.hexdigest():
		return username
	elif username==configData["tempUsername"] and configData["tempPassword"]==hashedPass.hexdigest():
		return username

# Swagger
@apiController.route('/', methods=['GET'])
@auth.login_required
def apiSwagger():
	listOfApis = {}
	listOfApis["/setNewPermission"] = {"Method":"POST",
	"Description":"adds a new permission",
	"parameters":{
		"date":"Date when permission is required", 
		"fromTime":"Campus exit time", 
		"toTime":"Campus entry time",
		"location":"Location of visit",
		"reason":"Purpose of visit",
		"rollNumber":"Roll Number of student"
		},
	"Authentication":"Required",
	"Return type":"msg,STATUS_CODE"
	}
	return listOfApis

# Health Check
@apiController.route('/healthCheckSender', methods=['POST'])
def healthCheckSender():
	print("Health check initiated")
	url = configData["PROD_BASE_URL"]+"healthCheckReceiver"
	response = requests.request("POST", url)
	print("Response code: "+str(response.status_code))
	if(response.status_code!=200):
		test = 3
		serverDead = 1
		while test>0:
			time.sleep(15)
			response = requests.request("POST", url)
			print("Response code: "+str(response.status_code))
			if response.status_code==200:
				serverDead = 0
				break
			test -= 1
		if serverDead == 1:
			sendHealthMessage("ALERT : Server not responding since last one minute!")
	return "OK",200

@apiController.route('/healthCheckReceiver', methods=['POST'])
def healthCheckReceiver():
	return "OK",200

# Saves new permission to db
@apiController.route('/setNewPermission', methods=['POST'])
@auth.login_required(role="admin")
def setNewPermission():
	cur = mysql.connection.cursor()
	try:
		if request.form['submit']=='submitPermission':
			date = request.form['date']
			fromTime = request.form['fromTime']
			toTime = request.form['toTime']
			location = request.form['location']
			reason = request.form['reason']
			rollNumber = request.form["rollNumber"]
			curDate = datetime.now().strftime("%d-%m-%Y")
			curTime = datetime.now().strftime("%H:%M:%S")
			cur.execute('insert into permissions (rollNumber, permDate, permOutTime, permInTime, reason, location, status, permRequestTime, PermRequestDate) values(%s,%s,%s,%s,%s,%s,%s,%s,%s);',(rollNumber, date, fromTime, toTime, reason,location, 0, curTime, curDate,))
			mysql.connection.commit()
			cur.close()
			return "OK",200
	except:
		cur.close()
		sendFailureMessage("setNewPermission", rollNumber)
		return "Internal Server Error",500

# Delete a permission from db
@apiController.route('/deletePermission', methods=['POST'])
@auth.login_required(role="admin")
def deletePermission():
	cur = mysql.connection.cursor()
	try:
		permisisonId = request.form['permissionId']
		cur.execute("UPDATE permissions SET `status` = '-1' WHERE (`permissionID` = %s);",(permisisonId,))
		mysql.connection.commit()
		cur.close()
		return "OK",200
	except:
		cur.close()
		sendFailureMessage("deletePermission", permisisonId)
		return "Internal Server Error",500

# Approve a permission parent
@apiController.route('/acceptPermission', methods=['POST'])
@auth.login_required(role="admin")
def acceptPermission():
	cur = mysql.connection.cursor()
	try:
		permisisonId = request.form['permissionId']
		cur.execute("UPDATE permissions SET `status` = '1' WHERE (`permissionID` = %s);",(permisisonId,))
		mysql.connection.commit()
		cur.close()
		return "OK",200
	except:
		cur.close()
		sendFailureMessage("acceptPermission", permisisonId)
		return "Internal Server Error",500

# Reject a permission parent
@apiController.route('/rejectPermission', methods=['POST'])
@auth.login_required(role="admin")
def rejectPermission():
	cur = mysql.connection.cursor()
	try:
		permisisonId = request.form['permissionId']
		cur.execute("UPDATE permissions SET `status` = '2' WHERE (`permissionID` = %s);",(permisisonId,))
		mysql.connection.commit()
		cur.close()
		return "OK",200
	except:
		cur.close()
		sendFailureMessage("rejectPermission", permisisonId)
		return "Internal Server Error",500

# Gets permissions where status is = 0 (i.e requested by student)
@apiController.route('/getRequestedPermissions', methods=['GET'])
@auth.login_required(role="admin")
def getRequestedPermissions():
	try:
		rollNumber = request.args.get('rollNumber')
		requestedPermission = query_db("select * from permissions where rollNumber=%s and status=0;",(rollNumber,))
		if requestedPermission is None:
			requestedPermission=[]
		data = {"requestedPermissions":list(requestedPermission)}
		return data,200
	except:
		sendFailureMessage("getRequestedPermissions", rollNumber)
		return "Internal Server Error",500

# Gets permissions where status is = 1, 3, 4 (i.e Active Permisisions)
@apiController.route('/getActivePermissions', methods=['GET'])
@auth.login_required(role="admin")
def getActivePermissions():
	try:
		rollNumber = request.args.get('rollNumber')
		activePermission = query_db("select * from permissions where rollNumber=%s and status in (1,3,4);",(rollNumber,))
		if activePermission is None:
			activePermission=[]
		data = {"activePermissions":list(activePermission)}
		return data,200
	except:
		sendFailureMessage("getActivePermissions", rollNumber)
		return "Internal Server Error",500

# Gets permissions where status is = 2, 5, 6, 7 (i.e  expired Permissions)
@apiController.route('/getExpiredPermissions', methods=['GET'])
@auth.login_required(role="admin")
def getexpiredPermissions():
	try:
		rollNumber = request.args.get('rollNumber')
		expiredPermission = query_db("select * from permissions where rollNumber=%s and status in (2, 5, 6, 7);",(rollNumber,))
		if expiredPermission is None:
			expiredPermission=[]
		data = {"expiredPermissions":list(expiredPermission)}
		return data,200
	except:
		sendFailureMessage("getExpiredPermissions", rollNumber)
		return "Internal Server Error",500

# Gets admin controlls
@apiController.route('/getPermissionsAdminControlls', methods=['GET'])
@auth.login_required(role="admin")
def getPermissionsAdminControlls():
	try:
		adminControlsDb = query_db("select * from permissions_admin_controls;")
		if adminControlsDb is None:
			adminControlsDb=[]
		data = mapPermissionsAdminControlsToDict(list(adminControlsDb))
		return data,200
	except:
		sendFailureMessage("getPermissionsAdminControlls")
		return "Internal Server Error",500

# Gets student details from roll number
@apiController.route('/getStudentDetails', methods=['GET'])
@auth.login_required
def getStudentDetails():
	try:
		rollNumber = request.args.get('rollNumber')
		studentDetails = query_db("select * from student_details where rollNumber=%s;",(rollNumber,))
		if studentDetails is None:
			studentDetails=[]
		print(studentDetails)
		data = {"studentDetails":list(studentDetails)}
		return data,200
	except:
		sendFailureMessage("getStudentDetails", rollNumber)
		return "Internal Server Error",500

# Gets permission for current date and status 1,3 from roll number 
# (Approved by parent but not returned to campus)
@apiController.route('/getPermission', methods=['GET'])
@auth.login_required(role="admin")
def getPermission():
	try:
		rollNumber = request.args.get('rollNumber')
		curDate=datetime.today()
		curDate=datetime.strftime(curDate,"%d-%m-%Y")
		permission = query_db("select * from permissions where rollNumber=%s and permDate=%s and status in (1,3,4);",(rollNumber, curDate,))
		if permission is None:
			permission=[]
			data = {"permission":permission}
		else:
			data = {"permission":list(permission)}
		return data,200
	except:
		sendFailureMessage("getPermission", rollNumber)
		return "Internal Server Error",500

# Mark exit by guard
@apiController.route('/markExit', methods=['POST'])
@auth.login_required(role="admin")
def markExit():
	cur = mysql.connection.cursor()
	try:
		permissionId = request.form['permissionId']
		guardId = request.form['guardId']
		status = 3
		now = datetime.now()
		curTime = now.strftime("%H:%M")
		cur.execute("UPDATE permissions SET status = %s, outTime = %s, guardIdOut = %s WHERE (permissionID = %s);",(status, curTime, guardId, permissionId,))
		mysql.connection.commit()
		cur.close()
		return "OK",200
	except:
		cur.close()
		sendFailureMessage("markExit", permissionId)
		return "Internal Server Error",500

# Mark entry by guard
@apiController.route('/markEntry', methods=['POST'])
@auth.login_required(role="admin")
def markEntry():
	cur = mysql.connection.cursor()
	try:
		permissionId = request.form['permissionId']
		guardId = request.form['guardId']
		now = datetime.now()
		curTime = now.strftime("%H:%M")
		inTime = list(query_db("select permInTime from permissions where permissionID=%s;",(permissionId,)))[0][0]
		curTimeObj = datetime.strptime(curTime,"%H:%M")
		inTimeObj = datetime.strptime(inTime,"%H:%M")
		status=0
		if(curTimeObj>inTimeObj):
			status=6
		else:
			status=5
		cur.execute("UPDATE permissions SET status = %s, inTime = %s, gaurdIdIn = %s WHERE (permissionID = %s);",(status, curTime, guardId, permissionId,))
		mysql.connection.commit()
		cur.close()
		return "OK",200
	except:
		cur.close()
		sendFailureMessage("markEntry", permissionId)
		return "Internal Server Error",500

# Get complaints by userID and status for student
@apiController.route('/getComplaintsStudent', methods=['GET'])
@auth.login_required
def getComplaintsStudent():
	try:
		userID = request.args.get('userID')
		status = request.args.get("status")
		query = "select * from cms where userID=%s and deleted=0 and status in ({status});".format(status=status)
		complaints = query_db(query,(userID,))
		if complaints is None:
			complaints =[]
		data = {"complaints": mapWorkerDetailToWorkerID(complaints)}
		return data,200
	except:
		sendFailureMessage("getComplaintsStudent", str(userID)+", status = "+str(status))
		return "Internal Server Error",500

# Get updates by userID and status for student
@apiController.route('/getUpdatesStudent', methods=['GET'])
@auth.login_required
def getUpdatesStudent():
	try:	
		userID = request.args.get('userID')
		status = request.args.get("status")
		query = "select * from cms where userID=%s and deleted=0 and status in ({status});".format(status=status)
		complaints = query_db(query,(userID,))
		if complaints is None:
			complaints =[]
		data = {"updates":mapUpdatesToComplaints(complaints)}
		return data,200
	except:
		sendFailureMessage("getUpdatesStudent", str(userID)+", status = "+str(status))
		return "Internal Server Error",500

# Submit complaint
@apiController.route('/submitComplaint', methods=['POST'])
@auth.login_required
def submitComplaint():
	cur = mysql.connection.cursor()
	try:
		userID = request.form['userID']
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
		filePath = request.form["filePath"]
		severity = request.form["severity"]
		hostelRoomID = request.form['room-number']
		hostelID = request.form['hostelID']
		duplicacy = 0
		deleted = 2
		status = 3

		# Format datetime
		datetime1 = date1+"="+from1+"="+to1
		datetime2 = date2+"="+from2+"="+to2
		datetime3 = date3+"="+from3+"="+to3

		# Format availibility time 
		availabilityTime = datetime1+"###"+datetime2+"###"+datetime3
		if date1=="#":
			availabilityTime = "Hostel Complaint"
		else:
			hostelID, hostelRoomID = getHostelIDRoomID(userID)
			duplicacy = checkIfDuplicateComplaint(userID,complaintType)
			deleted = 0
			status = 0

		curDate = datetime.now(IST).strftime("%d-%m-%Y")
		curTime = datetime.now(IST).strftime("%H:%M:%S")

		cur.execute('insert into cms (userID, hostelRoomID, type, subject, remarksStudent, hostelID, availabilityTime, attachment,times, date, repeated, severity, status, deleted) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);',(userID, hostelRoomID, complaintType, complaintSubject, description, hostelID, availabilityTime, filePath, curTime, curDate, duplicacy, severity, status, deleted, ))
		mysql.connection.commit()
		cur.close()
		return "OK",200
	except:
		cur.close()
		sendFailureMessage("submitComplaint", userID)
		return "Internal Server Error",500

# Delete Complaint
@apiController.route('/deleteComplaint', methods=['POST'])
@auth.login_required
def deleteComplaint():
	cur = mysql.connection.cursor()
	try:
		complaintID = request.form["complaintID"]
		cur.execute('update cms set deleted=1 where complaintID=%s;',(complaintID,))
		mysql.connection.commit()
		cur.close()
		return "OK",200
	except:
		cur.close()
		sendFailureMessage("deleteComplaint", complaintID)
		return "Internal Server Error",500

# Submit a complaint feedback (student)
@apiController.route('/submitFeedback', methods=['POST'])
@auth.login_required
def submitFeedback():
	cur = mysql.connection.cursor()
	try:
		complaintID = request.form["complaintID"]
		feedback = request.form["feedback"]
		cur.execute('update cms set feedback=%s, status=%s where complaintID=%s;',(feedback,6,complaintID,))
		mysql.connection.commit()
		cur.close()
		return "OK",200
	except:
		cur.close()
		sendFailureMessage("submitFeedback", complaintID)
		return "Internal Server Error",500

# Change Password Student
@apiController.route('/changePasswordStudent', methods=['POST'])
@auth.login_required(role=["admin"])
def changePasswordStudent():
	cur = mysql.connection.cursor()
	try:
		rollNumber = request.form['rollNumber']
		oldPassword = request.form['oldPassword']
		newPassword = request.form['newPassword']
		
		result = query_db("select * from login_student where rollNumber=%s;",(rollNumber,))
		
		if result[0][2]==oldPassword:
			cur.execute("update login_student set password=%s where rollNumber=%s;", (newPassword,rollNumber,))
			mysql.connection.commit()
			cur.close()
			return "OK",200
		cur.close()
		return "Incorrect Password",403
	except:
		cur.close()
		sendFailureMessage("changePasswordStudent", rollNumber)
		return "Internal Server Error",500

# Change Password Student
@apiController.route('/changePasswordHostel', methods=['POST'])
@auth.login_required(role="admin")
def changePasswordHostel():
	cur = mysql.connection.cursor()
	try:
		employeeID = request.form['employeeID']
		oldPassword = request.form['oldPassword']
		newPassword = request.form['newPassword']
		
		result = query_db("select * from login_hostel where employeeID=%s;",(employeeID,))
		
		if result[0][1]==oldPassword:
			cur.execute("update login_hostel set password=%s where employeeID=%s;", (newPassword,employeeID,))
			mysql.connection.commit()
			cur.close()
			return "OK",200
		cur.close()
		return "Incorrect Password",403
	except:
		cur.close()
		sendFailureMessage("changePasswordHostel", employeeID)
		return "Internal Server Error",500

# Get Hostel Staff
@apiController.route('/getHostelStaff', methods=['GET'])
@auth.login_required
def getHostelStaff():
	try:	
		wardenUserID = request.args.get('wardenUserID')
		ctUserID = request.args.get('ctUserID')
		ntctUserID = request.args.get('ntctUserID')
		securityUserID = request.args.get('securityUserID')
		
		wardenDeets = query_db("select firstName, lastName, mobile, email, hostelEmail from warden_details where userID=%s;",(wardenUserID,))
		ctDeets = query_db("select firstName, lastName, mobile, email from caretaker_details where userID=%s;",(ctUserID,))
		ntctDeets = query_db("select firstName, lastName, mobile, email from night_caretaker_details where userID=%s;",(ntctUserID,))
		securityDeets = query_db("select number from hostel_security_guards where userID=%s;",(securityUserID,))
		
		hostelStaff = []
		hostelStaff.append(wardenDeets[0])
		hostelStaff.append(ctDeets[0])
		hostelStaff.append(ntctDeets[0])
		hostelStaff.append(securityDeets[0])
		
		data = {"hostelStaff": hostelStaff}
		return data,200
	except:
		sendFailureMessage("getHostelStaff", str(wardenUserID)+","+str(ctUserID)+","+str(ntctUserID)+","+str(securityUserID))
		return "Internal Server Error",500

# Get hostel Employee Details
@apiController.route('/getHostelEmployeeDetails', methods=['GET'])
@auth.login_required(role="admin")
def getHostelEmployeeDetails():
	try:
		userID = request.args.get('userID')
		employee=query_db("select * from hostel_employee_mapping where employeeID=%s;",(userID,))
		employeeDetails = []
		userRole = ""
		if(employee[0][1]==0):
			employeeDetails=query_db("select userID, firstName, lastName, gender, mobile, picture, hostelID, hostelEmail from warden_details where userID=%s;",(employee[0][2],))
			userRole = "Warden"
		elif(employee[0][1]==1):
			employeeDetails=query_db("select * from caretaker_details where userID=%s;",(employee[0][2],))
			userRole = "Caretaker"
		elif(employee[0][1]==2):
			employeeDetails=query_db("select * from night_caretaker_details where userID=%s;",(employee[0][2],))
			userRole = "Night Caretaker"
		data = {"userData" : mapHostelEmployeeDetails(employeeDetails, employee), "userRole" : userRole}
		return data,200
	except:
		sendFailureMessage("getHostelEmployeeDetails",userID)
		return "Internal Server Error",500

@apiController.route('/getHostelRoomData', methods=['GET'])
@auth.login_required(role="admin")
def getHostelRoomData():
	try:
		hostelID = request.args.get('hostelID')
		hostelRoomData = query_db("select hostelRoomID, roomNumber from hostel_details where hostelID=%s;",(hostelID,))
		roomDict = {}
		if hostelRoomData is None:
			roomDict={}
			hostelRoomData=[]
		else:
			roomDict = dict(hostelRoomData)
		data = {"roomDict" : roomDict, "hostelRoomData" : hostelRoomData}
		return data,200
	except:
		sendFailureMessage("getHostelRoomData",hostelID)
		return "Internal Server Error",500

# Get complaints and updates by HostelID and status and deleted for hostel
@apiController.route('/getHostelComplaintsAndUpdates', methods=['GET'])
@auth.login_required(role="admin")
def getHostelComplaintsAndUpdates():
	try:
		hostelID = request.args.get('hostelID')
		status = request.args.get('status')
		deleted = request.args.get('deleted')
		addStudentDetails = request.args.get('student-details')
		limit = request.args.get('limit')
		
		query = "select * from cms where hostelID=%s and deleted=%s and status in ({status}) order by complaintID DESC".format(status=status)
		if limit!="-1":
			query = query + " LIMIT " + str(limit) + ";"
		else:
			query = query + ";"

		complaints = query_db(query,(hostelID,deleted,))
		if complaints is None:
			complaints =[]
		data = {"complaints" : mapCmsTable(complaints,addStudentDetails), "updates" : mapUpdatesToComplaints(complaints)}
		return data,200
	except:
		sendFailureMessage("getHostelComplaintsAndUpdates", str(hostelID)+", status = "+str(status)+", deleted = "+str(deleted))
		return "Internal Server Error",500

# Get complaints types
@apiController.route('/getComplaintTypes', methods=['GET'])
@auth.login_required
def getComplaintTypes():
	try:
		complaintTypes = query_db("select * from complaint_types;")
		data = {"complaintTypes" : list(complaintTypes)}
		return data,200
	except:
		sendFailureMessage("getComplaintTypes")
		return "Internal Server Error",500

# Submit update via hostel
@apiController.route('/postComplaintUpdate', methods=['POST'])
@auth.login_required(role="admin")
def postComplaintUpdate():
	try:
		cur = mysql.connection.cursor()

		userID = request.form["userID"]
		complaintID = request.form["complaintID"]
		update = request.form["update"]

		curDateTime = datetime.now(IST).strftime("%d-%m-%Y %H:%M:%S")
		
		cur.execute('insert into complaint_updates (complaintID,timestamp,updates,updatedBy) values (%s,%s,%s,%s);',(complaintID,curDateTime,update,userID,))
		mysql.connection.commit()
		cur.close
		return "OK",200
	except:
		sendFailureMessage("postComplaintUpdate", userID)
		return "Internal Server Error",500

# Mark complaint as completed
@apiController.route('/markComplaintCompleted', methods=['POST'])
@auth.login_required(role="admin")
def markComplaintCompleted():
	try:
		cur = mysql.connection.cursor()

		userID = request.form["userID"]
		complaintID = request.form["complaintID"]
		update = request.form["update"]
		status = request.form["status"]

		curDate = datetime.now(IST).strftime("%d-%m-%Y")
		curDateTime = datetime.now(IST).strftime("%d-%m-%Y %H:%M:%S")
		update = "Marked Completed: "+ update

		# Delete file from server
		filename=query_db("select attachment from cms where complaintID=%s",(complaintID,))
		print(filename)
		if filename is not None and filename[0] is not None and filename[0][0] is not None and filename[0][0]!="1":
			os.remove('app/static/'+filename[0][0])	

		# Mark complaint completed and push update
		cur.execute('insert into complaint_updates (complaintID,timestamp,updates,updatedBy) values (%s,%s,%s,%s);',(complaintID,curDateTime,update,userID,))
		cur.execute('update cms set status=%s, dateCompleted=%s where complaintID=%s;',(status,curDate,complaintID,))
		
		mysql.connection.commit()
		cur.close
		return "OK",200
	except:
		sendFailureMessage("markComplaintCompleted", userID)
		return "Internal Server Error",500

# Actions on a complaint (changing status and posting update)
@apiController.route('/actionsOnComplaint', methods=['POST'])
@auth.login_required(role="admin")
def actionsOnComplaint():
	try:
		cur = mysql.connection.cursor()

		userID = request.form["userID"]
		complaintID = request.form["complaintID"]
		update = request.form["update"]
		msg = request.form["msg"]
		status = request.form["status"]
		inHouse = request.form["inHouse"]

		update = msg + ": " + update
		curDateTime = datetime.now(IST).strftime("%d-%m-%Y %H:%M:%S")
		
		cur.execute('insert into complaint_updates (complaintID,timestamp,updates,updatedBy) values (%s,%s,%s,%s);',(complaintID,curDateTime,update,userID,))
		cur.execute('update cms set status=%s, inHouse=%s where complaintID=%s;',(status,inHouse,complaintID,))
		mysql.connection.commit()
		cur.close
		return "OK",200
	except:
		sendFailureMessage("postComplaintUpdate", userID)
		return "Internal Server Error",500

# Approve all complaints (hostel view)
@apiController.route('/approveAllComplaints', methods=['POST'])
@auth.login_required(role="admin")
def approveAllComplaints():
	try:
		cur = mysql.connection.cursor()

		userID = request.form["userID"]
		hostelID = request.form["hostelID"]

		update = "Approved via `Approve all`"
		curDateTime = datetime.now(IST).strftime("%d-%m-%Y %H:%M:%S")
		
		# Fetch all complaints from hostel ID
		complaints = query_db("select complaintID from cms where status=0 and hostelID=%s and deleted=0;",(hostelID,))
		if complaints is None:
			complaints = []

		# Push updates to complaints and change status = 3
		for complaint in complaints:
			cur.execute('insert into complaint_updates (complaintID,timestamp,updates,updatedBy) values (%s,%s,%s,%s);',(complaint[0],curDateTime,update,userID,))
		cur.execute('update cms set status=3 where status=0 and hostelID=%s and deleted=0;',(hostelID,))
		
		mysql.connection.commit()
		cur.close
		return "OK",200
	except:
		sendFailureMessage("postComplaintUpdate", userID)
		return "Internal Server Error",500

# Get complaints types
@apiController.route('/getHostelData', methods=['GET'])
@auth.login_required(role="admin")
def getHostelData():
	try:
		hostelID = request.args.get("hostelID")
		hostelData = query_db("select * from hostel_data where hostelID=%s",(hostelID,))[0]
		data = {"hostelData" : list(hostelData)}
		return data,200
	except:
		sendFailureMessage("getHostelData")
		return "Internal Server Error",500


# Create Complaints report on server
@apiController.route('/createComplaintsReportOnServer', methods=['POST'])
@auth.login_required(role="admin")
def createComplaintsReportOnServer():
	try:
		startDate=date(int(request.form['startDate'].split('-')[2]),int(request.form['startDate'].split('-')[1]),int(request.form['startDate'].split('-')[0]))
		endDate=date(int(request.form['endDate'].split('-')[2]),int(request.form['endDate'].split('-')[1]),int(request.form['endDate'].split('-')[0]))
		hostelID = request.form['hostelID']
		typeOfComplaint = request.form["typeOfComplaint"]
		status = request.form['status']
		inHouse = request.form['inHouse']
		hostelComplaint = request.form['hostelComplaint']
		fileName = request.form['fileName']
		reportFormat = request.form['reportFormat']
		query = createQueryForComplaintsReport(hostelID,typeOfComplaint,status,inHouse,hostelComplaint)
		
		print(query)
		allData = query_db(query)
		hostelData = query_db('select hostelID, hostelName from hostel_data;')
		roomData = query_db('select hostelRoomID, roomNumber from hostel_details;')
		workerData = query_db('select workerID, name from cms_workers_details;')

		if workerData is None:
			workerData = {}
		if allData is None:
			allData = []
		if roomData is None:
			roomData = {}
		if hostelData is None:
			hostelData = {}
		
		workerData = dict(workerData)
		roomData = dict(roomData)
		hostelData = dict(hostelData)
		roomData[1]="Hostel Complaint"
		
		count, hostels = generateComplaintsReportOnServer(fileName,startDate,endDate,reportFormat,allData,hostelData,roomData,workerData)
		data = {"hostels" : hostels, "count" : count}
		return data,200
	except:
		sendFailureMessage("createComplaintsReportOnServer","reportFormat"+str(reportFormat))
		return "Internal Server Error",500