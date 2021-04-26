from flask.helpers import url_for
from flask_login.utils import login_required, logout_user
from app import app, socketio
from flask_login import current_user, login_user
from app.models import User
from app.forms import LoginForm
from flask import redirect, render_template, flash, request
# from flask_socketio import emit

@app.route("/")
@app.route("/index")
def index():
    test = socketio.async_mode
    return render_template('index.html')



# @app.route('/admin')
# def admin():
#     return render_template('admin.html')

# @app.route('/client')
# def client():
#     return render_template('client.html')

# @socketio.on('image')
# def image(data):
#     socketio.emit('response_back',data)