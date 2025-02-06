from Cython.Plex import Empty
from numpy.matlib import empty

from app import app, db
from flask import render_template, url_for, flash, redirect, request, render_template, request, send_file, Flask, render_template, jsonify, Response
from forms import RegistrationForm, LoginForm, SubmissionForm
from models import User, Submission
from flask_login import login_user, current_user, logout_user, login_required
import os, shutil, time
from werkzeug.utils import secure_filename
from utils import allowed_file, evaluate_submission
import subprocess
import glob
import threading
from threading import Thread
import json


progress = 0
status_message = "Booting Script..."
terminal_output = []

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

@app.route("/challenge3", methods=['GET', 'POST'])
def challenge3():
    return render_template("challenge3.html")

@app.route("/run_script", methods=["POST"])
def run_script():
    global progress, status_message

    # Reset progress and status message
    progress = 0
    status_message = "Starting Script..."
    terminal_output = []

    def replace_directory(directory_path):
        if os.path.exists(directory_path):
            shutil.rmtree(directory_path)
        os.makedirs(directory_path)

    replace_directory("uploads")
    replace_directory("uploads/transcriptome_file1")
    replace_directory("uploads/transcriptome_file2")
    replace_directory("sqanti_results/results_file1")
    #replace_directory("sqanti_results/results_file2")
    replace_directory("uploads/coverage_files")
    replace_directory("uploads/coverage_files2")

    # Get file and form data from the request
    file = request.files.get('file')
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'transcriptome_file1', file.filename)
    file.save(file_path)

    # meta data
    organism = request.form.get('organism')
    platform = request.form.get('platform')
    tool = request.form.get('tool')
    library_preparation = request.form.get('library_preparation')
    data_category = request.form.get('data_category')

    # comparison
    selected_comparisons = request.form.getlist('comparison-dropdown')
    if not selected_comparisons:
        comparison = 'NA'
        comp_bambu = 'NA'
        comp_RNA_Bloom = 'NA'
        comp_rnaSPAdes = 'NA'
        comp_StringTie2_IsoQuant = 'NA'
    else:
        comparison = 'Custom'
        comp_bambu = 'Bambu' if 'Bambu' in selected_comparisons else 'NA'
        comp_RNA_Bloom = 'RNA_Bloom' if 'RNA_Bloom' in selected_comparisons else 'NA'
        comp_rnaSPAdes = 'rnaSPAdes' if 'rnaSPAdes' in selected_comparisons else 'NA'
        comp_StringTie2_IsoQuant = 'StringTie2_IsoQuant' if 'StringTie2_IsoQuant' in selected_comparisons else 'NA'

    annotation_file = request.files.get('annotation_file')
    if annotation_file and annotation_file.filename != '':
        annotation_path = os.path.join(app.config['UPLOAD_FOLDER'], 'transcriptome_file1', annotation_file.filename)
        annotation_file.save(annotation_path)
    else:
        annotation_path = 'NA'

    reference_file = request.files.get('reference_file')
    if reference_file and reference_file.filename != '':
        reference_path = os.path.join(app.config['UPLOAD_FOLDER'], 'transcriptome_file1', reference_file.filename)
        reference_file.save(reference_path)
    else:
        reference_path = 'NA'

    coverage = request.form.get('coverage_directory')
    if coverage == 'custom':
        coverage_files = request.files.getlist('coverage_directory[]')
        coverage_dir = coverage_files[0].filename.split('/')[0]
        replace_directory(os.path.join("uploads/coverage_files", coverage_dir))
        for cov_file in coverage_files:
            coverage_path = os.path.join(app.config['UPLOAD_FOLDER'], 'coverage_files', cov_file.filename)
            cov_file.save(coverage_path)
    else:
        coverage_dir = 'NA'

    file2 = request.files.get('file_2')
    file_path_2 = None
    if file2 is not None:
        file_path_2 = os.path.join(app.config['UPLOAD_FOLDER'], 'transcriptome_file2', file2.filename)
        file2.save(file_path_2)

    platform2 = request.form.get('platform_2')
    library_preparation2 = request.form.get('library_preparation_2')
    data_category2 = request.form.get('data_category_2')
    annotation_file2 = request.files.get('annotation_file_2')
    if annotation_file2 and annotation_file2.filename != '':
        annotation_path2 = os.path.join(app.config['UPLOAD_FOLDER'], 'transcriptome_file1', annotation_file2.filename)
        annotation_file2.save(annotation_path2)
    else:
        annotation_path2 = 'NA'

    reference_file_2 = request.files.get('reference_file_2')
    if reference_file_2 and reference_file_2.filename != '':
        reference_path2 = os.path.join(app.config['UPLOAD_FOLDER'], 'transcriptome_file1', reference_file_2.filename)
        reference_file_2.save(reference_path2)
    else:
        reference_path2 = 'NA'

    coverage2 = request.form.get('coverage_directory_2')
    if coverage2 == 'custom':
        coverage_files2 = request.files.getlist('coverage_directory_2[]')
        coverage_dir2 = coverage_files2[0].filename.split('/')[0]
        replace_directory(os.path.join("uploads/coverage_files2", coverage_dir2))
        for cov_file in coverage_files2:
            coverage_path2 = os.path.join(app.config['UPLOAD_FOLDER'], 'coverage_files2', cov_file.filename)
            cov_file.save(coverage_path2)
    else:
        coverage_dir2 = 'NA'

    sirv_list = request.files.get('sirv_file', 'NA')
    if sirv_list and sirv_list.filename != '':
        # Save the file if it exists
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'sirv_list', sirv_list.filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)  # Create directory if not exists
        sirv_list.save(file_path)
        sirv_list = os.path.join(app.config['UPLOAD_FOLDER'], 'sirv_list', sirv_list.filename)
    else:
        # If no file is provided, set sirv_list to NA
        sirv_list = "NA"

    ercc_list = request.files.get('ercc_file', 'NA')
    if ercc_list and ercc_list.filename != '':
        # Save the file if it exists
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'ercc_list', ercc_list.filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)  # Create directory if not exists
        ercc_list.save(file_path)
        ercc_list = os.path.join(app.config['UPLOAD_FOLDER'], 'ercc_list', ercc_list.filename)  # Set the file name to sirv_list
    else:
        # If no file is provided, set sirv_list to NA
        ercc_list = "NA"

    sequin_list = request.files.get('sequin_file', 'NA')
    if sequin_list and sequin_list.filename != '':
        # Save the file if it exists
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'sequin_list', sequin_list.filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)  # Create directory if not exists
        sequin_list.save(file_path)
        sequin_list = os.path.join(app.config['UPLOAD_FOLDER'], 'sequin_list', sequin_list.filename)  # Set the file name to sirv_list
    else:
        # If no file is provided, set sirv_list to NA
        sequin_list = "NA"

    # check if file 1 and file 2 are different for meta data
    if platform == platform2 and library_preparation == library_preparation2 and data_category == data_category2:
        status = 'ERROR: File 1 and File 2 seem to be the same! Exiting...'
        print(f'STATUS: {status}')
        return redirect(url_for('home'))

    # Run the script in a separate thread with the additional parameters
    thread = Thread(target=run_script_process, args=(file_path, organism, platform, library_preparation, tool, data_category, annotation_path, reference_path, coverage, coverage_dir,
                                                     file_path_2, platform2, library_preparation2, data_category2, annotation_path2, reference_path2, coverage2, coverage_dir2,
                                                     comparison, comp_bambu, comp_RNA_Bloom, comp_rnaSPAdes, comp_StringTie2_IsoQuant,
                                                     sirv_list, ercc_list, sequin_list))
    thread.start()

    return jsonify({"status": "Script started successfully!"})


def run_script_process(file_path, organism, platform, library_preparation, tool, data_category, annotation_path, reference_path, coverage, coverage_dir,
                       file_path_2, platform2, library_preparation2, data_category2, annotation_path_2, reference_path_2, coverage2, coverage_dir2,
                       comparison, comp_bambu, comp_RNA_Bloom, comp_rnaSPAdes, comp_StringTie2_IsoQuant,
                       sirv_list, ercc_list, sequin_list):

    global progress, status_message, terminal_output

    # Define the path to the script
    script_path = "lrgasp_event2_metrics/sqanti3_lrgasp.challenge3.py"

    # Run the script
    try:

        if file_path_2 is None:
            process = subprocess.Popen(
                ['python', script_path, file_path, organism, platform, library_preparation, tool, data_category, annotation_path, reference_path, coverage, coverage_dir,
                                comparison, comp_bambu, comp_RNA_Bloom, comp_rnaSPAdes, comp_StringTie2_IsoQuant,
                                sirv_list, ercc_list, sequin_list],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
        elif file_path_2 is not None:
            process = subprocess.Popen(
                ['python', script_path, file_path, organism, platform, library_preparation, tool, data_category, annotation_path, reference_path, coverage, coverage_dir,
                                file_path_2, platform2, library_preparation2, data_category2, annotation_path_2, reference_path_2, coverage2, coverage_dir2,
                                comparison, comp_bambu, comp_RNA_Bloom, comp_rnaSPAdes, comp_StringTie2_IsoQuant,
                                sirv_list, ercc_list, sequin_list],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

        for line in process.stdout:
            line = line.strip()
            print(line)
            terminal_output.append(line)

            if 'PROGRESS:' in line:
                progress = int(line.strip().split('PROGRESS:')[1])
                print(f"Progress updated to {progress}%")
            elif 'STATUS:' in line:
                status_message = line.strip().split('STATUS:')[1].strip()
                print(f"Status message updated to: {status_message}")

        process.wait()
        progress = 100
        status_message = 'Script Finished'

        # Move the generated report
        source = glob.glob("sqanti_results/results_file1/*.html")[0]
        destination = "static/report.html"
        shutil.move(source, destination)

    except Exception as e:
        print(f"Error running script: {e}")
        status_message = "Error running script"
        progress = 100  # Ensure progress reaches 100 on error

@app.route("/terminal_stream")
def terminal_stream():

    def generate():
        last_index = 0
        while True:
            # If new lines have been appended, yield them
            if last_index < len(terminal_output):
                new_lines = terminal_output[last_index:]
                for line in new_lines:
                    yield f"data: {line}\n\n"
                last_index = len(terminal_output)
            time.sleep(0.5)
    return Response(generate(), mimetype="text/event-stream")

@app.route("/progress_stream")
def progress_stream():
    """Stream progress updates to the client."""
    def generate():
        while True:
            global progress
            global status_message
            time.sleep(0.5)  # Check progress every 500ms
            data = json.dumps({'progress': progress, 'message': status_message})
            yield f"data: {data}\n\n"
            if progress >= 100:
                break
    return Response(generate(), mimetype="text/event-stream")



@app.route('/challenge3_results')
def challenge3_results():
    return render_template("show_report.html")



if __name__ == '__main__':
    app.run(debug=True)
