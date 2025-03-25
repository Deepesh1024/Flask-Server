from flask import Flask, request, jsonify
import os
import json
import requests
import time

app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # Needed for flashing messages

# # Ensure directories exist
VIDEO_DIR = os.path.join(app.root_path, "video")
JSON_DIR = os.path.join(app.root_path, "json")  
AUDIO_DIR = os.path.join(app.root_path, "audio")
REPORTS_DIR = os.path.join(app.root_path, "reports")
os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(JSON_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

video_file_path = os.path.join(VIDEO_DIR, "Anubhuto_1741435925.mp4")

@app.route("/", methods=["POST"])
def index():
    try:
        user_name = request.form.get("user_name")
        youtube_url = request.form.get("youtube_url")
        video_file = request.files.get("video_file")

        if not user_name:
            return jsonify({"error": "No Username received"}), 400

        if not youtube_url and not video_file:
            return jsonify({"error": "Neither Video File nor Video Link received"}), 400

        video_file_path = os.path.join(VIDEO_DIR, f"{user_name}_{int(time.time())}.mp4")

        if youtube_url:
            response = requests.post("http://localhost:8001/download_video", json={"url": youtube_url})
            if response.status_code != 200:
                raise Exception(f"Failed to download YouTube video: {response.text}")
            
            with open(video_file_path, "wb") as f:
                f.write(response.content)
        else:
            video_file.save(video_file_path)

        with open(video_file_path, 'rb') as f:
            files = {'file': f}
            analyzer_response = requests.post("http://localhost:8001/video_analyzer", files=files)

        if analyzer_response.status_code != 200:
            raise Exception("Failed to analyze the video")

        output_json_path = os.path.join(JSON_DIR, "output.json")
        with open(output_json_path, 'w', encoding='utf-8') as json_file:
            json.dump(analyzer_response.json(), json_file, ensure_ascii=False, indent=4)
    
        """ VIDEO LOGIC FINALISED """


        """ VIDEO TRANSCRIPTION"""

        with open(video_file_path, 'rb') as f:
            audio_path = os.path.join(AUDIO_DIR, "audiofile.wav")
            transcription_json_path = os.path.join(JSON_DIR, "transcription_output.json")
            files = {'file' : f}
            transcription_response = requests.post("http://localhost:8003/video_transcribe", files=files)
            if transcription_response.status_code != 200:
                raise Exception("Failed to transcribe the video")
        
        transcription_data = transcription_response.json()
        transcription_output = transcription_data["transcription_text"]
        with open(audio_path, 'wb') as audio_file:
            audio_file.write(transcription_data['audio_file'].encode('latin1'))

        with open(transcription_json_path, 'w', encoding='utf-8') as json_file:
            json.dump(json.loads(transcription_data['json_file']), json_file, indent=4)
        

        """ SETTING UP AUDIO MODULE REQUEST """

        with open(transcription_json_path, "rb") as json_file, open(audio_path, "rb") as audio_file:
            files = {
                "transcription_file": ("transcription_output.json", json_file, "application/json"),
                "audio_file": ("audiofile.wav", audio_file, "audio/wav")
            }

            audio_metrics_response = requests.post("http://localhost:8002/audio_analysis", files = files)
            if audio_metrics_response.status_code != 200:
                raise Exception("Failed to Analyse the Audio Files")
        
        audio_metrics = audio_metrics_response.json()

        """ SETTING UP EVALUATE TRANSCRIPTION """

        eval_results_response = requests.post("http://localhost:8003/evaluate_transcription", json = {"output":transcription_output, "audio_metrics": audio_metrics})
        if eval_results_response.status_code != 200:
            raise Exception("Failed to Evaluate Transcription")
        eval_results = eval_results_response.json()

        """ SETTING UP EVALUATING QUALITY OF TRANSCRIPTION """

        quality_eval_response = requests.post("http://localhost:8003/quality_evaluator", json = {"output":transcription_output})
        if quality_eval_response.status_code != 200:
            raise Exception("Failed to Evaluate Quality Of Transcription")
        quality_eval = quality_eval_response.json()

        """ UPDATING OUTPUT JSON FILES """

        quality_eval_json_path = os.path.join(JSON_DIR, "quality_analysis.json")
        with open(quality_eval_json_path, 'w', encoding='utf-8') as json_file:
            json.dump(quality_eval, json_file, ensure_ascii=False, indent=4)
            print(f"Quality analysis saved to {quality_eval_json_path}")

            with open(output_json_path, 'r') as f:
                data = json.load(f)
            data.update({
                'User Name': user_name or "Trial",
                'LLM': eval_results
            })
            with open(output_json_path, 'w') as f:
                json.dump(data, f, indent=4)
        
        """ REPORT MODULE STARTS """

        pdf_path = os.path.join(REPORTS_DIR, "combined_report.pdf")
        quality_analysis_path = os.path.join(JSON_DIR, "quality_analysis.json")
        with open(output_json_path, 'rb') as f, open(quality_analysis_path, 'rb') as quality:
            files = {'output': f, 'quality': quality}
            report_response = requests.post("http://localhost:8004/create_report", files = files)
            if report_response.status_code != 200:
                raise Exception("Failed to Evaluate Quality Of Transcription")
        
        with open(pdf_path, "wb") as pdf_file:
            pdf_file.write(report_response.content)
        

        return jsonify({"message":"PDF generated"})
    
    except Exception as e:
        return jsonify({"message":f"An error occurred: {str(e)}"})

# Endpoint to serve uploaded video files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    uploads = os.path.join(app.root_path, "static", "uploads")
    return send_from_directory(uploads, filename)

@app.route("/download_pdf")
def download_pdf():
     pdf_path = os.path.join(app.root_path, "reports", "combined_report.pdf")
     return send_file(pdf_path, as_attachment=True, download_name="evaluation_report.pdf")
if __name__ == "__main__":
    app.run(port = '8000',host = '0.0.0.0', debug=False)