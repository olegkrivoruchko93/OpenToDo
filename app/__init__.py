from flask import Flask
from flask_login import LoginManager

from app.models import db

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-me-in-production'
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mydatabase.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

login_manager = LoginManager(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'You must be authorized'

db.init_app(app)

def create_app():
    with app.app_context():
        db.create_all()
    app.run(debug=True)
