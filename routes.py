from app import app, db
from flask import render_template, url_for, flash, redirect, request
from forms import RegistrationForm, LoginForm, SubmissionForm
from models import User, Submission
from flask_login import login_user, current_user, logout_user, login_required
import os
from werkzeug.utils import secure_filename
from utils import allowed_file, evaluate_submission

@app.route("/")
@app.route("/home")
def home():
    return render_template('index.html')

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        # Hash the password here in production!
        user = User(username=form.username.data, email=form.email.data, password=form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Account created! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.password == form.password.data:
            # For security, implement password hashing!
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Login unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route("/dashboard")
@login_required
def dashboard():
    submissions = Submission.query.filter_by(author=current_user)
    return render_template('dashboard.html', title='Dashboard', submissions=submissions)

@app.route("/submit", methods=['GET', 'POST'])
@login_required
def submit():
    form = SubmissionForm()
    if form.validate_on_submit():
        if form.data_file.data and allowed_file(form.data_file.data.filename):
            filename = secure_filename(form.data_file.data.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            form.data_file.data.save(file_path)
            # Evaluate the submission
            evaluation_result = evaluate_submission(file_path)
            # Save submission to the database
            submission = Submission(data_file=filename, evaluation_result=evaluation_result, author=current_user)
            db.session.add(submission)
            db.session.commit()
            flash('Submission successful!', 'success')
            return redirect(url_for('dashboard'))
    return render_template('upload.html', title='Submit Prediction', form=form)

@app.route("/submission/<int:submission_id>")
@login_required
def submission(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    if submission.author != current_user:
        abort(403)
    return render_template('submission.html', title='Submission Detail', submission=submission)

@app.route("/data")
def data():
    return render_template('data.html', title='Data')