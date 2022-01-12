from app import *
from app.helperFunctions import *
from app.views.guard import BASE_URL
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
from datetime import date
import subprocess
import string
import secrets
import pytz 
IST = pytz.timezone('Asia/Kolkata')

configData = getConfigsFromJson()
admin = Blueprint('admin', __name__, url_prefix='/admin') 
BASE_URL = configData["BASE_URL"]
	
# Login Page
@admin.route('/', methods=['GET','POST'])
def home():
	user = getCurrentAdminUser()
	userIP = str(request.remote_addr)
	storeIP(userIP,"AdminLoginPage")
	try:
		if user:
			return redirect(url_for('admin.dashboard'))
		if request.method == 'POST':
			employeeID = request.form['admin-login-employeeID']
			password = hashlib.md5(request.form['admin-login-password'].encode())
			result=None
			result = query_db("select * from login_admin where employeeID=%s;",(employeeID,))
			if result:
				if result[0][1]==password.hexdigest():
					session['employeeID']=employeeID
					session['whatIsMyRole']=configData["adminRole"]
					return redirect(url_for('admin.dashboard'))
				else:
					return render_template('admin/login.html',loginFlag=0)
			else:
				return render_template('admin/login.html',loginFlag=0)
		else:
			return render_template('admin/login.html',loginFlag=1)
	except Exception as e:
		return redirect(url_for('admin.home'))

# Dashboard
@admin.route('/dashboard', methods=['GET'])
def dashboard():
	user=getCurrentAdminUser()
	if user:
		return redirect(url_for('admin.userProfile'))
	else:
		return redirect(url_for('admin.home'))

# Display hostel Data	
@admin.route('/hostel-data', methods=["POST","GET"])
def hostelData():
	user=getCurrentAdminUser()
	
	if user:
		userIP = str(request.remote_addr)
		storeIP(userIP,"AdminHostelData",user[0][0])
		employeeDetails=query_db("select * from admin_details where employeeID=%s;",(user[0][0],))
		wardenDetails=query_db('select * from warden_details order by hostelID;')
		caretakerDetails=query_db('select * from caretaker_details order by hostelID;')
		nightCaretakerDetails=query_db('select * from night_caretaker_details order by hostelID;')
		
		wardenData=[]
		for i in range(len(wardenDetails)):
			hostelID=wardenDetails[i][6]
			hostel=(query_db("select hostelName from hostel_data where hostelID=%s;",(hostelID,)))[0][0]
			if hostel == 'TEST':
				continue
			name=wardenDetails[i][1]+" "+wardenDetails[i][2] 
			gender=wardenDetails[i][3]
			contact=wardenDetails[i][4]
			email=wardenDetails[i][8]
			personalEmail=wardenDetails[i][7]
			warden=[hostel,name,gender,contact,email,personalEmail]
			wardenData.append(warden)
			
		caretakerData=[]
		for i in range(len(caretakerDetails)):
			hostelID=caretakerDetails[i][6]
			hostel=(query_db("select hostelName from hostel_data where hostelID=%s;",(hostelID,)))[0][0]
			if hostel == 'TEST':
				continue
			name=caretakerDetails[i][1]
			gender=caretakerDetails[i][3]
			contact=caretakerDetails[i][4]
			email=caretakerDetails[i][7]
			caretaker=[hostel,name,gender,contact,email]
			caretakerData.append(caretaker)
			
		nightCaretakerData=[]
		for i in range(len(nightCaretakerDetails)):
			hostelID=nightCaretakerDetails[i][6]
			hostel=(query_db("select hostelName from hostel_data where hostelID=%s;",(hostelID,)))[0][0]
			if hostel == 'TEST':
				continue
			name=nightCaretakerDetails[i][1]
			gender=nightCaretakerDetails[i][3]
			contact=nightCaretakerDetails[i][4]
			email=nightCaretakerDetails[i][7]
			nightCaretaker=[hostel,name,gender,contact,email]
			nightCaretakerData.append(nightCaretaker)
		
		
		return render_template('admin/hostel-data.html',user=employeeDetails,wardenData=wardenData,caretakerData=caretakerData,nightCaretakerData=nightCaretakerData)
	else:
		return redirect(url_for('admin.home'))
		
# Generate Report
@admin.route('/generate-report', methods=["POST","GET"])
def generateReport():
	user=getCurrentAdminUser()
	
	if user:
		userIP = str(request.remote_addr)
		storeIP(userIP,"AdminGenerateReport",user[0][0])
		AuthenticationHeader = {'Authorization':configData["AuthorizationToken"]}
		employeeDetails=query_db("select * from admin_details where employeeID=%s;",(user[0][0],))
		
		if request.method=="GET":
			
			# Get all hostel data
			hostelData = query_db('select hostelID, hostelName from hostel_data;')
			
			# Get complaint types
			getComplaintTypesUrl = BASE_URL + "getComplaintTypes"
			response = requests.request("GET", getComplaintTypesUrl, headers=AuthenticationHeader)
			complaintTypes = response.json()["complaintTypes"]
			
			return render_template('admin/generateReport.html',user=employeeDetails, hostelList=hostelData, complaintTypes=complaintTypes)
		
		elif request.method=="POST":

			startDate=request.form['startDate']
			endDate=request.form['endDate']
			typeOfComplaint = request.form['type-of-complaint']
			statusCheck = request.form['status']
			hostelID = request.form['select-hostel']
			
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
			payload={'startDate': startDate,'endDate': endDate, 'hostelID' : hostelID,'typeOfComplaint': typeOfComplaint,'status': status,'inHouse': '-1','hostelComplaint': '-1','fileName': fileName,'reportFormat': '1'}
			response = requests.request("POST", createComplaintsReportUrl, headers=AuthenticationHeader, data=payload)
        
			return send_file('static/complaintReports/'+fileName, mimetype='text/csv', attachment_filename='complaintsReport.csv',as_attachment=True)
	else:
		return redirect(url_for('admin.home'))

@admin.route('/complaints-data', methods=['GET', 'POST'])
def complaintsData():
	user=getCurrentAdminUser()
	
	if user:
		userIP = str(request.remote_addr)
		storeIP(userIP,"AdminComplaintsData",user[0][0])
		userDetails=(query_db("select firstName, lastName from admin_details where employeeID=%s;",(user[0][0],)))
		pendingDB = (query_db("select * from cms where deleted<>1 and status in (0);"))
		activeDB = (query_db("select * from cms where deleted<>1 and status in (2,3,4);"))
		completedDB = (query_db("select * from cms where deleted<>1 and status in (1,5,6,7,8);"))
		hostels = list(query_db("select hostelID, hostelName from hostel_data;"))
		pendingApprovals = {}
		activeComplaints = {}
		completedComplaints = {}
		if pendingDB is None:
			pendingDB = []
		if activeDB is None:
			activeDB = []
		if completedDB is None:
			completedDB = []
		sd = "NULL"
		ed = "NULL"
		if request.method=="POST":
			sd = request.form['startDate']
			ed = request.form['endDate']
			startDate=date(int(request.form['startDate'].split('-')[2]),int(request.form['startDate'].split('-')[1]),int(request.form['startDate'].split('-')[0]))
			endDate=date(int(request.form['endDate'].split('-')[2]),int(request.form['endDate'].split('-')[1]),int(request.form['endDate'].split('-')[0]))
			for record in pendingDB:
				complaintDate=date(int(record[13].split('-')[2]),int(record[13].split('-')[1]),int(record[13].split('-')[0]))
				if complaintDate<startDate or complaintDate>endDate:
					continue
				if record[9] in pendingApprovals:
					pendingApprovals[record[9]]+=1
				else:
					pendingApprovals[record[9]]=1
			for record in activeDB:
				complaintDate=date(int(record[13].split('-')[2]),int(record[13].split('-')[1]),int(record[13].split('-')[0]))
				if complaintDate<startDate or complaintDate>endDate:
					continue
				if record[9] in activeComplaints:
					activeComplaints[record[9]]+=1
				else:
					activeComplaints[record[9]]=1
			for record in completedDB:
				complaintDate=date(int(record[13].split('-')[2]),int(record[13].split('-')[1]),int(record[13].split('-')[0]))
				if complaintDate<startDate or complaintDate>endDate:
					continue
				if record[9] in completedComplaints:
					completedComplaints[record[9]]+=1
				else:
					completedComplaints[record[9]]=1
		if request.method=="GET":
			for record in pendingDB:
				if record[9] in pendingApprovals:
					pendingApprovals[record[9]]+=1
				else:
					pendingApprovals[record[9]]=1
			for record in activeDB:
				if record[9] in activeComplaints:
					activeComplaints[record[9]]+=1
				else:
					activeComplaints[record[9]]=1
			for record in completedDB:
				if record[9] in completedComplaints:
					completedComplaints[record[9]]+=1
				else:
					completedComplaints[record[9]]=1


		complaints=[]
		for hostel in hostels:
				complaint=[]
				if hostel[1]=="TEST":
					continue
				complaint.append(hostel[1])
				if hostel[0] in pendingApprovals:
					complaint.append(pendingApprovals[hostel[0]])
				else:
					complaint.append(0)

				if hostel[0] in activeComplaints:
					complaint.append(activeComplaints[hostel[0]])
				else:
					complaint.append(0)

				if hostel[0] in completedComplaints:
					complaint.append(completedComplaints[hostel[0]])
				else:
					complaint.append(0)

				complaints.append(complaint)

		return render_template('admin/complaintsData.html',user=userDetails,complaints=complaints, sd=sd, ed=ed)
	else:
		return redirect(url_for('admin.home'))
			
		
@admin.route('/user-profile', methods=['GET', 'POST'])
def userProfile():
	user=getCurrentAdminUser()
	cur = mysql.connection.cursor()
	
	if user:
		userIP = str(request.remote_addr)
		storeIP(userIP,"AdminUserProfile",user[0][0])
		
		userDetails=(query_db("select firstName, lastName from admin_details where employeeID=%s;",(user[0][0],)))
			
		if request.method=='GET':
			return render_template('admin/userProfile.html',employeeID = user[0][0],user=userDetails,passwordCheck=0,success=0)
		if request.method=='POST':
			if request.form['submit']=='Change Password':
				oldPassword = hashlib.md5(request.form['employee-old-password'].encode())
				newPassword = hashlib.md5(request.form['employee-new-password'].encode())
				result = query_db("select * from login_admin where employeeID=%s;",(user[0][0],))
				if result[0][1]==oldPassword.hexdigest():
					cur.execute("update login_admin set password=%s where employeeID=%s;", (newPassword.hexdigest(),user[0][0],))
					mysql.connection.commit()
					return render_template('admin/userProfile.html',employeeID = user[0][0],user=userDetails,passwordCheck=0,success=1)
				else:
					return render_template('admin/userProfile.html',employeeID = user[0][0],user=userDetails,passwordCheck=1,success=0)
			
	else:
		return redirect(url_for('admin.home'))
	cur.close()
		
@admin.route('/forgot-password', methods=['GET','POST'])
def forgotPassword():
	cur = mysql.connection.cursor()
	userIP = str(request.remote_addr)
	storeIP(userIP,"AdminForgetPassword")
	if request.method=='GET':
		return render_template('admin/forgotPassword.html',detailsCheck=0,success=0)
	if request.method=='POST':
		employeeID = request.form['employee-id']
		emailX= request.form['employee-email']
		employeeResult = query_db("select * from login_admin where employeeID=%s;", (employeeID,))
		if employeeResult is not None:
			emailResult = query_db("select email from admin_details where employeeID=%s;",(employeeID,))
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
				curDateTime = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
				mailSubject="Hostel Webkiosk Password Reset Requested at "+str(curDateTime)
				if email(mailBody,mailSubject,emailX)=="OK":
					cur.execute("update login_admin set password=%s where employeeID=%s;", (hashlib.md5(password.encode()).hexdigest(),employeeID,))
					mysql.connection.commit()
					return render_template('admin/forgotPassword.html',detailsCheck=0,success=1)
				else:
					return render_template('admin/forgotPassword.html',detailsCheck=0,success=0) 
			else:
				return render_template('admin/forgotPassword.html',detailsCheck=1,success=0)
		else:
			return render_template('admin/forgotPassword.html',detailsCheck=1,success=0)
	cur.close()


@admin.route('/logout')
def logout():
	user = getCurrentAdminUser()
	if user:
		session.pop('employeeID', None)
		session.pop('whatIsMyRole', None)
		return redirect(url_for('admin.home'))
	else:
		return redirect(url_for('admin.home'))

