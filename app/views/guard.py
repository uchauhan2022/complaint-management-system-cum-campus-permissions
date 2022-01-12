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
from datetime import date
import pandas as pd
import json
import pytz 
IST = pytz.timezone('Asia/Kolkata')

configData = getConfigsFromJson()
guard = Blueprint('guard', __name__, url_prefix='/guard') 
BASE_URL = configData["BASE_URL"]

#Login page
@guard.route('/', methods=['GET','POST'])
def home():
	user = getCurrentGuardUser()
	if user:
		return redirect(url_for('guard.permissions'))
	if request.method == 'POST':
		guardID = request.form['guard-login-userID']
		password = hashlib.md5(request.form['guard-login-password'].encode())
		result = query_db("select * from login_guard where userID=%s;",(guardID,))
		if result is not None:
			if result[0][1]==password.hexdigest():
				session['guardID']=guardID
				return redirect(url_for('guard.permissions'))
			else:
				return render_template('guard/login.html',loginFlag=0)
		else:
			return render_template('guard/login.html',loginFlag=0)
	else:
		return render_template('guard/login.html',loginFlag=1)


#permissions
@guard.route('/permissions', methods=['GET','POST'])
def permissions():
	user = getCurrentGuardUser()
	cur = mysql.connection.cursor()

	if user:

		#permissionsAdminControl
		permissionsAdminControlUrl = BASE_URL+"getPermissionsAdminControlls"
		permissionsAdminControlHeaders = {'Authorization': configData["AuthorizationToken"]}
		permissionsAdminControlResponse = requests.request("GET", permissionsAdminControlUrl, headers=permissionsAdminControlHeaders)
		permissionsAdminControls = json.loads(permissionsAdminControlResponse.text)
		permissionsAppActivated = permissionsAdminControls["activatePermissionsApp"]
		rulesInformation = permissionsAdminControls["informationToBeDisplayed"]
		inTime = permissionsAdminControls["inTime"]
		outTime = permissionsAdminControls["outTime"]
		studentDetails=[]
		permission=[]

		if request.method == 'GET':
			return render_template('/guard/permissions.html', appActivation = permissionsAppActivated, inTime = inTime, outTime = outTime, studentDetails = studentDetails, permission = permission)


		if request.method == 'POST':
			# fetch permission and student details from roll number
			if request.form['submit'].split(':')[0]=='search':
				rollNumber = request.form["student-roll-number"]
				searchParams = {'rollNumber':rollNumber}
				searchHeaders = {'Authorization': configData["AuthorizationToken"]}

				getStudentDetailsUrl = BASE_URL+"getStudentDetails"

				studentDetailsResponse = requests.request("GET", getStudentDetailsUrl, headers=searchHeaders, params=searchParams)
				studentDetails = mapStudentDetailsToList(studentDetailsResponse.json())
				
				getPermissionUrl = BASE_URL+"getPermission"
				permissionResponse = requests.request("GET", getPermissionUrl, headers=searchHeaders, params=searchParams)
				permission = mapPermissionToList(permissionResponse.json())

				return render_template('/guard/permissions.html', appActivation = permissionsAppActivated, inTime = inTime, outTime = outTime, studentDetails = studentDetails, permission = permission)
			
			elif request.form['submit'].split(':')[0]=='markExit':
				permissionId = request.form['submit'].split(':')[1]
				guardId = user[0][0]
				url = BASE_URL+"markExit"
				payload={"permissionId":permissionId, "guardId":guardId}
				headers = {'Authorization': configData["AuthorizationToken"]}
				response = requests.request("POST", url, headers=headers, data=payload)
				return redirect(url_for("guard.permissions"))


			elif request.form['submit'].split(':')[0]=='markEntry':
				permissionId = request.form['submit'].split(':')[1]
				guardId = user[0][0]
				url = BASE_URL+"markEntry"
				payload={"permissionId":permissionId, "guardId":guardId}
				headers = {'Authorization': configData["AuthorizationToken"]}
				response = requests.request("POST", url, headers=headers, data=payload)
				return redirect(url_for("guard.permissions"))

	else:
		return redirect(url_for('guard.home'))

@guard.route('/forgot-password', methods=['GET','POST'])
def forgotPassword():
	pass

@guard.route('/logout')
def logout():
    user = getCurrentGuardUser()
    if user:
        session.pop('guardID', None)
        return redirect(url_for('guard.home'))
    else:
        return redirect(url_for('guard.home'))