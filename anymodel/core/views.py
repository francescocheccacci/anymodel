from flask import render_template,request,Blueprint, current_app
from anymodel import mail
from flask_mail import Message

core = Blueprint('core',__name__)

@core.route('/')
def index():
    '''
    This is the home page view.
    '''
    return render_template('index.html')

@core.route('/info')
def info():
    '''
    Example view of any other "core" page. Such as a info page, about page,
    contact page. Any page that doesn't really sync with one of the models.
    '''
    return render_template('info.html')
