import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import config
import cv2

def send_notification_email(subject, body_text, recipients, image_frame=None):
    if not recipients:
        print("No recipients provided for email notification.")
        if config.EMAIL_RECEIVER:
            print(f"Falling back to admin email: {config.EMAIL_RECEIVER}")
            recipients = [config.EMAIL_RECEIVER]
        else:
            print("No admin/fallback email configured. Email not sent.")
            return

    msg = MIMEMultipart()
    msg['From'] = config.EMAIL_SENDER
    msg['To'] = ", ".join(recipients)
    msg['Subject'] = subject

    msg.attach(MIMEText(body_text, 'plain'))

    if image_frame is not None:
        try:
            cv2.imwrite(config.TEMP_IMAGE_PATH, image_frame)
            with open(config.TEMP_IMAGE_PATH, 'rb') as fp:
                img = MIMEImage(fp.read())
            img.add_header('Content-Disposition', 'attachment', filename="visitor_image.jpg")
            msg.attach(img)
            print("Image attached to email.")
        except Exception as e:
            print(f"Error attaching image to email: {e}")

    try:
        server = smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT)
        server.starttls()
        server.login(config.EMAIL_SENDER, config.EMAIL_PASSWORD)
        server.sendmail(config.EMAIL_SENDER, recipients, msg.as_string())
        server.quit()
        print(f"Email sent successfully to: {', '.join(recipients)}")
    except Exception as e:
        print(f"Error sending email: {e}")
