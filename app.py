from flask import Flask, request, jsonify, send_from_directory, send_file, render_template, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
import requests
import base64
from moviepy.editor import VideoFileClip
import time

app = Flask(__name__)
app.secret_key = "your_secret_key_here"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

VIDEO_DIR = os.path.join(app.root_path, "video")
JSON_DIR = os.path.join(app.root_path, "json")
AUDIO_DIR = os.path.join(app.root_path, "audio")
REPORTS_DIR = os.path.join(app.root_path, "reports")
os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(JSON_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for('signup'))

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(url_for('signup'))

        if User.query.filter_by(email=email).first():
            flash("Email already exists.", "danger")
            return redirect(url_for('signup'))

        session['signup_username'] = username
        session['signup_email'] = email
        session['signup_password'] = password

        from otpgen import otp_gen, send_email
        otp = otp_gen(6)
        session['signup_otp'] = otp
        send_email(subject="Signup OTP Verification", body=f"Your OTP for signup is: {otp}", to_email=email)
        return redirect(url_for('verify_signup_otp'))

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Logged in successfully!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid username or password.", "danger")
            return redirect(url_for('login'))

    return render_template("login.html")

@app.route("/verify-signup-otp", methods=["GET", "POST"])
def verify_signup_otp():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if 'signup_otp' not in session or 'signup_username' not in session:
        flash("Please signup first", "danger")
        return redirect(url_for('signup'))
        
    if request.method == "POST":
        user_otp = ''.join([request.form.get(f'otp{i}', '') for i in range(1, 7)])
        if user_otp and user_otp == session['signup_otp']:
            user = User(username=session['signup_username'], email=session['signup_email'])
            user.set_password(session['signup_password'])
            db.session.add(user)
            db.session.commit()
            
            session.pop('signup_otp', None)
            session.pop('signup_username', None)
            session.pop('signup_email', None)
            session.pop('signup_password', None)
            
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))
        flash("Invalid OTP. Please try again.", "danger")
        
    return render_template("verify_otp.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "success")
    return redirect(url_for('login'))

@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    if request.method == "GET":
        return render_template("index.html", username=current_user.username)

    try:
        user_name = current_user.username
        drive_url = request.form.get("drive_url")
        video_file = request.files.get("video_file")
        presentation_mode = request.form.get("presentation_mode") == "on"
        
        if request.form.get("presentation_mode") == "on":
            presentation_mode = "on" 
        else:
            presentation_mode = "off"

        if not user_name:
            return jsonify({"error": {"code": "NO_USERNAME", "message": "No Username received"}}), 400

        if not drive_url and not video_file:
            return jsonify({"error": {"code": "NO_INPUT", "message": "Neither Video File nor Video Link received"}}), 400

        # User-specific directories
        user_video_dir = os.path.join(VIDEO_DIR, user_name)
        user_json_dir = os.path.join(JSON_DIR, user_name)
        user_audio_dir = os.path.join(AUDIO_DIR, user_name)
        user_reports_dir = os.path.join(REPORTS_DIR, user_name)
        os.makedirs(user_video_dir, exist_ok=True)
        os.makedirs(user_json_dir, exist_ok=True)
        os.makedirs(user_audio_dir, exist_ok=True)
        os.makedirs(user_reports_dir, exist_ok=True)

        # Save video file if uploaded
        video_path = None
        if video_file:
            video_filename = f"input_video_{int(time.time())}.mp4"
            video_path = os.path.join(user_video_dir, video_filename)
            video_file.save(video_path)
        elif drive_url:
            # Download video from drive_url (handled by download_video service)
            form_data = {"user_name": user_name, "drive_url": drive_url , "presentation_mode": presentation_mode}
            try:
                response = requests.post(
                    "http://localhost:8001/download_video",
                    data=form_data,
                    timeout=300
                )
                print(f"Response from download_video: {response.status_code}, {response.text}")
                if response.status_code != 200:
                    return jsonify({"error": {"code": "DOWNLOAD_FAILED", "message": f"Failed to download video: {response.text}"}}), response.status_code
                analysis_data = response.json().get("data", {})
                # Assume video is saved by the service; update video_path if needed
                video_path = os.path.join(user_video_dir, "downloaded_video.mp4")
                with open(video_path, "wb") as f:
                    f.write(response.content)  # Adjust based on actual response
            except requests.exceptions.RequestException as e:
                print(f"Error contacting download_video: {str(e)}")
                return jsonify({"error": {"code": "SERVER_UNAVAILABLE", "message": f"Failed to contact video downloader: {str(e)}"}}), 500
        else:
            return jsonify({"error": {"code": "NO_VIDEO", "message": "No video file or URL provided"}}), 400

        # Save analysis output
        output_json_path = os.path.join(user_json_dir, "output.json")
        with open(output_json_path, 'w', encoding='utf-8') as json_file:
            json.dump(analysis_data if 'analysis_data' in locals() else {}, json_file, ensure_ascii=False, indent=4)

        # Extract audio locally using moviepy
        audio_path = os.path.join(user_audio_dir, "audiofile.wav")
        try:
            video = VideoFileClip(video_path)
            video.audio.write_audiofile(audio_path)
            video.close()
        except Exception as e:
            print(f"Error extracting audio: {str(e)}")
            return jsonify({"error": {"code": "AUDIO_EXTRACT_FAILED", "message": f"Failed to extract audio: {str(e)}"}}), 500

        # Video Transcription
        transcription_json_path = os.path.join(user_json_dir, "transcription_output.json")
        with open(audio_path, 'rb') as audio_file:
            files = {'file': ('audiofile.wav', audio_file, 'audio/wav')}
            try:
                transcription_response = requests.post(
                    "http://localhost:8003/video_transcribe",
                    files=files,
                    timeout=300
                )
                print(f"Transcription response: {transcription_response.status_code}, {transcription_response.text}")
                if transcription_response.status_code != 200:
                    return jsonify({"error": {"code": "TRANSCRIPTION_FAILED", "message": f"Failed to transcribe audio: {transcription_response.text}"}}), transcription_response.status_code
                transcription_data = transcription_response.json()
                if "transcription_text" not in transcription_data or "json_file" not in transcription_data:
                    return jsonify({"error": {"code": "INVALID_RESPONSE", "message": "Transcription response missing required fields"}}), 500
            except requests.exceptions.RequestException as e:
                print(f"Error contacting video_transcribe: {str(e)}")
                return jsonify({"error": {"code": "SERVER_UNAVAILABLE", "message": f"Failed to contact transcriber: {str(e)}"}}), 500

        transcription_output = transcription_data["transcription_text"]
        with open(transcription_json_path, 'w', encoding='utf-8') as json_file:
            json.dump(json.loads(transcription_data['json_file']), json_file, indent=4)

        # Audio Module Request
        with open(transcription_json_path, "rb") as json_file, open(audio_path, "rb") as audio_file:
            files = {
                "transcription_file": ("transcription_output.json", json_file, "application/json"),
                "audio_file": ("audiofile.wav", audio_file, "audio/wav")
            }
            try:
                audio_metrics_response = requests.post(
                    "http://localhost:8002/audio_analysis",
                    files=files,
                    timeout=300
                )
                print(f"Audio metrics response: {audio_metrics_response.status_code}, {audio_metrics_response.text}")
                if audio_metrics_response.status_code != 200:
                    return jsonify({"error": {"code": "AUDIO_ANALYSIS_FAILED", "message": f"Failed to analyze audio: {audio_metrics_response.text}"}}), audio_metrics_response.status_code
                audio_metrics = audio_metrics_response.json()
            except requests.exceptions.RequestException as e:
                print(f"Error contacting audio_analysis: {str(e)}")
                return jsonify({"error": {"code": "SERVER_UNAVAILABLE", "message": f"Failed to contact audio analyzer: {str(e)}"}}), 500

        # Evaluate Transcription
        try:
            eval_results_response = requests.post(
                "http://localhost:8003/evaluate_transcription",
                json={"output": transcription_output, "audio_metrics": audio_metrics},
                timeout=300
            )
            print(f"Eval results response: {eval_results_response.status_code}, {eval_results_response.text}")
            if eval_results_response.status_code != 200:
                return jsonify({"error": {"code": "EVAL_FAILED", "message": f"Failed to evaluate transcription: {eval_results_response.text}"}}), eval_results_response.status_code
            eval_results = eval_results_response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error contacting evaluate_transcription: {str(e)}")
            return jsonify({"error": {"code": "SERVER_UNAVAILABLE", "message": f"Failed to contact evaluator: {str(e)}"}}), 500

        # Evaluate Quality of Transcription
        try:
            quality_eval_response = requests.post(
                "http://localhost:8003/quality_evaluator",
                json={"output": transcription_output},
                timeout=300
            )
            print(f"Quality eval response: {quality_eval_response.status_code}, {quality_eval_response.text}")
            if quality_eval_response.status_code != 200:
                return jsonify({"error": {"code": "QUALITY_EVAL_FAILED", "message": f"Failed to evaluate quality: {quality_eval_response.text}"}}), quality_eval_response.status_code
            quality_eval = quality_eval_response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error contacting quality_evaluator: {str(e)}")
            return jsonify({"error": {"code": "SERVER_UNAVAILABLE", "message": f"Failed to contact quality evaluator: {str(e)}"}}), 500

        # Update Output JSON Files
        quality_eval_json_path = os.path.join(user_json_dir, "quality_analysis.json")
        with open(quality_eval_json_path, 'w', encoding='utf-8') as json_file:
            json.dump(quality_eval, json_file, ensure_ascii=False, indent=4)
            print(f"Quality analysis saved to {quality_eval_json_path}")

        with open(output_json_path, 'r') as f:
            data = json.load(f)
        data.update({
            'User Name': user_name,
            'LLM': eval_results,
            'Presentation Mode': presentation_mode
        })
        with open(output_json_path, 'w') as f:
            json.dump(data, f, indent=4)

        # Report Module
        pdf_path = os.path.join(user_reports_dir, "combined_report.pdf")
        quality_analysis_path = os.path.join(user_json_dir, "quality_analysis.json")
        with open(output_json_path, 'rb') as f, open(quality_analysis_path, 'rb') as quality:
            files = {'output': f, 'quality': quality}
            try:
                report_response = requests.post(
                    "http://localhost:8004/create_report",
                    files=files,
                    timeout=300
                )
                print(f"Report response: {report_response.status_code}, {report_response.text}")
                if report_response.status_code != 200:
                    return jsonify({"error": {"code": "REPORT_FAILED", "message": f"Failed to create report: {report_response.text}"}}), report_response.status_code
            except requests.exceptions.RequestException as e:
                print(f"Error contacting create_report: {str(e)}")
                return jsonify({"error": {"code": "SERVER_UNAVAILABLE", "message": f"Failed to contact report creator: {str(e)}"}}), 500
        
        with open(pdf_path, "wb") as pdf_file:
            pdf_file.write(report_response.content)
        
        return jsonify({"message": "PDF generated successfully"}), 200
    
    except Exception as e:
        print(f"Error in dashboard: {str(e)}")
        return jsonify({"error": {"code": "SERVER_ERROR", "message": f"An error occurred: {str(e)}"}}), 500

@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    uploads = os.path.join(app.root_path, "static", "Uploads")
    return send_from_directory(uploads, filename)

@app.route("/download_pdf")
@login_required
def download_pdf():
    user_reports_dir = os.path.join(REPORTS_DIR, current_user.username)
    pdf_path = os.path.join(user_reports_dir, "combined_report.pdf")
    return send_file(pdf_path, as_attachment=True, download_name="evaluation_report.pdf")

if __name__ == "__main__":
    app.run(port=8000, host="0.0.0.0", debug=True)