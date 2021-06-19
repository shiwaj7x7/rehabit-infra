import  json, os
import  pyrebase
import  firebase_admin
from    starlette.responses import RedirectResponse
from    firebase_admin      import credentials, auth, firestore, storage
from    fastapi             import FastAPI, Form, Header, File, UploadFile
from    os.path             import join, dirname
from    dotenv              import load_dotenv

# load firebase credentials from environment variables
# create json files if required
load_dotenv(join(dirname(__file__), '.env'))
with open(join(dirname(__file__), 'firebase.json'),'w') as f:
    json.dump(eval(os.environ['FB_CREDS']), f, indent = 4)
with open(join(dirname(__file__), 'fbadmin.json'),'w') as f:
    json.dump(eval(os.environ['FB_ADMIN_CREDS']), f, indent = 4)

# Initialize FastAPI
app = FastAPI()

# Firebase connections
cred = credentials.Certificate('fbadmin.json')
firebase = firebase_admin.initialize_app(cred)
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './fbadmin.json'
db = firestore.Client()
bucket = storage.bucket('rehabit-7072a.appspot.com')
pb = pyrebase.initialize_app(json.load(open('firebase.json')))

# helper methods to hande firebase storage
def upload_to_firestore(file, uid):
    file_ref = bucket.blob(uid)
    file_ref.upload_from_file(file.file, content_type=file.content_type)
    file_ref.make_public()
    return file_ref.public_url

def delete_profile_pic(uid):
    file = bucket.blob(uid)
    if file.exists():
        file.delete()
    return None

# Api route for documentation
@app.get('/')
def view_documentation():
    return RedirectResponse(url='/docs')

# Api route to sign up a new user
@app.post('/api/signup')
def signup(email: str = Form(None), password: str = Form(None), name: str = Form(None), phone_no: str = Form(None)):
    if not email or not password:
        return {'message': 'Error: Missing email or password'}
    data={
        'name':name,
        'email':email,
        'phone_no':phone_no
    }
    # create firebase user
    try:
        user = auth.create_user(
                email=email,
                password=password
        )
        # add user data in firestore
        db.collection('users').document(user.uid).set(data)
        return {'message': f'Successfully created user {user.uid}'}
    except:
        return {'message': 'Error creating user'}
    
# Api route to get a new token for a valid user
@app.post('/api/signin')
def signin(email: str = Form(None), password: str = Form(None)):
    if email is None or password is None:
        return {'message': 'Error: Missing email or password'}
    try:
        user = pb.auth().sign_in_with_email_and_password(email, password)
        jwt = user['idToken']
        return {'token': jwt}
    except:
        return {'message': 'There was an error logging in'}

# Api route to add or update user data
@app.post('/api/user/update')
def update_user_data(authorization: str = Header(None), name: str = Form(None),phone_no: str = Form(None), testdata: str = Form(None), profile: UploadFile = File(None)):
    if authorization is None:
        return {'message': 'No token provided'}
    try:
        try:
            user = auth.verify_id_token(authorization)
        except:
            return {'message': 'Invalid or expired Token'}
        uid = user['uid']
        # if profile file present, upload it to firestore
        if profile:
            url = upload_to_firestore(profile,uid)
        else:
            url = delete_profile_pic(uid)
        # fetch data from db
        doc = db.collection('users').document(uid)
        userdata = doc.get().to_dict()
        # modify data
        userdata.update({
            'name':name,
            'phone_no':phone_no,
            'data':testdata,
            'profile':url
        })
        # update to db
        db.collection('users').document(uid).set(userdata)
        return userdata
    except:
        return {'message': 'There was an error Updating user data'}

# Api route to get user metadata
@app.get('/api/user/metadata')
def get_user_metadata(authorization: str = Header(None)):
    if authorization is None:
        return {'message': 'No token provided'}
    try:
        user = auth.verify_id_token(authorization)
        return user
    except:
        return {'message': 'Invalid or expired Token'}

# Api route to get user data
@app.get('/api/user/data')
def get_userdata(authorization: str = Header(None)):
    if authorization is None:
        return {'message': 'No token provided'}
    try:
        try:
            user = auth.verify_id_token(authorization)
        except:
            return {'message': 'Invalid or expired Token'}
        uid = user['uid']
        doc = db.collection('users').document(uid)
        userdata = doc.get().to_dict()
        return userdata
    except:
        return {'message': 'There was an error logging in'}

