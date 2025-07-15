import re
import base64
import gpxpy
import pandas as pd
import folium
import os
import pyrebase
import json

from datetime import datetime
from io import BytesIO
from flask import Flask, request, redirect, url_for, jsonify
from flask import render_template, render_template_string, session, flash
from matplotlib.figure import Figure
from firebase_admin import credentials, firestore, initialize_app, storage
from gpx_class import GPXTracker

import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

app.secret_key = os.urandom(12)

# cred = credentials.Certificate('serviceAccountKey.json')

service_account_json_str = os.environ['FIREBASE_SERVICE_ACCOUNT_JSON']
service_account_info = json.loads(service_account_json_str)

cred = credentials.Certificate(service_account_info)
default_app = initialize_app(cred, { 'storageBucket' : os.environ['FIREBASE_STORAGEBUCKET']})
db = firestore.client()
bucket = storage.bucket()

firebaseConfig = {
  "apiKey": os.environ['FIREBASE_API_KEY'],
  "authDomain": os.environ['FIREBASE_AUTHDOMAIN'],
  "projectId": os.environ['FIREBASE_PROJECTID'],
  "storageBucket": os.environ['FIREBASE_STORAGEBUCKET'],
  "messagingSenderId": os.environ['FIREBASE_MESSAGINGSENDERID'],
  "appId": os.environ['FIREBASE_APPID'],
  "databaseURL": os.environ['FIREBASE_DATABASEURL']
}

firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()
db_real = firebase.database()

person = {"is_logged_in": False, "name": "", "email": "", "uid": ""}

@app.route("/")
def home():

    # url = "http://www.roadrun.co.kr/schedule/list.php"
    # response = requests.get(url)

    # soup = BeautifulSoup(response.content, "html.parser")

    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        return "Hello! <a href='/logout'>Logout</a>"
    # return render_template("home.html")

@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route("/welcome")
def welcome():

    # db_events = db_real.child("events").get().val().values()
    # print(db_events)

    if person["is_logged_in"] == True:
        gpxs_ref = db.collection('gpxs')
        all_gpxs = [doc.to_dict() for doc in gpxs_ref.stream()]

        user_gpx = []
        for x in all_gpxs:
            if person['uid'] == x['creatorId']:
                user_gpx.append(x)

        return render_template("welcome.html", email = person["email"], name = person["name"], gpx = user_gpx)
    else:
        return redirect(url_for('home'))

@app.route('/login', methods=['POST'])
def do_admin_login():
    
    if request.method == "POST":        #Only if data has been posted
        result = request.form           #Get the data
        email = result["username"]
        password = result["password"]
        try:
            #Try signing in the user with the given information
            user = auth.sign_in_with_email_and_password(email, password)
            #Insert the user data in the global person
            global person
            person["is_logged_in"] = True
            person["email"] = user["email"]
            person["uid"] = user["localId"]

            #Get the name of the user
            # data = db_real.child("users").get()
            # person["name"] = data.val()[person["uid"]]["name"]

            #Redirect to welcome page
            return redirect(url_for('welcome'))
        except:
            #If there is any error, redirect back to login
            return redirect(url_for('login'))
    else:
        if person["is_logged_in"] == True:
            return redirect(url_for('welcome'))
        else:
            return redirect(url_for('login'))

@app.route("/logout")
def logout():
    session['logged_in'] = False
    person["is_logged_in"] = False
    return redirect(url_for('home'))

@app.route("/about/")
def about():
    return render_template("about.html")

@app.route("/contact/")
def contact():
    return render_template("contact.html")

@app.route("/hello/")
@app.route("/hello/<name>")
def hello_there(name = None):
    # now = datetime.now()
    # formatted_now = now.strftime("%A, %d %B, %Y at %X")
    # 
    # # Filter the name argument to letters only using regular expressions. URL arguments
    # # can contain arbitrary text, so we restrict to safe characters only.
    # match_object = re.match("[a-zA-Z]+", name)
    # 
    # if match_object:
    #     clean_name = match_object.group(0)
    # else:
    #     clean_name = "Friend"
    # 
    # content = "Hello there, " + clean_name + "! It's " + formatted_now
    #return content
    return render_template(
        "hello_there.html",
        name=name,
        date=datetime.now()
    )

@app.route("/gpxs")
@app.route("/gpxs/<creatorId>")
def gpxs(creatorId=None):
    gpxs_ref = db.collection('gpxs')
    all_gpxs = [doc.to_dict() for doc in gpxs_ref.stream()]

    if creatorId != None:
        user_gpx = []
        for x in all_gpxs:
            if creatorId == x['creatorId']:
                user_gpx.append(x)                
        # return jsonify(user_gpx), 200
        return render_template("gpxs.html", gpx = user_gpx)
    
    # return jsonify(all_gpxs), 200
    return render_template("gpxs.html", gpx = all_gpxs)
    
@app.route("/nweets")
@app.route("/nweets/<id>")
def nweets(id=None):
    nweets_ref = db.collection('nweets')
    all_nweets = [doc.to_dict() for doc in nweets_ref.stream()]
    
    if id != None:
        nweet = nweets_ref.document(id).get()
        return jsonify(nweet.to_dict()), 200
    
    return jsonify(all_nweets), 200
    
@app.route("/nweets", methods=['POST'])
def create():
    # nweet = {"text": "test", "creatorName": "테스터"}
    
    try:
        nweet = request.json
        nweet_ref = db.collection("nweets").add(nweet)
        return jsonify({"success": True}), 200
    
    except Exception as e:
        return f"An Error Occured: {e}"

@app.route('/nweets', methods=['POST', 'PUT'])
def update():
    try:
        nweets_ref = db.collection('nweets')
        
        id = request.json['id']
        nweets_ref.document(id).update(request.json)
        return jsonify({"success": True}), 200
    except Exception as e:
        return f"An Error Occured: {e}"

@app.route('/nweets', methods=['GET', 'DELETE'])
def delete():
    try:
        nweets_ref = db.collection('nweets')
        
        nweet_id = request.args.get('id')
        nweets_ref.document(nweet_id).delete()
        return jsonify({"success": True}), 200
    except Exception as e:
        return f"An Error Occured: {e}"
    
@app.route("/api/data")
def get_data():
    return app.send_static_file("data.json")
    
@app.route("/tracker")
def hello():

    # gpx_tracker = GPXTracker(db);
    
    # route = gpx_tracker.tracker_route();
    # altitude = gpx_tracker.tracker_altitude();
    
    return render_template(
        "tracker.html",
        # tracker_route=f"data:image/png;base64,{route}",
        # tracker_altitude=f"data:image/png;base64,{altitude}"
    )
    
@app.route("/iframe")
@app.route("/iframe/<filepath>")
def iframe(filepath=None):

    if filepath == None:
        return render_template(
            "home.html"
        )
        
    gpx_tracker = GPXTracker(db);
    iframe, total_time = gpx_tracker.tracking(filepath.replace('|','/'));
    
    return render_template(
        "iframe.html",
        iframe=iframe,
        total_time=total_time
    )
    
@app.route('/register', methods=['POST'])
def register():
    if 'file' not in request.files:
        flash('No file part')
        print("no file part")
        
    file = request.files['file']
    
    if file.filename == '':
        flash('No selected file')
        print("no selected file")
    
    #file.save(f'G:\\tmp\\flask_test\\static\\'+file.filename)
    
    dtToday = datetime.today().strftime('%Y%m%d%H%M%S')
    file_path = 'gpx' + '/' + dtToday + '_' +file.filename

    blob = bucket.blob(file_path)
    #blob.upload_from_filename(f'G:\\tmp\\flask_test\\static\\'+file.filename)
    blob.upload_from_string(file.read())

    creator = {"creatorId": "LkcVFWZyjPPrHRurT5fLI6btfAY2", "creatorName": "이준영2", "gpxFilePath": file_path}
    gpx_ref = db.collection("gpxs").add(creator)
    
    return redirect(url_for('iframe', filepath=file_path.replace('/','|')))
    
@app.route("/registeruser", methods = ["POST", "GET"])
def registeruser():
    if request.method == "POST":        #Only listen to POST
        result = request.form           #Get the data submitted
        email = result["email"]
        password = result["pass"]
        name = result["name"]
        try:
            #Try creating the user account using the provided data
            auth.create_user_with_email_and_password(email, password)
            #Login the user
            user = auth.sign_in_with_email_and_password(email, password)
            #Add data to global person
            global person
            person["is_logged_in"] = True
            person["email"] = user["email"]
            person["uid"] = user["localId"]
            person["name"] = name
            #Append data to the firebase realtime database
            data = {"name": name, "email": email}

            db_real.push(data)

            # db_real.child("users").child(person["uid"]).set(data)
            # db_real.child("events").push(data)

            #Go to welcome page
            return redirect(url_for('welcome'))
        except:
            #If there is any error, redirect to register
            return redirect(url_for('registeruser'))

    else:
        if person["is_logged_in"] == True:
            return redirect(url_for('welcome'))
        else:
            return redirect(url_for('registeruser'))

# if __name__ == "__main__":
#     app.secret_key = os.urandom(12)
#     app.run()