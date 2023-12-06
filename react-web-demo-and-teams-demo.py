from flask import Flask, jsonify
from flask import request
from voiceSDK.examples.python.diarization_api_example import *
import requests
import json
import uuid
import time
import os
import csv
from flask_cors import CORS
from flask_cors import cross_origin
app_ = Flask(__name__)
cors = CORS(app_, resources={r"/*": {"origins": "*"}})
    

def create_template(file_path, user_id):
    url = "http://3.225.88.176:8080/"
    print(" ** ")
    base_url = "voice_template_factory/create_voice_template_from_samples?channel_type=&sample_rate=48000"
    with open(file_path, 'rb') as f:
        payload = f.read()
    headers = {
        'Content-Type': 'application/octet-stream'
    }
    response = requests.request("POST", url + base_url, headers=headers, data=payload)
    return response.text


def validate_templates(template1, template2):
    url = "http://3.225.88.176:8080/"
    base_url = "voice_template_matcher/match_voice_templates"
    
    payload = json.dumps({
      "template1": template1,
      "template2": template2
    })
    headers = {
      'Content-Type': 'application/json',
      'x-api-key': ''
    }
    
    response = requests.request("POST", url + base_url, headers=headers, data=payload)
    response = response.json()
    return response['probability'], response['score']

def converts(file_name):
    if file_name.endswith(".wav"):  # or .avi, .mpeg, whatever.
        print('Calling for {} and {}'.format(file_name, file_name.replace('.wav', '_new.wav')))
        os.system("ffmpeg -i {} {}".format(file_name, file_name.replace('.wav', '_new.wav')))
    else:
        pass


def upload_sample_file(STORAGE_SIGNED_URL, file_path):
    data = open(file_path, 'rb')
    # print(STORAGE_SIGNED_URL)
    url = STORAGE_SIGNED_URL
    headers = {'Content-Type': 'audio/wave'}
    r = requests.put(url, data=data, headers=headers)
    return r.status_code


def get_token_and_user():
    url_token = "https://api.sondeservices.com/platform/v1/oauth2/token"
    # base_token = 'Basic ' + 'MW9kNnZzNzgxNXZibnYwZTQ2aG1jYWhmYTg6bmpldjltNzdnczdzODBmNzdkZ21yNmEyaWUwYWtpOXUyanJvM2s4ajl1YnFwNmxnZWJk'
    base_token = 'Basic ' + 'MnNrM21oajhmbWhuMGpwMjExMGpka2FmYTpzbGI3aGpvdGVzZ2o0cWk2ZWhuZGJ1bjc2azRvZWN1OHBjYmNwMXY2Z3Fqb3Z0N3M5dg=='

    payload = 'grant_type=client_credentials'
    headers = {
        'Authorization': base_token,
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.request("POST", url_token, headers=headers, data=payload)
    # print(f'token api response - {response.json()}')
    access_token = response.json()['access_token']

    # url_user = "https://https://api.sondeservices.com/platform/v1/users"
    # 
    # payload = json.dumps({
    #     "gender": "Male",
    #     "yearOfBirth": "1995",
    #     "language": "ENGLISH"
    # })
    # headers = {
    #     'Authorization': access_token,
    #     'Content-Type': 'application/json'
    # }
    # response = requests.request("POST", url_user, headers=headers, data=payload)
    # user_identifier = response.json()['userIdentifier']
    # print('User ID - ', user_identifier)
    return access_token, 'f96a6b7f6'
# 
# 
# def check_if_present(user_id):
#     with open('mapping.csv', 'r') as f:
#         csv_reader = csv.reader(f)
#         for line in csv_reader:
#             if user_id in line:
#                 return True, line[1]
#         return False, ''
# 
# def check_and_create_user(access_token, user_id):
#     user, u_id = check_if_present(user_id)
#     if not user:
#         url_user = "https://api.sondeservices.com/platform/v1/users"
#         payload = json.dumps({
#             "gender": "Male",
#             "yearOfBirth": "1995",
#             "language": "ENGLISH"
#         })
#         headers = {
#             'Authorization': access_token,
#             'Content-Type': 'application/json'
#         }
#         response = requests.request("POST", url_user, headers=headers, data=payload)
#         user_identifier = response.json()['userIdentifier']
#         my_dict = {'user_id': user_id, 'user_identifier': user_identifier}
#         with open('mapping.csv', 'a+') as f:
#             w = csv.DictWriter(f, my_dict.keys())
#             w.writerow(my_dict)
#             f.close()
#         return {'userIdentifier': user_identifier}
#     return {'userIdentifier': u_id}
# 
# 
def get_vf_and_transcript(access_token, user_identifier, AUDIO_FILE_PATH):
    url_storage = "https://api.sondeservices.com/platform/v1/storage/files"

    payload = json.dumps({
        "fileType": "wav",
        "countryCode": "US",
        "userIdentifier": user_identifier
    })
    headers = {
        'Authorization': access_token,
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url_storage, headers=headers, data=payload)

    signed_url = response.json()['signedURL']
    file_path = response.json()['filePath']
    print(f'Local File Path - {AUDIO_FILE_PATH} & S3 File Path - {file_path}')
    upload_sample_file(signed_url, AUDIO_FILE_PATH)

    print('calling VF Scores')
    url_vf_score = "https://api.sondeservices.com/platform/async/v1/inference/voice-feature-scores"

    payload = json.dumps({
        "infer": [
            {
                "type": "Acoustic",
                "version": "v3"
            }
        ],
        "filePath": file_path,
        "measureName": "mental-fitness"
    })
    headers = {
        'Authorization': access_token,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.request("POST", url_vf_score, headers=headers, data=payload)
    except Exception as ex:
        print(f'Kuch to fat gya! - {ex}')
    vf_job = response.json()['jobId']
    request_id = response.json()['requestId']
    print(f'Response - {response.json()}')
    url_vf_score_get = "https://api.sondeservices.com/platform/async/v1/inference/voice-feature-scores/" + vf_job

    payload = {}
    headers = {
        'Authorization': access_token
    }
    # Default Score in case some got failed.
    score = {"filePath": "s3://prod-sondeplatform-us-subject-metadata/68e877c2-7d17-4533-8408-f6ba40e05bac/voice-samples/3d070784-a9f3-4af2-afaa-f9a0da3c9da2.wav", "measureName": "mental-fitness", "inferredAt": "2023-04-07T06:14:54Z", "userIdentifier": "f96a6b7f6", "id": "242551e2-b41f-4d77-b0af-6c90c8674753", "inference": [{"type": "Acoustic", "version": "v3", "voiceFeatures": [{"name": "Smoothness", "score": "88"}, {"name": "Liveliness", "score": "0.19"}, {"name": "Control", "score": "94"}, {"name": "Energy Range", "score": "28"}, {"name": "Clarity", "score": "0.22"}, {"name": "Crispness", "score": "202"}, {"name": "Pause Duration", "score": "0.77"}, {"name": "Speech Rate", "score": "0"}], "score": {"value": "58"}}], "type": "VoiceFeatureScores"}

    voice_features = ''
    response = requests.request("GET", url_vf_score_get, headers=headers, data=payload)
    status_vf = response.json()['status']
    while status_vf != 'DONE':
        time.sleep(3)
        response = requests.request("GET", url_vf_score_get, headers=headers, data=payload)
        status_vf = response.json()['status']
        if status_vf == 'FAIL':
            print(status_vf, f'Response - {response.json()}')
            error_response = dict()
            request_id = response.json()['requestId']
            error_response.update({'result': response.json()['result'], 'requestId': request_id})
            return error_response
    if status_vf == 'DONE':
        score = response.json()['result']
    print(f'Returning score - {score}')
    return score


@app_.route('/test', methods=['GET'])
@cross_origin()
def hello_world():
    return {'a': 'Hello World'}

# @app_.after_request
# def after_request(response):
#   response.headers['Access-Control-Allow-Methods']='*'
#   response.headers['Access-Control-Allow-Origin']='*'
#   response.headers['Vary']='Origin'
  
  
# @app_.route('/get-dummy', methods=['GET'])
# @cross_origin()
# def get_dummy_data():
#     return {"score": {"filePath": "s3://prod-sondeplatform-us-subject-metadata/68e877c2-7d17-4533-8408-f6ba40e05bac/voice-samples/3d070784-a9f3-4af2-afaa-f9a0da3c9da2.wav", "measureName": "mental-fitness", "inferredAt": "2023-04-07T06:14:54Z", "userIdentifier": "f96a6b7f6", "id": str(uuid.uuid4()), "inference": [{"type": "Acoustic", "version": "v3", "voiceFeatures": [{"name": "Smoothness", "score": "88"}, {"name": "Liveliness", "score": "0.19"}, {"name": "Control", "score": "94"}, {"name": "Energy Range", "score": "28"}, {"name": "Clarity", "score": "0.22"}, {"name": "Crispness", "score": "202"}, {"name": "Pause Duration", "score": "0.77"}, {"name": "Speech Rate", "score": "0"}], "score": {"value": "58"}}], "type": "VoiceFeatureScores"}}

# @app_.route('/get-speakers', methods=['GET'])
# @cross_origin()
# def get_speaker_count():  
#   return {"score": {"filePath": "s3://prod-sondeplatform-us-subject-metadata/68e877c2-7d17-4533-8408-f6ba40e05bac/voice-samples/3d070784-a9f3-4af2-afaa-f9a0da3c9da2.wav", "measureName": "mental-fitness", "inferredAt": "2023-04-07T06:14:54Z", "userIdentifier": "f96a6b7f6", "id": str(uuid.uuid4()), "inference": [{"type": "Acoustic", "version": "v3", "voiceFeatures": [{"name": "Smoothness", "score": "88"}, {"name": "Liveliness", "score": "0.19"}, {"name": "Control", "score": "94"}, {"name": "Energy Range", "score": "28"}, {"name": "Clarity", "score": "0.22"}, {"name": "Crispness", "score": "202"}, {"name": "Pause Duration", "score": "0.77"}, {"name": "Speech Rate", "score": "0"}], "score": {"value": "58"}}], "type": "VoiceFeatureScores"}}



# @app_.route('/user/<userId>', methods=['GET'])
# @cross_origin()
# def user(userId):
#     url_token = "https://api.sondeservices.com/platform/v1/oauth2/token"
#     # base_token = 'Basic ' + 'MW9kNnZzNzgxNXZibnYwZTQ2aG1jYWhmYTg6bmpldjltNzdnczdzODBmNzdkZ21yNmEyaWUwYWtpOXUyanJvM2s4ajl1YnFwNmxnZWJk'
#     base_token = 'Basic ' + 'MnNrM21oajhmbWhuMGpwMjExMGpka2FmYTpzbGI3aGpvdGVzZ2o0cWk2ZWhuZGJ1bjc2azRvZWN1OHBjYmNwMXY2Z3Fqb3Z0N3M5dg=='
# 
#     payload = 'grant_type=client_credentials'
#     headers = {
#         'Authorization': base_token,
#         'Content-Type': 'application/x-www-form-urlencoded'
#     }
# 
#     response = requests.request("POST", url_token, headers=headers, data=payload)
#     # print(f'token api response - {response.json()}')
#     access_token = response.json()['access_token']
#     
#     resp = check_and_create_user(access_token, userId)
#     return resp
#     
  
# @app_.route('/audio', methods=['POST'])
# @cross_origin()
# def audio():
#     return {'Hello': "World"}
#    

@app_.route('/user/<userId>/voice-features', methods=['POST'])
@cross_origin()   
def get_vf_score(userId):
    local_file_name = str(uuid.uuid4())[:8] + '.wav'
    # response.headers.add('Access-Control-Allow-Origin', '*')
    score = dict()
    if request.method == 'POST':
        # os.system("rm -r *.wav")
        f = request.files['webmasterfile']
        f1 = open(local_file_name, 'wb+')
        f.save(f1)
        converts(local_file_name)
        access_token, u_id = get_token_and_user()
        score = get_vf_and_transcript(access_token, userId, local_file_name.replace('.wav', '_new.wav'))
        # score = get_vf_and_transcript(access_token, u_id, local_file_name.replace('.wav', '.wav'))
        # os.system("rm -r *.wav")
        # return {'done': b}
    return {'score': score}




@app_.route('/user/<userId>/docker-enroll', methods=['POST'])
@cross_origin()   
def docker_enroll(userId):
    local_file_name = str(uuid.uuid4())[:8] + '.wav'
    # response.headers.add('Access-Control-Allow-Origin', '*')
    score = dict()
    if request.method == 'POST':
        # os.system("rm -r *.wav")
        f = request.files['webmasterfile']
        f1 = open(local_file_name, 'wb+')
        f.save(f1)
        converts(local_file_name)
        url = f"http://100.26.214.98:8080/api/user-management/user/enrollment?identifier={userId}"
        audio_file_path = local_file_name.replace('.wav', '_new.wav')
        # Read the audio file as binary data
        with open(audio_file_path, 'rb') as audio_file:
            payload = audio_file.read()
        headers = {
            'Content-Type': 'audio/wave'
        }
        
        response = requests.request("POST", url, headers=headers, data=payload)

    return response.json()
    
    
@app_.route('/docker-voice-features', methods=['POST'])
@cross_origin()   
def docker_verify():
    local_file_name = str(uuid.uuid4())[:8] + '.wav'
    score = dict()
    if request.method == 'POST':
        identifier = request.args.get('identifier')
        os.system("rm -r *.wav")
        f = request.files['webmasterfile']
        f1 = open(local_file_name, 'wb+')
        f.save(f1)
        converts(local_file_name)
        if identifier:
            url = f"http://100.26.214.98:8080/api/voice-feature-scores?identifier={identifier}"
        else:
            url = "http://100.26.214.98:8080/api/voice-feature-scores"
        audio_file_path = local_file_name.replace('.wav', '_new.wav')
        with open(audio_file_path, 'rb') as audio_file:
            payload = audio_file.read()
        headers = {
            'Content-Type': 'audio/wave'
        }
        os.system("rm -r *.wav")
        response = requests.request("POST", url, headers=headers, data=payload)

    return response.json()    



@app_.route('/user/<userId>/enrollment', methods=['POST'])
@cross_origin()
def enrollment(userId):
    local_file_name = str(uuid.uuid4())[:8] + '.wav'
    # response.headers.add('Access-Control-Allow-Origin', '*')
    score = dict()
    if request.method == 'POST':
        #os.system("rm -r *.wav")
        f = request.files['webmasterfile']
        f1 = open(local_file_name, 'wb+')
        f.save(f1)
        converts(local_file_name)
        access_token, u_id = get_token_and_user()
        
        # return {'done': b}
    template = create_template(local_file_name.replace('.wav', '_new.wav'), userId)
    with open('user_enrollment_files/' + userId + '.txt', 'w+') as f_txt:
        f_txt.write(template)
    #os.system("rm -r *.wav")
    return {'template': template} 
  
    
@app_.route('/user/<userId>/enrollment', methods=['GET'])
@cross_origin()
def get_user_enrollment(userId):  
    flag = os.path.isfile('user_enrollment_files/' + userId + '.txt')
    if flag:
        return {"enrolled": True}  
    return {"enrolled": False}


@app_.route('/api/user-management/users', methods=['GET'])
@cross_origin()
def get_all_users():  
    url = "http://100.26.214.98:8080/api/user-management/user"
    
    payload = {}
    headers = {}
    
    response = requests.request("GET", url, headers=headers, data=payload)
    
    return response.json()
    

@app_.route('/api/user-management/user/<userId>', methods=['GET'])
@cross_origin()
def delete_user(userId):  
    url = f"http://100.26.214.98:8080/api/user-management/user/{userId}"

    payload = {}
    headers = {}
    
    response = requests.request("DELETE", url, headers=headers, data=payload)
    
    return response.json()    
    

@app_.route('/api/user-management/users-history', methods=['GET'])
@cross_origin()
def get_user_history():  
    url = "http://100.26.214.98:8080/api/user-management/user/scoring-history"
    
    payload = {}
    headers = {}
    
    response = requests.request("GET", url, headers=headers, data=payload)
    
    return response.json() 


@app_.route('/api/user-management/score/<scoreId>', methods=['GET'])
@cross_origin()
def get_score_history(scoreId):  
    url = f"http://100.26.214.98:8080/api/user-management/user/score/{scoreId}"
    
    payload = {}
    headers = {}
    
    response = requests.request("GET", url, headers=headers, data=payload)
    
    return response.json()  


@app_.route('/api/user-management/user/<userId>/scoring-history', methods=['GET'])
@cross_origin()
def get_user_history_by_id(userId):  
    url = f"http://100.26.214.98:8080/api/user-management/user/{userId}/scoring-history"
    
    payload = {}
    headers = {}
    
    response = requests.request("GET", url, headers=headers, data=payload)
    
    return response.json()     
    
    
@app_.route('/api/user-management/user/<userId>/chunks', methods=['GET'])
@cross_origin()
def get_user_chunks(userId):  
    url = f"http://100.26.214.98:8080/api/user-management/user/{userId}/chunk"
    
    payload = {}
    headers = {}
    
    response = requests.request("GET", url, headers=headers, data=payload)
    
    return response.json()     
    
    

@app_.route('/user/<userId>/reset-enrollment', methods=['GET'])
@cross_origin()
def reset_user_enrollment(userId):  
    flag = os.path.isfile('user_enrollment_files/' + userId + '.txt')
    if flag:
        os.system(f"rm -r user_enrollment_files/{userId}.txt")
        return {"enrolled": False}  
    return {"enrolled": False}

    
@app_.route('/user/<userId>/verification', methods=['POST'])
@cross_origin()
def verification(userId):
    template_1 = ''
    with open('user_enrollment_files/' + userId + '.txt', 'r') as f:
            template_1 = f.read() 
    local_file_name = str(uuid.uuid4())[:8] + '.wav'
    # response.headers.add('Access-Control-Allow-Origin', '*')
    score = dict()
    if request.method == 'POST':
        # os.system("rm -r *.wav")
        f = request.files['webmasterfile']
        f1 = open(local_file_name, 'wb+')
        f.save(f1)
        converts(local_file_name)
        access_token, u_id = get_token_and_user()
        # return {'done': b}
    template_2 = create_template(local_file_name.replace('.wav', '_new.wav'), userId)
    # template_2 = create_template('5b4b9f5f_new.wav', userId)
    prod, score = validate_templates(template_1, template_2)
    # os.system("rm -r *.wav")
    # print("prob is - ", prod, "score is - ", score)
    msg = f"prob is {prod} & score is {score}"
    with open('prob_mapping/' + userId + '.txt', 'a+') as f_txt:
        f_txt.write(msg)
    return {"prod": prod, "score": score}


@app_.route('/user/<userId>/verification-test', methods=['POST'])
@cross_origin()
def verification_test(userId):
    template_1 = ''
    with open('user_enrollment_files/' + userId + '.txt', 'r') as f:
            template_1 = f.read() 
    local_file_name = str(uuid.uuid4())[:8] + '.wav'
    # response.headers.add('Access-Control-Allow-Origin', '*')
    score = dict()
    if request.method == 'POST':
        os.system("rm -r *.wav")
        f = request.files['webmasterfile']
        f1 = open(local_file_name, 'wb+')
        f.save(f1)
        converts(local_file_name)
        access_token, u_id = get_token_and_user()
        # return {'done': b}
    try:
        speakers = get_speaker(f"/home/sachinsingh/ffmpeg/{local_file_name.replace('.wav', '_new.wav')}")
    except Exception as ex:
        print(f"Some Issue happend - {ex}")
        speakers = 0
    if speakers == 1:
        template_2 = create_template(local_file_name.replace('.wav', '_new.wav'), userId)
        # template_2 = create_template('5b4b9f5f_new.wav', userId)
        prod, score = validate_templates(template_1, template_2)
        os.system("rm -r *.wav")
        # print("prob is - ", prod, "score is - ", score)
        msg = f"prob is {prod} & score is {score}"
        with open('prob_mapping/' + userId + '.txt', 'a+') as f_txt:
            f_txt.write(msg)
        return {"prod": prod, "score": score, "speakers": 1}
    return {"prod": 0, "score": 0, "speakers": speakers}
    
    

if __name__ == '__main__':
    # app_.run(host='0.0.0.0')
    app_.run('0.0.0.0')
