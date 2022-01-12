from app import *
from app.views.guard import BASE_URL
from flask import (Blueprint, Flask, flash, g, redirect, render_template,
                   request, send_file, session, url_for)
from flask_mysqldb import MySQL
import hashlib
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import re
import csv
from datetime import date
import json
from flask_httpauth import HTTPBasicAuth
import hashlib
import pandas as pd
from app.helperFunctions import *
import pytz 
IST = pytz.timezone('Asia/Kolkata')

configData = getConfigsFromJson()
BASE_URL = configData["BASE_URL"]
cronController = Blueprint('cronController', __name__, url_prefix='/cron') 
auth = HTTPBasicAuth()

# CRONS 
# 58 23 * * * curl -X POST http://13.235.245.38:3006/cron/refreshApprovals --header 'Authorization: Basic Y2Fwc3RvbmU6Q2Fwc3RvbmVANTQzMjEj'
# 59 23 * * * curl -X POST http://13.235.245.38:3006/cron/mail --header 'Authorization: Basic Y2Fwc3RvbmU6Q2Fwc3RvbmVANTQzMjEj'
# */1 * * * * curl -X POST 'http://13.235.245.38:3006/cron/allot' --header 'Authorization: Basic Y2Fwc3RvbmU6Q2Fwc3RvbmVANTQzMjEj'
# 30 0 * * * curl -X POST http://13.235.245.38:3006/hostel/cmsMail
# */30 * * * * curl -X POST http://13.235.245.38:3006/cron/dbSync --header 'Authorization: Basic Y2Fwc3RvbmU6Q2Fwc3RvbmVANTQzMjEj'
# 0 0 * * * curl -X POST http://13.235.245.38:3006/cron/deleteComplaintReports --header 'Authorization: Basic Y2Fwc3RvbmU6Q2Fwc3RvbmVANTQzMjEj'

# Verify Authentication
@auth.verify_password
def verify_password(username, password):
	hashedPass = hashlib.md5(password.encode())
	if username==configData["AuthorizationUsername"] and configData["AuthorizationPassword"]==hashedPass.hexdigest():
		return username

#webhook for auto pull
@cronController.route("/autoPull", methods=['POST'])
def autoPull():
    try:
        os.system("sudo git pull")
        return "SUCCESS",200
    except:
        return "FAIL",200


# Cronjob to send complaint feedback reminders to students and
# updates if the complaint has been auto approved
# CRON : 58 23 * * * curl -X POST http://13.235.245.38:3006/cron/refreshApprovals (add authorization in header)
@cronController.route("/refreshApprovals", methods=['POST'])
@auth.login_required
def refreshApprovals():
    cur=mysql.connection.cursor()
    try:
        listOfComplaints = query_db('select complaintID,subject,userID,dateCompleted from cms where status in (5) and deleted<>2;')
        if listOfComplaints is None:
            listOfComplaints = []
        for complaint in listOfComplaints:
            complainID = complaint[0]
            complaintDesc = complaint[1]
            userID=complaint[2]
            dateOfComplaint = complaint[3]
            curDate = date.today()
            complaintDate = date.today()
            if dateOfComplaint== None:
                complaintDate=curDate
            else:
                dateOfComplaint=str(dateOfComplaint)
                complaintDate = date(int(dateOfComplaint.split('-')[2]),int(dateOfComplaint.split('-')[1]),int(dateOfComplaint.split('-')[0]))
            deltaOfDates = curDate-complaintDate
            if(deltaOfDates.days==2):
                body='''Dear Student,
Your Complaint with Complaint ID = {complainID} and Subject : '{complaintDesc}' awaits a feedback.
Incase you fail to provide a feedback by today, it shall be auto-approved by the system.
Please check your dashboard at http://cmmstiet.in for further details.
Thank You!\n\n
THIS IS AN AUTOMATED MESSAGE PLEASE DO NOT REPLY.'''.format(complainID = complainID, complaintDesc = complaintDesc)
                subject = "Complaint feedback required for complaintID:"+str(complainID)
                print(body)
                emailViaUserID(body,subject,userID)
            if(deltaOfDates.days>3):
                cur.execute('update cms set status=7 where complaintID=%s;',(complainID,))
                mysql.connection.commit()
                body='''Dear Student,
Your Complaint with Complaint ID = {complainID} and Subject : '{complaintDesc}' has been auto-approved.
Please check your dashboard at http://cmmstiet.in for further details.
Thank You!\n\n
THIS IS AN AUTOMATED MESSAGE PLEASE DO NOT REPLY.'''.format(complainID = complainID, complaintDesc = complaintDesc)
                subject = "Complaint Auto-approved (complaintID:"+str(complainID)+")"
                print(body)
                emailViaUserID(body,subject,userID)
        cur.close()
        return "OK", 200
    except:
        cur.close()
        sendFailureMessage("refreshApprovals")
        return "Internal Server Error",500


# Syncs the Databse
# CRON : */30 * * * * curl -X POST http://13.235.245.38:3006/cron/dbSync (add authentication headers)
@cronController.route("/dbSync", methods=['POST'])
@auth.login_required
def dbSync():
    try:
        os.system("python3 database\ updation/dbSyncAutomated.py")
        return "OK", 200
    except:
        sendFailureMessage("dbSync")
        return "Internal Server Error",500

# Allots worker automatically
# */2 * * * * curl -X POST 'http://13.235.245.38:3006/cron/allot' (add authentication headers)
@cronController.route("/allot", methods=['POST'])
@auth.login_required
def allot():
    try:
        cur=mysql.connection.cursor()
        cur.execute("update cms set status=4 where status=3;")
        mysql.connection.commit()
        cur.close()
        return "OK", 200
    except:
        sendFailureMessage("allot")
        return "Internal Server Error",500

# Deletes the complaint reports from server
# 0 0 * * * curl -X POST http://13.235.245.38:3006/cron/deleteComplaintReports (add authentication headers)
@cronController.route("/deleteComplaintReports", methods=['POST'])
@auth.login_required
def deleteComplaintReports():
    try:
        directory = "app/static/complaintReports"
        files_in_directory = os.listdir(directory)
        filtered_files = [file for file in files_in_directory if file.endswith(".csv")]
        for file in filtered_files:
            path_to_file = os.path.join(directory, file)
            os.remove(path_to_file)
        files_in_directory = os.listdir(directory)
        filtered_files = [file for file in files_in_directory if file.endswith(".xlsx")]
        for file in filtered_files:
            path_to_file = os.path.join(directory, file)
            os.remove(path_to_file)
        return "OK", 200
    except:
        sendFailureMessage("deleteComplaintReports")
        return "Internal Server Error",500

# Mail to caretakers everyday about count of pending complaints
# 59 23 * * * curl -X POST http://13.235.245.38:3006/cron/mail (add authentication headers)
@cronController.route("/mail", methods=['POST'])
@auth.login_required
def refreshMails():
    try:
        hostelList=query_db('select hostelID, caretakerID from hostel_data;')
        if hostelList is None:
            hostelList=[]
        for hostel in hostelList:
            hostelID = hostel[0]
            caretakerID = hostel[1]
            pendingApprovals = query_db("select * from cms where status=0 and deleted=0 and hostelID=%s",(hostelID,))
            if pendingApprovals is None:
                pendingApprovals=[]
            count = len(pendingApprovals)
            if count>0:
                caretakerEmail = query_db("select email from caretaker_details where userID=%s",(caretakerID,))[0][0]
                curDateTime = datetime.now(IST).strftime("%d-%m-%Y")
                subject = "Pending Complaint Approvals as of "+str(curDateTime)
                body = "Dear Hostel Caretaker,\n\nKindly approve the student complaints on CMMS website. Number of remaining complaints = "+str(count)+". \nPlease visit http://cmmstiet.in/hostel for the same.\nTHIS IS AN AUTOMATED MESSAGE- PLEASE DO NOT REPLY.\n\nThank you!"
                email(body,subject,caretakerEmail)
        return "OK", 200
    except:
        sendFailureMessage("mail")
        return "Internal Server Error",500

# Mail to cms department
# 30 0 * * * curl -X POST http://13.235.245.38:3006/hostel/cron/cmsMail (add authentication headers)
@cronController.route("/cmsMail", methods=['POST'])
@auth.login_required
def cmsMail():
    try:
        curDateTime = datetime.now(IST).strftime("%d-%m-%Y-%H-%M-%S")
        fileName = "complaintsReportMail-" + str(curDateTime) + ".csv"
        
        createComplaintsReportUrl = BASE_URL + "createComplaintsReportOnServer"
        payload={'startDate': '12-02-2021','endDate': '12-02-2021','hostelID': 'all','typeOfComplaint': 'all','status': '3,4','inHouse': '0','hostelComplaint': '-1','fileName': fileName,'reportFormat': '0'}
        AuthenticationHeader = {'Authorization':configData["AuthorizationToken"]}
        response = requests.request("POST", createComplaintsReportUrl, headers=AuthenticationHeader, data=payload)
        listOfHostelsInvolved = list(response.json()["hostels"])
        complaintCount = response.json()["count"]
        excelFileName = convertCsvToExcel(fileName)

        curDate = datetime.now(IST).strftime("%d-%m-%Y")
        subject = "Pending Hostel Complaints till  "+str(curDate)
        body = "Dear Team CMS,\n\nPlease find attached the pending complaints till " +str(curDate)+". Number of remaining complaints = "+str(complaintCount)+". \nKindly resolve them ASAP.\n\nTHIS IS AN AUTOMATED MESSAGE- PLEASE DO NOT REPLY.\n\nThank you!"
        recipients=["chandan.kumar@thapar.edu","sanchit.pachauri@thapar.edu","azharuddin@thapar.edu","ajay@thapar.edu","arvind.gupta@thapar.edu","tarsem.kumar@thapar.edu"]
        cc=["skjain.cms@thapar.edu","harpreet.virdi@thapar.edu","ashish.purohit@thapar.edu"]
        bcc=[]
        
        warden_emails=query_db("Select hostelID, hostelEmail from warden_details;")
        ct_emails=query_db("Select hostelID, email from caretaker_details;")
        for email in ct_emails:
            if email is not None and email[1] is not None and str(email[0]) in listOfHostelsInvolved:
                bcc.append(email[1])
        for email in warden_emails:
            if email is not None and email[1] is not None and str(email[0]) in listOfHostelsInvolved:
                cc.append(email[1])
      
        emailAttach(body,subject,recipients,cc,bcc,"static/complaintReports/"+excelFileName,"CMSReport.xlsx")

        return "OK",200
    except:
        sendFailureMessage("cmsMail")
        return "Internal Server Error",500


# Expire active permissions of previous day at 6am everyday
# 0 6 * * * curl -X POST http://13.235.245.38:3006/cron/expireActivePermissions (add authentication headers)
@cronController.route("/expireActivePermissions", methods=['POST'])
@auth.login_required
def expireActivePermissions():
    cur = mysql.connection.cursor()
    try:
        prevDate=datetime.today() - timedelta(days=1)
        prevDate=datetime.strftime(prevDate,"%d-%m-%Y")
        activePermissions = query_db("select * from permissions where status in (3,4) and permDate = %s;",(prevDate,))
        if activePermissions is None:
            activePermissions=[]
        else:
            activePermissions=list(activePermissions)

        res=""
        
        for permission in activePermissions:
            cur.execute('update permissions set status=7 where permissionID=%s;',(permission[0],))
            mysql.connection.commit()
        return "OK", 200
    except:
        return "Internal Server Error",500

# Expire requested permissions at 9pm everyday
# 0 21 * * * curl -X POST http://13.235.245.38:3006/cron/expireRequestedPermissions (add authentication headers)
@cronController.route("/expireRequestedPermissions", methods=['POST'])
@auth.login_required
def expireRequestedPermissions():
    cur = mysql.connection.cursor()
    try:
        curDate=datetime.today()
        curDate=datetime.strftime(curDate,"%d-%m-%Y")
        requestedPermissions = query_db("select * from permissions where status in (1) and permDate = %s;",(curDate,))
        if requestedPermissions is None:
            requestedPermissions=[]
        else:
            requestedPermissions=list(requestedPermissions)
        
        for permission in requestedPermissions:
            cur.execute("update permissions set status = 2 where permissionID = %s;",(permission[0],))
            mysql.connection.commit()
        return "OK", 200
    except:
        return "Internal Server Error",500

# Mail wardens list of students wh haven't returned at 11pm everyday
# 0 23 * * * curl -X POST http://13.235.245.38:3006/cron/mailWardenStudentsNotReturned (add authentication headers)
@cronController.route("/mailWardenStudentsNotReturned", methods=['POST'])
@auth.login_required
def mailWardenStudentsNotReturned():
    try:
        curDate=datetime.today()
        curDate=datetime.strftime(curDate,"%d-%m-%Y")
        neverReturned = query_db("select * from permissions where status in (4) and permDate = %s;",(curDate,))

        hostelIDs = {}

        if neverReturned is None:
            neverReturned=[]
        else:
            neverReturned=list(neverReturned)
        
        for permission in neverReturned :
            rollNumber = permission[1]
            hostelID = getHostelIDFromRollNumber(rollNumber)
            hostelIDs.add(hostelID)

        subject = "Students not returned on  "+str(curDate)
        body = "Dear Warden,\n\n The following students from your hostel haven't returned back to the campus.. \nTHIS IS AN AUTOMATED MESSAGE- PLEASE DO NOT REPLY.\n\nThank you!"
        recepients = []
        cc = []
        bcc = []
        status = ""
        
        for hostelID in hostelIDs :
            wardenEmail = getWardenEmailViaHostelID(hostelID)
            recepients.append(wardenEmail)
    
        status=status+"4"
        attachmentFileName = generatePermissionsReport(status)
        emailAttach(body, subject, recepients, cc, bcc, "static/permissionReports/"+attachmentFileName, "PermissionsReport.xlsx")

        return "OK", 200
    except:
        return "Internal Server Error",500


# Mail students whose permission time has started
# */15 * * * * curl -X POST http://13.235.245.38:3006/cron/mailStudentsPermissionStarted (add authentication headers)
@cronController.route("/mailStudentsPermissionStarted", methods=['POST'])
@auth.login_required
def mailStudentsPermissionStarted() :
    try:
        curDateTime=datetime.today()
        prevDateTime=datetime.today() - timedelta(minutes=15)
        curDate=datetime.strftime(curDateTime,"%d-%m-%Y")
        curTime=datetime.strftime(curDateTime,"%H:%M")
        prevTime=datetime.strftime(prevDateTime,"%H:%M")

        permStarted = query_db("select * from permissions where permOutTime between %s and %s and status = 1 and permDate = %s;",(prevTime,curTime,curDate,))

        if permStarted is None:
            permStarted = []
        else:
            permStarted = list(permStarted)

        subject = "Permission Started for  "+str(curDate)
        body = "Dear Student,\n\n Your permission for " + str(curDate) + " has started. Kindly delete the permission if you're not going out to avoid any undue action. \nTHIS IS AN AUTOMATED MESSAGE- PLEASE DO NOT REPLY.\n\nThank you!"
        recepients = []

        for perm in permStarted:
            emailID = getStudenEmailViaRollNumber(perm[1])
            recepients.append(emailID)
            email(body,subject,emailID)

            # change email function to receive list of recepeints
        
        return "OK",200
    except:
        return "Internal Server Error",500


# Mail parents of students whose in time has exceeded and change status
# */15 * * * * curl -X POST http://13.235.245.38:3006/cron/inTimeExceeded (add authentication headers)
@cronController.route("/inTimeExceeded", methods=['POST'])
@auth.login_required
def inTimeExceeded() :
    cur = mysql.connection.cursor()
    try:
        curDateTime=datetime.today()
        prevDateTime=datetime.today() - timedelta(minutes=15)
        curDate=datetime.strftime(curDateTime,"%d-%m-%Y")
        curTime=datetime.strftime(curDateTime,"%H:%M")
        prevTime=datetime.strftime(prevDateTime,"%H:%M")

        inTimeExceededPermissions = query_db("select * from permissions where permInTime between %s and %s and status = 3 and permDate = %s;",(prevTime,curTime,curDate,))

        if inTimeExceededPermissions is None:
            inTimeExceededPermissions = []
        else:
            inTimeExceededPermissions = list(inTimeExceededPermissions)

        subject = "Campus In Time ecxeeded for the permission of your wardfor  "+str(curDate)
        
        for perm in inTimeExceededPermissions:

            parentsEmail = getStudenEmailViaRollNumber(perm[1])
            studentName = getStudenNameViaRollNumber(perm[1])
            motherEmail = parentsEmail[0]
            fatherEmail = parentsEmail[1]
            body = "Dear Parent,\n\n Your ward, " + str(studentName) + " hasn't returned back to the campus. The permission In Time was " + str(perm[4]) + " whaich has exceeded. \nTHIS IS AN AUTOMATED MESSAGE- PLEASE DO NOT REPLY.\n\nThank you!"

            cur.execute("update permissions set status = 4 where permissionID = %s;",(perm[0],))
            mysql.connection.commit()

            email(body,subject,motherEmail)
            email(body,subject,fatherEmail)

            # change email function to receive list of recepeints
            # recepients = parentsEmail
        
        return "OK", 200
    except:
        return "Internal Server Error",500