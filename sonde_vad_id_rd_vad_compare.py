import requests
import os
from pydub import AudioSegment
import sys
sys.path.append('/home/ubuntu/VAD/user_verification/detection/')

from speech_suffic_onnx import SpeechSufficCheck
from flask import Flask, request, jsonify, make_response
from user_verification.examples.python.media_api_example import *
from user_verification.examples.python.verify_api_example import *
import logging
from pydub import AudioSegment

app = Flask(__name__)

app.logger.setLevel(logging.INFO)
app.logger.setLevel(logging.INFO)



import boto3
import botocore
from pydub import AudioSegment
import os
import csv


def save_to_csv(data_dict):
    csv_file_path = 'test_result.csv'
    field_names = ['sonde_meta_recording_duration', 'sonde_speech_length', 'sonde_speech_percent', 'ID_RD_total_len', 'ID_RD_background_len', 'ID_RD_speech_len', 'audio_file_path', 'old_vad', 'fbf_vad', 'hys_vad','ID_RD_SNR_value', 'qos_reject', 'background_noise', 'activity', 'activity_language']
    with open(csv_file_path, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=field_names)
        if file.tell() == 0:
            writer.writeheader()
        writer.writerow(data_dict)

def get_file_paths(dir_path):
    res = []
    for path in os.listdir(dir_path):
        if os.path.isfile(os.path.join(dir_path, path)):
            res.append(dir_path + '/' + path)
    return sorted(res)
    

def get_data_from_csv(file_name):
    try:
        import csv
        
        data_dict  = {}
        
        # Open the CSV file for reading
        with open(file_name, 'r') as csvfile:
            csv_reader = csv.DictReader(csvfile)
            for row in csv_reader:
                vad_type = row['vad_type']
                score = float(row['score'])
                # rounded_score = round(score, 2)
                data_dict[vad_type] = score
            return data_dict
    except Exception as ex:
        print(f"Something went wrong - {ex}")

        

def download_file(object_key, file_name, folder_name, bucket):
    os.system(f"mkdir {folder_name}")
    s3 = boto3.client('s3')
    bucket_name = bucket
    local_file_path = f'{folder_name}/{file_name}'
    print(f'download file - {object_key} with file name - {file_name}')
    try:
        s3.download_file(bucket_name, object_key, local_file_path)
        print(f"File downloaded: {local_file_path}")
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
        else:
            raise

def slice_audio(input_file, chunk_size_ms, out_path, output_format='wav'):
    # Load the audio file
    audio_file_path  = out_path +  '/' + input_file
    # print(f'audio_file_path - {audio_file_path}')
    audio = AudioSegment.from_file(audio_file_path)
    file_n = input_file.replace('.wav', '')
    # print('File_n - ', file_n)
    # Calculate the total duration of the audio file in milliseconds
    total_duration = len(audio)

    # Calculate the number of chunks
    num_chunks = total_duration // chunk_size_ms

    for i in range(num_chunks):
        # Calculate the starting and ending positions for the current chunk
        start_time = i * chunk_size_ms
        end_time = start_time + chunk_size_ms

        # Extract the chunk
        chunk = audio[start_time:end_time]

        # Save the chunk to a new file
        output_file = f"{out_path}/{file_n}_chunk_{i + 1}.{output_format}"
        chunk.export(output_file, format=output_format)
        # print(f"Chunk {i + 1} saved as '{output_file}'")

def pcm_conversion(audio_file_path):
    # print(f'audio file path - {audio_file_path}')
    input_audio = AudioSegment.from_file(audio_file_path)
    # print(f'input audio - {input_audio}')
    if input_audio.sample_width == 2 and input_audio.frame_rate == 16000 and input_audio.sample_width == 16:
        output_pcm_file = input_audio_file
        input_audio.export(output_pcm_file, format="wav")
        print("The input audio is in the correct PCM16 format.")
    else:
        print("The input audio is not in the correct PCM16 format.")

        # output_pcm_file = '/home/ubuntu/VAD/sonde/v8.1.0/out/file_pcm.wav'
        output_pcm_file = audio_file_path

        if input_audio.sample_width != 2:
            # print("Converting to PCM16...")
            input_audio = input_audio.set_sample_width(2)
        if input_audio.frame_rate != 16000:
            # print("Resampling to 16kHz...")
            input_audio = input_audio.set_frame_rate(16000)

        input_audio.export(output_pcm_file, format="wav")

        return output_pcm_file


def get_vad(audio_file_path, segment):
    app.logger.info(f'running sp library to check vad - {audio_file_path}')

    pcm_file=pcm_conversion(audio_file_path)

    os.system(
        f"/home/ubuntu/VAD/sonde/v8.1.0/sonde_sp_algorithm {pcm_file} /home/ubuntu/VAD/sonde/v8.1.0/manifest.yaml /home/ubuntu/VAD/sonde/v8.1.0/out/vad_only_vad.csv /home/ubuntu/VAD/sonde/v8.1.0/out/vad_speech_fe.csv /home/ubuntu/VAD/sonde/v8.1.0/resources/ 'None' "
        f"/home/ubuntu/VAD/sonde/v8.1.0/resources/thresholds.yaml")
    
    app.logger.info('-------------checking vad started------------')
    
    sp_obj = SpeechSufficCheck('/home/ubuntu/VAD/sonde/v8.1.0/out/vad_speech_fe.csv', segment)
    speech_length_sec, speech_percent, result, prob, array = sp_obj.compute_speech_suffic()
    app.logger.info('speech length {} and speech percent {} and result {} and prob {} array {}'.format(speech_length_sec, speech_percent, result, prob, array))
    app.logger.info('-------------checking vad completed------------')
    
    return {'sonde_speech_length': speech_length_sec * 1000, 'sonde_speech_percent': speech_percent, 'audio_file_path': audio_file_path}

    
def get_audio_file_duration(input_file):
    audio = AudioSegment.from_file(input_file)
    total_duration = len(audio)
    return total_duration    
        

import csv

# Specify the path to your CSV file
csv_file_path = '/home/ubuntu/VAD/quest_qos_fs_all_8_lang_ids_audio_path_final.csv'

# Open the CSV file
with open(csv_file_path, 'r') as file:
    csv_reader = csv.DictReader(file)
    for row in csv_reader:
        print(f"Process for audio file - {row['audio_file_path']}")
        file_keys = row['audio_file_path'].split('/')
        file_name = file_keys[-1]
        folder_name = file_name.replace('.wav', '')
        os.system(f"cd chunks/")
        os.system(f"mkdir chunks/{folder_name}")
        
        key = '/'.join(file_keys[3:])
        bucket = file_keys[2]
        download_file(key, file_keys[-1], f'chunks/{folder_name}', bucket)
        
        slice_audio(file_name, 3000, f'/home/ubuntu/VAD/chunks/{folder_name}', output_format='wav')
        all_files = get_file_paths(f'/home/ubuntu/VAD/chunks/{folder_name}')

        csv_data = {'activity_language': row['activity_language'], 'activity': row['activity'], 'sonde_meta_recording_duration': row['recording_duration'], 'qos_reject': row['reject'],'background_noise': row['background_noise']}
        for audio_file in all_files:
            vad = get_vad(audio_file, 35000) 
            ID_RD_dict = get_SNR_IDRD(audio_file)
            vad.update(ID_RD_dict)            
            chunk_file_name = audio_file.split('/')[-1].replace('.wav', '')
            records = get_data_from_csv(f'/home/ubuntu/VAD/sonde/v8.1.0/out/{chunk_file_name}_Qos_SNR.csv')       
            vad.update(records)
            vad.update(csv_data)            
            save_to_csv(vad)
            os.system('rm /home/ubuntu/VAD/sonde/v8.1.0/out/*')
        os.system(f'rm -rf /home/ubuntu/VAD/chunks/{folder_name}')
            



