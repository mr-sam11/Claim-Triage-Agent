from email.message import EmailMessage
import smtplib
import ssl

def send_sns_email(subject: str, body: str, receiver_email: str):
    """
    Simulates AWS SNS email notification using Gmail SMTP.
    Sends email alerts for high-priority claims.
    """

    sender_email = "samtestdata05@gmail.com"
    app_password = "jsuj ovhf usuu tghy"  # 🔒 Gmail App Password (not regular password)

    # Create the email message
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg.set_content(body)

    # Secure SSL context
    context = ssl.create_default_context()

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
            smtp.login(sender_email, app_password)
            smtp.send_message(msg)
        print("✅ SNS email notification sent successfully!")
        return True
    except Exception as e:
        print(f"❌ Error sending SNS email: {e}")
        return False
