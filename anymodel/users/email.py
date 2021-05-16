from flask import render_template, current_app
from flask_mail import Message
from anymodel import mail

def send_password_reset_email(user):
    token = user.get_reset_password_token()
    send_email('[AnyModel] Reset Your Password',
               sender='anymodel.noreply@gmail.com',
               recipients=[user.email],
               html_body=render_template('email/reset_password.html',
                                         user=user, token=token))

def send_email(subject, sender, recipients, html_body):
    with current_app.app_context():
        msg = Message(subject, sender=sender ,recipients=recipients)
        msg.html = html_body
        mail.send(msg)
