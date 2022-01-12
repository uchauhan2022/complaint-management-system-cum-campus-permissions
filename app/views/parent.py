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

configData = getConfigsFromJson()
parent = Blueprint('parent', __name__, url_prefix='/parent') 
BASE_URL = configData["BASE_URL"]

#Login page
@parent.route('/', methods=['GET','POST'])
def home():
	user = getCurrentParentUser()
	if user:
		return redirect(url_for('parent.dashboard'))
	if request.method == 'POST':
		parentID = request.form['parent-login-userID']
		password = hashlib.md5(request.form['parent-login-password'].encode())
		result = query_db("select * from login_parent where userID=%s;",(parentID,))
		if result is not None:
			if result[0][1]==password.hexdigest():
				session['parentID']=parentID
				return redirect(url_for('parent.dashboard'))
			else:
				return render_template('parent/login.html',loginFlag=0)
		else:
			return render_template('parent/login.html',loginFlag=0)
	else:
		return render_template('parent/login.html',loginFlag=1)


# Dashboard
@parent.route('/dashboard', methods=['GET'])
def dashboard():
	user=getCurrentParentUser()
	if user:
		return redirect(url_for('parent.permissions'))
	else:
		return redirect(url_for('parent.home'))

@parent.route('/permissions', methods=['GET','POST'])
def permissions():
	user = getCurrentParentUser()
	cur = mysql.connection.cursor()
	if user:
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
			return render_template('/parent/permissions.html', user = userDetails, requestedPermissionsList = requestedPermissionsList, activePermissionsList = activePermissionsList, expiredPermissionsList = expiredPermissionsList, appActivation = permissionsAppActivated, invalidTime = 0, inTime = inTime, outTime = outTime, rulesInformation = rulesInformation)
		
		if request.method=='POST':
			#approve permission
			if request.form['submit'].split(':')[0]=='acceptPermission':
				permissionId = request.form['submit'].split(':')[1]
				url = BASE_URL+"acceptPermission"
				payload={"permissionId":permissionId}
				headers = {'Authorization': configData["AuthorizationToken"]}
				response = requests.request("POST", url, headers=headers, data=payload)
				return redirect(url_for("parent.permissions"))
				
			#reject permission
			elif request.form['submit'].split(':')[0]=='rejectPermission':
				permissionId = request.form['submit'].split(':')[1]
				url = BASE_URL+"rejectPermission"
				payload={"permissionId":permissionId}
				headers = {'Authorization': configData["AuthorizationToken"]}
				response = requests.request("POST", url, headers=headers, data=payload)
				return redirect(url_for("parent.permissions"))
	else:
		return redirect(url_for('parent.home'))
	cur.close()

@parent.route('/forgot-password', methods=['GET','POST'])
def forgotPassword():
	pass

@parent.route('/logout')
def logout():
    user = getCurrentParentUser()
    if user:
        session.pop('parentID', None)
        return redirect(url_for('parent.home'))
    else:
        return redirect(url_for('parent.home'))