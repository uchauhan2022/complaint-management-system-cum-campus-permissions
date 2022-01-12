from datetime import datetime
from flask import session
from app import *
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
import json
import pytz 
import csv
import pandas as pd
from datetime import date
IST = pytz.timezone('Asia/Kolkata')


# Configs *******
# Read configs from config.json
def getConfigsFromJson():
	with open('instance/config.json', 'r') as config_file:
		config_data = json.load(config_file)
	return config_data

# Get App Status Flag
def getAppStatusFlag():
	res = 0
	if "statusFlag" in session:
		res = session["statusFlag"]
		session.pop("statusFlag")
	return res

configData = getConfigsFromJson()

# Users *******
# Gets current student user
def getCurrentStudent():
	userResult = None
	if 'rollNumber' in session:
		rollNumber = session['rollNumber']
		for key in list(session.keys()):
			if key != "rollNumber" and key != "statusFlag":
				session.pop(key)
		userResult = query_db("select userID, rollNumber from login_student where rollNumber=%s;",(rollNumber,))
	return userResult

# Gets current hostel user
def getCurrentHostelUser():
	userResult = None
	if 'employeeID' in session:
		employeeID = session['employeeID']
		role=session['whatIsMyRole']
		for key in list(session.keys()):
			if key == "employeeID" or key == "whatIsMyRole" or key == "statusFlag":
				continue
			session.pop(key)
		userResult = query_db("select employeeID from login_hostel where employeeID=%s;",(employeeID,))
		if role != configData["hostelRole"]:
			return None
	return userResult

# Gets current Admin user
def getCurrentAdminUser():
	userResult = None
	if 'employeeID' in session:
		employeeID = session['employeeID']
		role=session['whatIsMyRole']
		for key in list(session.keys()):
			if key == "employeeID" or key == "whatIsMyRole" or key == "statusFlag":
				continue
			session.pop(key)
		userResult = query_db("select employeeID from login_admin where employeeID=%s;",(employeeID,))
		if role!= configData["adminRole"]:
			return None
	return userResult

# Gets current CMS user
def getCurrentCmsUser():
	userResult = None
	if 'employeeID' in session:
		employeeID = session['employeeID']
		role=session['whatIsMyRole']
		for key in list(session.keys()):
			if key == "employeeID" or key == "whatIsMyRole":
				continue
			session.pop(key)
		userResult = query_db("select employeeID from login_cms where employeeID=%s;",(employeeID,))
		if role!= configData["cmsRole"]:
			return None
	return userResult

# Gets current parent user
def getCurrentParentUser():
	userResult = None
	if 'parentID' in session:
		parentID = session['parentID']
		for key in list(session.keys()):
			if key == "parentID" or key == "statusFlag":
				continue
			session.pop(key)
		userResult = query_db("select userID from login_parent where userID=%s;",(parentID,))
	return userResult

# Gets current guard user
def getCurrentGuardUser():
	userResult = None
	if 'guardID' in session:
		guardID = session['guardID']
		for key in list(session.keys()):
			if key == "guardID" or key == "statusFlag":
				continue
			session.pop(key)
		userResult = query_db("select userID from login_guard where userID=%s;",(guardID,))
	return userResult

# Emails *******
mail = Mail(app)

# Email to a student by userID
def emailViaUserID(msgBody,subject,userID):
	receiversEmail = query_db("select emailStudent from student_details where userID=%s",(userID,))
	if receiversEmail is None:
		return
	email(msgBody,subject,receiversEmail[0][0])
	return "OK"

# Email to a student by rollNumber
def emailViaRollNumber(msgBody,subject,rollNumber,senderEmail='cmstiet@gmail.com' ):
	receiversEmail = query_db("select emailStudent from student_details where rollNumber=%s",(rollNumber,))
	if receiversEmail is None:
		return
	email(msgBody,subject,receiversEmail[0][0])
	return "OK"

# Email without attachment
def email(msgBody,subject,receiversEmail,senderEmail='cmstiet@gmail.com' ):
	msg = Message(subject, sender = senderEmail, recipients = [receiversEmail])
	msg.body = msgBody
	mail.send(msg)
	return "OK"

# Email with attachment (FOR CMS REPORT)
def emailAttach(msgBody,subject,recipients,cc,bcc,attachment,attachmentName,senderEmail='cmstiet@gmail.com' ):
	msg = Message(subject, body = msgBody, sender = senderEmail, recipients = recipients, cc = cc, bcc = bcc)
	with app.open_resource(attachment) as fp:
		msg.attach(attachmentName, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", fp.read())
		mail.send(msg)
	return "OK"

# Utility Functions *******
# Save file on server ()
def uploadFileOnServer(file,folderName,userID):
	try:
		fileName = ""
		fileName = secure_filename(file.filename)
		if fileName == "":
			return "1"
		fileExtension = fileName.split('.')[-1]
		fileName = str(userID)+datetime.now(IST).strftime("-%H-%M-%S")+'.'+fileExtension
		filePath = folderName+'/'+fileName
		file.save('app/static/'+folderName+'/'+fileName)
		return filePath
	except:
		return "ERROR"

# Get hostel ID and Room ID from user ID
def getHostelIDRoomID(userID):
	hostelLog=query_db("select * from hostel_log where userID=%s and active=1;",(userID,))
	hostelRoomID=-1
	hostelID=-1
	if hostelLog is not None:
		hostelRoomID=hostelLog[0][4]
		hostelDetails = query_db("select * from hostel_details where hostelRoomID=%s;",(hostelRoomID,))
		hostelID=hostelDetails[0][1]
	return hostelID,hostelRoomID

# Disord bot to send failed API messages
def sendFailureMessage(APIname,referenceID="NULL"):
	msg = "Request to API : '" + APIname + "' failed.\nCall made through reference ID :" + str(referenceID)
	url = configData["DiscordWebhook"]
	headers = {'Content-Type': 'application/json'}
	payload = json.dumps({"content": msg})
	response = requests.request("POST", url, headers=headers, data=payload)

# Disord bot to send server health msg
def sendHealthMessage(msg):
	url = configData["DiscordWebhookProdOffline"]
	headers = {'Content-Type': 'application/json'}
	payload = json.dumps({"content": msg})
	response = requests.request("POST", url, headers=headers, data=payload)

def storeIP(userIP, APIname, userID = "Not Available"):
	cur = mysql.connection.cursor()
	curDate = datetime.now().strftime("%d-%m-%Y")
	curTime = datetime.now().strftime("%H:%M:%S")
	cur.execute("INSERT INTO `analytics` ( `userIP`, `date`, `time`, `APIname`, `userID`) VALUES (%s, %s, %s, %s, %s);",(userIP,curDate,curTime,APIname,userID,))
	mysql.connection.commit()
	cur.close()

# Check Conditions *******
# Check for the following conditions:
# 1) if permisison in time is after allowed in time
# 2) if permisison out time is after allowed out time
# 3) if permisison in date-time before current time
# 4) if in time is before out time
def checkForValidTimestamp(toTime, fromTime, date, inTime, outTime):
	inTimeObeject = datetime.strptime(inTime, '%H:%M:%S')
	outTimeObject = datetime.strptime(outTime, '%H:%M:%S')
	curDateTimeObject = datetime.now()
	toTimeObject = datetime.strptime(toTime, '%H:%M')
	fromTimeObject = datetime.strptime(fromTime, '%H:%M')
	permissionDateTimeObject = datetime.strptime(date+" "+toTime, '%d-%m-%Y %H:%M')
	if inTimeObeject<toTimeObject or outTimeObject<fromTimeObject:
		return False
	if curDateTimeObject>permissionDateTimeObject:
		return False
	if inTimeObeject<outTimeObject:
		return False	
	return True

# Checks if a permission already exists for the asked date. (Only one permission per date)
def checkIfPermissionAlreadyExists(userId, date):
	permission = query_db("select * from permissions where rollNumber=%s and permDate=%s;",(userId, date,))
	if permission is None:
		return False
	return True

# Checks if its a duplicate complaint
def checkIfDuplicateComplaint(userID,complaintType):
	duplicacy = 0
	curTypes = query_db("select type from cms where deleted=0 and status in (0,2,3,4) and userID=%s;", (userID,))
	if curTypes is None:
		curTypes=[]
	for curType in curTypes:
		if curType[0] == complaintType:
			duplicacy = 1
	return duplicacy


# Mappings *******
# Mapping worker details to worker ID and append in the list
def mapWorkerDetailToWorkerID(complaints):
	result = []
	for complaint in complaints:
		workerID = complaint[14]
		worker = query_db("select name, phone from cms_workers_details where workerID=%s;",(workerID,))
		if worker is None:
			worker = [["Not Available","Not Available"]]
		tempResult = []
		for i in complaint:
			tempResult.append(i)
		tempResult.append(worker[0][0])
		tempResult.append(worker[0][1])
		result.append(tempResult)
	return result

# Map complaints in general format (Acceots a list)
def mapCmsTable(complaints, addStudentDetails = 0):
	result = []
	
	for complaint in complaints:
		
		complaint = list(complaint)
		
		complaint[2] = str(complaint[2])

		if complaint[11] is None:
			complaint[11] = "1"

		if complaint[12] is None:
			complaint[12] = "Not Available"
		workerName = "Not Alloted"
		workerPhone = "Not Alloted"
		
		
		if complaint[14] == 0:
			complaint[14] = "Not Alloted"
		else:
			worker = query_db("select name, phone from cms_workers_details where workerID=%s;",(complaint[14],))
			if worker is not None:
				workerName = worker[0][0]
				workerPhone = worker[0][1]
		
		if complaint[15] is None:
			complaint[15] = "Not Available"
		
		complaint.append(workerName) #19
		complaint.append(workerPhone) #20
		
		if addStudentDetails == "1":
			
			studentDetails = query_db("select rollNumber,firstName,lastName,mobileStudent from student_details where userID=%s;",(complaint[1],))
			if studentDetails is not None:
				complaint.append(studentDetails[0][0]) # roll Number 21
				complaint.append(studentDetails[0][1]) # first name 22
				complaint.append(studentDetails[0][2]) # last Name 23
				complaint.append(studentDetails[0][3]) # mobile 24
		
		result.append(complaint)
	
	return result

# Mapping updates to complaints
def mapUpdatesToComplaints(complaints):
	result = []
	for complaint in complaints:
		complaintID = complaint[0]
		updates = query_db("select updatedID,complaintID,timestamp,updates from complaint_updates where complaintID=%s;",(complaintID,),)
		if updates is None:
			updates = []
		for update in updates:
			result.append(update)
	return result


# Mapping requested permissions to a list
def mapRequestedPermissionsToList(data):
	tempResponse = data["requestedPermissions"]
	finalResponse = []
	for i in tempResponse:
		permissionID = i[0]
		permissionDate = i[2]
		permissionOutTime = i[3]
		permissionInTime = i[4]
		reason = i[5]
		location = i[6]
		permissionRequestedAt = i[8]
		permissionRequestedOn = i[9]
		curResponse = [permissionID, permissionDate, permissionOutTime, permissionInTime, reason, location, permissionRequestedAt, permissionRequestedOn]
		finalResponse.append(curResponse)
	return finalResponse

# Mapping active permissions to a list
def mapActivePermissionsToList(data):
	tempResponse = data["activePermissions"]
	finalResponse = []
	for i in tempResponse:
		permissionID = i[0]
		permissionDate = i[2]
		permissionOutTime = i[3]
		permissionInTime = i[4]
		reason = i[5]
		location = i[6]
		status = i[7]
		permissionRequestedAt = i[8]
		permissionRequestedOn = i[9]
		approvedByParentsAt = i[10]
		approvedByParentsOn = i[11]
		leftCampusAt = i[13]
		if leftCampusAt is None:
			leftCampusAt="Time unavailable"
		campusExitApprovedByGaurd = i[14]
		if campusExitApprovedByGaurd is None:
			campusExitApprovedByGaurd = "Unavailable"
		curResponse = [permissionID, permissionDate, permissionOutTime, permissionInTime, reason, location, status, permissionRequestedAt, permissionRequestedOn, approvedByParentsAt, approvedByParentsOn, leftCampusAt, campusExitApprovedByGaurd]
		finalResponse.append(curResponse)
	return finalResponse

# Mapping expired permissions to a list
def mapExpiredPermissionsToList(data):
	tempResponse = data["expiredPermissions"]
	finalResponse = []
	for i in tempResponse:
		permissionID = i[0]
		permissionDate = i[2]
		permissionOutTime = i[3]
		permissionInTime = i[4]
		reason = i[5]
		location = i[6]
		status = i[7]
		permissionRequestedAt = i[8]
		permissionRequestedOn = i[9]
		approvedByParentsAt = i[10]
		approvedByParentsOn = i[11]
		returnedToCampusAt = i[12]
		if returnedToCampusAt is None:
			returnedToCampusAt = "Time unavailable"
		leftCampusAt = i[13]
		if leftCampusAt is None:
			leftCampusAt = "Time unavailable"
		campusExitApprovedByGaurd = i[14]
		campusEntryApprovedByGaurd = i[15]
		if campusEntryApprovedByGaurd is None:
			campusEntryApprovedByGaurd = "Unavailable"
		if campusExitApprovedByGaurd is None:
			campusExitApprovedByGaurd = "Unavailable"
		curResponse = [permissionID, permissionDate, permissionOutTime, permissionInTime, reason, location, status, permissionRequestedAt, permissionRequestedOn, approvedByParentsAt, approvedByParentsOn, returnedToCampusAt, leftCampusAt, campusEntryApprovedByGaurd, campusExitApprovedByGaurd]
		finalResponse.append(curResponse)
	return finalResponse

# Maps permission admin controls to dictionary with appropriate data
def mapPermissionsAdminControlsToDict(adminControlsDb):
	data = {}
	if len(adminControlsDb)==0:
		data["inTime"]="Not Available"
		data["outTime"]="Not Available"
		data["informationToBeDisplayed"]=["Not Available"]
		data["activatePermissionsApp"]=0
		data["mailReportsToWardens"]="Configure accordingly"
	else:
		data["inTime"]=adminControlsDb[0][1]
		data["outTime"]=adminControlsDb[0][2]
		data["informationToBeDisplayed"]=list(adminControlsDb[0][3].split("#$#"))
		data["activatePermissionsApp"]=adminControlsDb[0][4]
		data["mailReportsToWardens"]=list(adminControlsDb[0][5].split(" "))
	return data

# Maps student details to dictionary with appropriate data
def mapStudentDetailsToList(studentDetailsData):
	studentDetails = studentDetailsData["studentDetails"]
	data = []
	# Check if details are present
	if len(studentDetails)==0:
		data.append(0)
	else:
		data.append(1)
		data.append(studentDetails[0][1])
		data.append(studentDetails[0][2])
		data.append(studentDetails[0][3])
		data.append(studentDetails[0][4])
		data.append(studentDetails[0][5])
		data.append(studentDetails[0][6])
		data.append(studentDetails[0][7])
		data.append(studentDetails[0][8])
		data.append(studentDetails[0][9])
		data.append(studentDetails[0][10])
		data.append(studentDetails[0][11])
		data.append(studentDetails[0][12])
		data.append(studentDetails[0][13])
		data.append(studentDetails[0][14])
		data.append(studentDetails[0][15])
		data.append(studentDetails[0][16])
	return data
	

# Maps current permission to dictionary with appropriate data
def mapPermissionToList(permissionData):
	permission = permissionData["permission"]
	data = []
	# Check if permission is present
	if len(permission)==0:
		data.append(0)
	else:
		data.append(1)
		data.append(permission[0][0])  # permissionId
		data.append(permission[0][3])  # permOutTime
		data.append(permission[0][4])  # permInTime
		data.append(permission[0][5])  # reason
		data.append(permission[0][6])  # location
		data.append(permission[0][7])  # status
		if permission[0][13] is None:  # outTime
			data.append("Not Available")
		else:
			data.append(permission[0][13]) 
		if permission[0][13] is None:  # inTime
			data.append("Not Available")
		else:
			data.append(permission[0][12])
	return data


# Maps hostel employee details
def mapHostelEmployeeDetails(employeeDetails, employee):
	employeeID = employee[0][0]
	employeeRole = employee[0][1]
	employeeUserID = employee[0][2]
	employeeFName = employeeDetails[0][1]
	employeeSName = employeeDetails[0][2]
	employeeGender = employeeDetails[0][3]
	employeePic = employeeDetails[0][5]
	employeePhone = employeeDetails[0][4]
	hostelID = int(employeeDetails[0][6])
	employeeEmail = employeeDetails[0][7]
	userData = [employeeID,employeeUserID,employeeRole,employeeFName,employeeSName,employeeGender,employeePic,employeePhone,hostelID,employeeEmail]
	return userData

# HERE 

# Get hostel ID from student roll number
def getHostelIDFromRollNumber(rollNumber) :
	hostelRoomIDResult = query_db("Select hostelRoomID from hostel_log where userID = %s ans active=1;", (rollNumber,))
	if hostelRoomIDResult is None:
		hostelRoomID=""
	else:
		hostelRoomID=list(hostelRoomIDResult)[0][0]
	hostelIDResult = query_db("Select hostelID from hostel_details where hostelRoomID = %s;", (hostelRoomID,))
	if hostelIDResult is None:
		hostelID=""
	else:
		hostelID=list(hostelIDResult)[0][0]
	
	return hostelID

# Get warden email ID from hostel ID
def getWardenEmailViaHostelID(hostelID) :
	wardenIDResult = query_db("Select wardenID from hostel_data where hostelID = %s;", (hostelID,))
	if wardenIDResult is None:
		wardenID=""
	else:
		wardenID=list(wardenIDResult)[0][0]

	wardenEmailResult = query_db("Select hostelEmail from warden_details where userID = %s;",(wardenID,))

	if wardenEmailResult is None:
		wardenEmail=""
	else:
		wardenEmail=list(wardenEmailResult)[0][0]

	return wardenEmail

# Get student's name from roll number
def getStudenNameViaRollNumber(rollNumber) :
	studentNameResult = query_db("Select firstName,lastName from student_details where rollNumber = %s;",(rollNumber,))

	if studentNameResult is None:
		studentName=""
	else:
		studentNameResult=list(studentNameResult)
		studentName = studentNameResult[0][0] + " " +studentNameResult[0][1]

	return studentName

# Get student's email ID from roll number
def getStudenEmailViaRollNumber(rollNumber) :
	studentEmailResult = query_db("Select emailStudent from student_details where rollNumber = %s;",(rollNumber,))

	if studentEmailResult is None:
		studentEmail=""
	else:
		studentEmail=list(studentEmailResult)[0][0]

	return studentEmail

# Get parents' email ID from roll number
def getParentsEmailViaRollNumber(rollNumber) :
	parentsEmailResult = query_db("Select emailMother,emailFather from student_details where rollNumber = %s;",(rollNumber,))

	if parentsEmailResult is None:
		parentsEmail=[]
	else:
		parentsEmail=list(parentsEmailResult)[0]

	return parentsEmail

def getPermissionStatusMapping():
	permissionStatusMap = {}
	permissionStatusMap[-1] = "Permission Deleted"
	permissionStatusMap[0] = "Permission Requested by Student"
	permissionStatusMap[1] = "Permission Approved by Parent"
	permissionStatusMap[2] = "Permission Denied by Parent"
	permissionStatusMap[3] = "Student exited the Campus"
	permissionStatusMap[4] = "In time exceeded; Student not returned"
	permissionStatusMap[5] = "Student entered in time"
	permissionStatusMap[6] = "Student entered late"
	permissionStatusMap[7] = "Student never returned"

	return permissionStatusMap


def getRollNumberNameMapping():
	nameData = query_db('select rollNumber, firstName, lastName from student_details;')

	rollNumberNameMap = {}

	if nameData is None:
		nameData=[]
	else:
		nameData = list(nameData)

	for data in nameData:
		name = data[1]+" "+data[2]
		rollNumberNameMap[data[0]] = name

	return rollNumberNameMap

def getRollNumberStudentContactMapping():
	contactData = query_db('select rollNumber, mobileStudent from student_details;')

	rollNumberContactMap = {}

	if contactData is None:
		rollNumberContactMap = {}
	else:
		rollNumberContactMap = dict(contactData)

	return rollNumberContactMap

def getRollNumberMotherContactMapping():
	contactData = query_db('select rollNumber, mobileMother from student_details;')

	rollNumberContactMap = {}

	if contactData is None:
		rollNumberContactMap = {}
	else:
		rollNumberContactMap = dict(contactData)

	return rollNumberContactMap

def getRollNumberFatherContactMapping():
	contactData = query_db('select rollNumber, mobileFather from student_details;')

	rollNumberContactMap = {}

	if contactData is None:
		rollNumberContactMap = {}
	else:
		rollNumberContactMap = dict(contactData)

	return rollNumberContactMap

def getRollNumberHostelMapping():
	hostelRoomIDData = query_db('select userID, hostelRoomID from hostel_log where active=1;')
	roomHostelMapping = query_db('select hostelRoomID, hostelID from hostel_details;')
	hostelData = query_db('select hostelID, hostelName from hostel_data;')
	
	if roomHostelMapping is None:
		roomHostelMapping = {}
	else:
		roomHostelMapping = dict(roomHostelMapping)
	if hostelData is None:
		hostelData = {}
	else:
		hostelData = dict(hostelData)
	if hostelRoomIDData is None:
		hostelRoomIDData = {}
	else:
		hostelRoomIDData = dict(hostelRoomIDData)

	rollNumberHostelMap = {}

	for key, value in hostelRoomIDData.items() :
		rollNumberHostelMap[key] = hostelData[roomHostelMapping[value]]


	return rollNumberHostelMap

def getRollNumberRoomNumberMapping():

	hostelRoomIDData = query_db('select userID, hostelRoomID from hostel_log where active=1;')
	roomData = query_db('select hostelRoomID, roomNumber from hostel_details;')
	if roomData is None:
		roomData = {}
	else:
		roomData = dict(roomData)
	if hostelRoomIDData is None:
		hostelRoomIDData = {}
	else:
		hostelRoomIDData = dict(hostelRoomIDData)

	rollNumberRoomNumberMap = {}

	for key, value in hostelRoomIDData.items():
		rollNumberRoomNumberMap[key] = roomData[value]

	return rollNumberRoomNumberMap


# Get permissions report
def generatePermissionsReport(status) :

	query = "select * from permissions where status in ({status})".format(status=status)
	permissions = query_db(query)

	if permissions is None:
		permissions = []
	else:
		permissions=list(permissions)

	rollNumberNameMap = getRollNumberNameMapping()
	rollNumberHostelMap = getRollNumberHostelMapping()
	rollNumberRoomNmberMap = getRollNumberRoomNumberMapping()
	rollNumberStudentContactMap = getRollNumberStudentContactMapping()
	rollNumberMotherContactMap = getRollNumberMotherContactMapping()
	rollNumberFatherContactMap = getRollNumberFatherContactMapping()
	permissionStatusMap = getPermissionStatusMapping()


	curDateTime = datetime.now(IST).strftime("%d-%m-%Y-%H-%M-%S")
	filename = "permissionsReport-"+str(curDateTime)+".csv"
	count=0
	with open('app/static/permissionReports/'+filename, 'w') as csvfile:

		fieldnames = ['S.No.', 'Roll Number', 'Name', 'Hostel', 'Room Number', 'Permission Date', 'Permission Out Time', 'Actual Out Time', 'Permission In Time', 'Actual In Time', 'Reason', 'Location', 'Status', 'Student Contact Number', 'Father Contact Number', 'Mother Contact Number',]
		writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
		writer.writeheader()

		for permission in permissions :
			count = count + 1
			rollNumber = permission[1]
		
			if permission[12] is None:
				inTime = "Not Available"
			else:
				inTime = permission[12]

			if permission[13] is None:
				outTime = "Not Available"
			else:
				outTime = permission[13]
			
			data = {'S.No.' : count, 'Roll Number' : rollNumber, 'Name' : rollNumberNameMap[rollNumber], 'Hostel' : rollNumberHostelMap[rollNumber], 'Room Number' : rollNumberRoomNmberMap[rollNumber], 'Permission Date' : permission[2],'Permission Out Time' : permission[3], 'Actual Out Time' : outTime, 'Permission In Time' : permission[4], 'Actual In Time' : inTime, 'Reason' : permission[5], 'Location' : permission[6], 'Status' : permissionStatusMap[permission[7]], 'Student Contact Number' : rollNumberStudentContactMap[rollNumber], 'Father Contact Number' : rollNumberFatherContactMap[rollNumber], 'Mother Contact Number' : rollNumberMotherContactMap[rollNumber]}
			writer.writerow(data)
		csvfile.close()
		data = pd.read_csv("app/static/permissionReports/"+filename)
		filename = "permissionsReport-"+str(curDateTime)+".xlsx"
		data.to_excel("app/static/permissionReports/"+filename, index=None, header=True)
	return filename

# END

# Create query for complaints report
def createQueryForComplaintsReport(hostelID,typeOfComplaint,status,inHouse,hostelComplaint):
	queryStart = "select * from cms "
	queryEnd = " order by complaintID desc;"
	addedWhere = 0
	
	if hostelID != "all":
		if addedWhere == 0:
			queryStart = queryStart + " where " + " hostelID={hostelID} ".format(hostelID=hostelID)
			addedWhere = 1 
		else:
			queryStart = queryStart + " and " + " hostelID={hostelID} ".format(hostelID=hostelID)
	
	if typeOfComplaint != "all":
		if addedWhere == 0:
			queryStart = queryStart + " where " + " type='{type}' ".format(type=typeOfComplaint)
			addedWhere = 1 
		else:
			queryStart = queryStart + " and " + " type='{type}' ".format(type=typeOfComplaint)
	
	if status != "all":
		if addedWhere == 0:
			queryStart = queryStart + " where " + " status in ({status}) ".format(status=status)
			addedWhere = 1 
		else:
			queryStart = queryStart + " and " + " status in ({status}) ".format(status=status)
	
	if inHouse != "-1":
		if addedWhere == 0:
			queryStart = queryStart + " where " + " inHouse={inHouse} ".format(inHouse=inHouse)
			addedWhere = 1 
		else:
			queryStart = queryStart + " and " + " inHouse={inHouse} ".format(inHouse=inHouse)
	
	if hostelComplaint != "-1":
		if addedWhere == 0:
			queryStart = queryStart + " where " + " deleted in ({hostelComplaint}) ".format(hostelComplaint=hostelComplaint)
			addedWhere = 1 
		else:
			queryStart = queryStart + " and " + " deleted in ({hostelComplaint}) ".format(hostelComplaint=hostelComplaint)
	else:
		if addedWhere == 0:
			queryStart = queryStart + " where " + " deleted in ({hostelComplaint}) ".format(hostelComplaint="0,2")
			addedWhere = 1 
		else:
			queryStart = queryStart + " and " + " deleted in ({hostelComplaint}) ".format(hostelComplaint="0,2")
	query = queryStart + queryEnd
	return query

# generate report on server
def generateComplaintsReportOnServer(fileName,startDate,endDate,reportFormat,allData,hostelData,roomData,workerData):
	
	hostels = {}
	count = 0
	with open('app/static/complaintReports/'+fileName, 'w') as csvfile:
		fieldnames = ['S.No', 'Complaint ID', 'Date', 'Time', 'Pending Since (days)', 'Roll number/ User ID', 'Hostel', 'Room No', 'Complaint Type', 'Subject', 'Student Remarks', 'Status', 'Availability Date 1', 'From Time 1', 'To Time 1', 'Availability Date 2', 'From Time 2', 'To Time 2', 'Availability Date 3', 'From Time 3', 'To Time 3', 'Worker', 'Severity', ]
		if reportFormat == "1":
			fieldnames = ['S.No', 'Complaint ID', 'Date', 'Time', 'Pending Since (days)', 'Roll number/ User ID', 'Hostel', 'Room No', 'Complaint Type', 'Subject', 'Student Remarks', 'Status', 'Availability Date 1', 'From Time 1', 'To Time 1', 'Availability Date 2', 'From Time 2', 'To Time 2', 'Availability Date 3', 'From Time 3', 'To Time 3', 'Worker', 'Severity','Date Completed' ,'Feedback', 'In house', ]
		writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
		writer.writeheader()
		for record in allData:
			complaintId = record[0]
			userId = record[1]
			hostelName = hostelData[record[9]]
			hostels[record[9]] = 1
			hostelRoom = roomData[record[2]]
			complaintType = record[3]
			subject = record[4]
			remarksStudent = record[5]
			time = record[6]
			status = record[7]
			availabilityTime = record[10]
			feedback=record[12]
			complaintDate = date(int(record[13].split('-')[2]),int(record[13].split('-')[1]),int(record[13].split('-')[0]))
			curDate = datetime.now(IST).strftime("%d-%m-%Y")
			pendDays = (date(int(curDate.split('-')[2]),int(curDate.split('-')[1]),int(curDate.split('-')[0])) - date(int(record[13].split('-')[2]),int(record[13].split('-')[1]),int(record[13].split('-')[0]))).days
			workerId = record[14]
			worker = "Not Available"
			if record[17]==1:
				inHouse="Yes"
			else:
				inHouse="No"
			if workerId in workerData.keys():
				worker = workerData[workerId]
			dateCompleted=record[15]
			severity = record[16]
			if record[7] == 4:
				status = "Active and alloted to worker"
				dateCompleted = "NA"
			elif record[7] == 3:
				status = "Pending allotment to worker"
				dateCompleted = "NA"
			elif record[7]==0:
				status="Pending Approval"
				dateCompleted = "NA"
			elif record[7] in [5,6,7,8]:
				pendDays = "NA"
				status = "Completed"
			elif record[7] in [1,9]:
				status="Discarded"
				pendDays = "NA"
				dateCompleted = "Discarded"
			elif record[7] == 2:
				status = "Being handled In-House"
				dateCompleted = "NA"
			else:
				continue
			if availabilityTime is not None:
				if availabilityTime=="Hostel Complaint":
					date1="ANY DAY"
					fromTime1="ANY TIME"
					toTime1="-"
					date2="ANY DAY"
					fromTime2="ANY TIME"
					toTime2="-"
					date3="ANY DAY"
					fromTime3="ANY TIME"
					toTime3="-"
				else:
					res=availabilityTime.split('###')
					res0=res[0].split('=')
					res1=res[1].split('=')
					res2=res[2].split('=')
					date1=res0[0]
					fromTime1=res0[1]
					toTime1=res0[2]
					date2=res1[0]
					fromTime2=res1[1]
					toTime2=res1[2]
					date3=res2[0]
					fromTime3=res2[1]
					toTime3=res2[2]
			count += 1
			if reportFormat == "1":
				data = {'S.No' : count, 'Complaint ID' : complaintId, 'Date' : complaintDate, 'Time' : time, 'Pending Since (days)' : pendDays, 'Roll number/ User ID' : userId, 'Hostel' : hostelName, 'Room No' : hostelRoom, 'Complaint Type' : complaintType, 'Subject' : subject, 'Student Remarks' : remarksStudent, 'Status' : status, 'Availability Date 1' : date1, 'From Time 1' : fromTime1, 'To Time 1' : toTime1, 'Availability Date 2' : date2, 'From Time 2' : fromTime2, 'To Time 2' : toTime2, 'Availability Date 3' : date3, 'From Time 3' : fromTime3, 'To Time 3' : toTime3, 'Worker' : worker, 'Severity' : severity, 'Date Completed' : dateCompleted ,'Feedback' : feedback, 'In house' : inHouse}
				if complaintDate>=startDate and complaintDate<=endDate:
						writer.writerow(data)
			else:
				data = {'S.No' : count, 'Complaint ID' : complaintId, 'Date' : complaintDate, 'Time' : time, 'Pending Since (days)' : pendDays, 'Roll number/ User ID' : userId, 'Hostel' : hostelName, 'Room No' : hostelRoom, 'Complaint Type' : complaintType, 'Subject' : subject, 'Student Remarks' : remarksStudent, 'Status' : status, 'Availability Date 1' : date1, 'From Time 1' : fromTime1, 'To Time 1' : toTime1, 'Availability Date 2' : date2, 'From Time 2' : fromTime2, 'To Time 2' : toTime2, 'Availability Date 3' : date3, 'From Time 3' : fromTime3, 'To Time 3' : toTime3, 'Worker' : worker, 'Severity' : severity}
				writer.writerow(data)
		csvfile.close()
	return count,hostels

# convert csv to excel 
def convertCsvToExcel(fileName):
	data = pd.read_csv("app/static/complaintReports/"+fileName)
	newName = fileName.split(".")[0] + ".xlsx"
	data.to_excel("app/static/complaintReports/"+newName, index=None, header=True)
	return newName		