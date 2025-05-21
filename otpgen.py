import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def otp_gen(length=6):
    """Generate a numeric OTP of specified length"""
    digits = "0123456789"
    return "".join(random.choice(digits) for _ in range(length))

def send_email(subject, body, to_email):
    """Send email using SMTP"""
    # Email configuration
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
   
   
    sender_email = "Ammanagiabhishek1@gmail.com"  # Replace with your Gmail address
    sender_password = "hrho syxz lqtl pfnw"  # Generate an App Password from Google Account Settings

    # Create message
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = to_email
    message["Subject"] = subject

    # Add body to email
    message.attach(MIMEText(body, "plain"))

    try:
        # Create SMTP session
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)

        # Send email
        server.send_message(message)
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False