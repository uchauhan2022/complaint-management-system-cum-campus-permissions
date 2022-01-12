import os
from flask import Flask, request, render_template, flash, redirect, url_for, session, Blueprint
from tempfile import mkdtemp
from flask_mysqldb import MySQL
from flask_session import Session
from flask_mail import Mail, Message
import requests



#config
app = Flask(__name__, instance_path=os.path.join(os.path.abspath(os.curdir), 'instance'), instance_relative_config=True, static_url_path="", static_folder="static")
app.config.from_pyfile('config.cfg')
app.config['SESSION_FILE_DIR'] = mkdtemp()
mysql=MySQL(app)
Session(app)

#db
def execute_db(query,args=()):
    try:
        cur=mysql.connection.cursor()
        cur.execute(query,args)
        mysql.connection.commit()
    except:
        mysql.connection.rollback()
    finally:
        cur.close()

def query_db(query,args=(),one=False):
    cur=mysql.connection.cursor()
    result=cur.execute(query,args)
    if result>0:
        values=cur.fetchall()
        return values
    cur.close()

# Importing Blueprints
from app.views.main import main
from app.views.admin import admin
from app.views.hostel import hostel
from app.views.cms import cms
from app.views.apiController import apiController
from app.views.parent import parent
from app.views.guard import guard
from app.views.cronController import cronController

# Registering Blueprints
app.register_blueprint(main)
app.register_blueprint(admin)
app.register_blueprint(hostel)
app.register_blueprint(cms)
app.register_blueprint(apiController)
app.register_blueprint(parent)
app.register_blueprint(guard)
app.register_blueprint(cronController)