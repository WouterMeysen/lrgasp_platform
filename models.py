from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# User model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    submissions = db.relationship('Submission', backref='author', lazy=True)

# Submission model
class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    submission_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_file = db.Column(db.String(100), nullable=False)
    evaluation_result = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
