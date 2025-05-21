from flask import Flask, request, jsonify, send_from_directory, send_file, render_template, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
import requests
import time

app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # For flashing messages and session management

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # Redirect to login page if not authenticated

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Create database tables
with app.app_context():
    db.create_all()

# Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Ensure directories exist
VIDEO_DIR = os.path.join(app.root_path, "video")
JSON_DIR = os.path.join(app.root_path, "json")  
AUDIO_DIR = os.path.join(app.root_path, "audio")
REPORTS_DIR = os.path.join(app.root_path, "reports")
os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(JSON_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# Routes
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

        # Validation
        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for('signup'))

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(url_for('signup'))

        if User.query.filter_by(email=email).first():
            flash("Email already exists.", "danger")
            return redirect(url_for('signup'))

        # Store signup data in session
        session['signup_username'] = username
        session['signup_email'] = email
        session['signup_password'] = password

        # Generate and send OTP
        otp = otp_gen(6)
        session['signup_otp'] = otp
        send_email(
            subject="Signup OTP Verification",
            body=f"Your OTP for signup is: {otp}",
            to_email=email
        )
        
        return redirect(url_for('verify_signup_otp'))

    return render_template("signup.html")

from otpgen import otp_gen, send_email

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
        # Concatenate the 6 OTP digits from form
        user_otp = ''.join([request.form.get(f'otp{i}', '') for i in range(1, 7)])
        if user_otp and user_otp == session['signup_otp']:
            # Create new user
            user = User(username=session['signup_username'], email=session['signup_email'])
            user.set_password(session['signup_password'])
            db.session.add(user)
            db.session.commit()
            
            # Clear signup session data
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
        youtube_url = request.form.get("youtube_url")
        video_file = request.files.get("video_file")
        presentation_mode = request.form.get("presentation_mode") == "on"

        if not user_name:
            return jsonify({"error": "No Username received"}), 400

        if not youtube_url and not video_file:
            return jsonify({"error": "Neither Video File nor Video Link received"}), 400

        # User-specific directories
        user_video_dir = os.path.join(VIDEO_DIR, user_name)
        user_json_dir = os.path.join(JSON_DIR, user_name)
        user_audio_dir = os.path.join(AUDIO_DIR, user_name)
        user_reports_dir = os.path.join(REPORTS_DIR, user_name)
        os.makedirs(user_video_dir, exist_ok=True)
        os.makedirs(user_json_dir, exist_ok=True)
        os.makedirs(user_audio_dir, exist_ok=True)
        os.makedirs(user_reports_dir, exist_ok=True)

        video_file_path = os.path.join(user_video_dir, f"{user_name}_{int(time.time())}.mp4")

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

        output_json_path = os.path.join(user_json_dir, "output.json")
        with open(output_json_path, 'w', encoding='utf-8') as json_file:
            json.dump(analyzer_response.json(), json_file, ensure_ascii=False, indent=4)
    
        # Video Transcription
        with open(video_file_path, 'rb') as f:
            audio_path = os.path.join(user_audio_dir, "audiofile.wav")
            transcription_json_path = os.path.join(user_json_dir, "transcription_output.json")
            files = {'file': f}
            transcription_response = requests.post("http://localhost:8003/video_transcribe", files=files)
            if transcription_response.status_code != 200:
                raise Exception("Failed to transcribe the video")
        
        transcription_data = transcription_response.json()
        transcription_output = transcription_data["transcription_text"]
        with open(audio_path, 'wb') as audio_file:
            audio_file.write(transcription_data['audio_file'].encode('latin1'))

        with open(transcription_json_path, 'w', encoding='utf-8') as json_file:
            json.dump(json.loads(transcription_data['json_file']), json_file, indent=4)

        # Audio Module Request
        with open(transcription_json_path, "rb") as json_file, open(audio_path, "rb") as audio_file:
            files = {
                "transcription_file": ("transcription_output.json", json_file, "application/json"),
                "audio_file": ("audiofile.wav", audio_file, "audio/wav")
            }
            audio_metrics_response = requests.post("http://localhost:8002/audio_analysis", files=files)
            if audio_metrics_response.status_code != 200:
                raise Exception("Failed to Analyse the Audio Files")
        
        audio_metrics = audio_metrics_response.json()

        # Evaluate Transcription
        eval_results_response = requests.post("http://localhost:8003/evaluate_transcription", json={"output": transcription_output, "audio_metrics": audio_metrics})
        if eval_results_response.status_code != 200:
            raise Exception("Failed to Evaluate Transcription")
        eval_results = eval_results_response.json()

        # Evaluate Quality of Transcription
        quality_eval_response = requests.post("http://localhost:8003/quality_evaluator", json={"output": transcription_output})
        if quality_eval_response.status_code != 200:
            raise Exception("Failed to Evaluate Quality Of Transcription")
        quality_eval = quality_eval_response.json()

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
            report_response = requests.post("http://localhost:8004/create_report", files=files)
            if report_response.status_code != 200:
                raise Exception("Failed to Evaluate Quality Of Transcription")
        
        with open(pdf_path, "wb") as pdf_file:
            pdf_file.write(report_response.content)
        
        return jsonify({"message": "PDF generated successfully"}), 200
    
    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    uploads = os.path.join(app.root_path, "static", "uploads")
    return send_from_directory(uploads, filename)

@app.route("/download_pdf")
@login_required
def download_pdf():
    user_reports_dir = os.path.join(REPORTS_DIR, current_user.username)
    pdf_path = os.path.join(user_reports_dir, "combined_report.pdf")
    return send_file(pdf_path, as_attachment=True, download_name="evaluation_report.pdf")

if __name__ == "__main__":
    app.run(port='8000', host='0.0.0.0', debug=True)