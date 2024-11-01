from flask import Flask, render_template, request, send_file
import os
import subprocess

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'  # Temporary upload folder
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)  # Ensure folder exists

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/challenge1')
def challenge1():
    return "<h2>Challenge 1</h2><p>This is the page for Challenge 1.</p>"

@app.route('/challenge2')
def challenge2():
    return "<h2>Challenge 2</h2><p>This is the page for Challenge 2.</p>"

@app.route('/challenge3')
def challenge3():
    return render_template("challenge_3.html")

@app.route('/run_script', methods=['POST'])
def run_script():
    # Retrieve the file, organism, and skipORF checkbox status
    file = request.files.get('file')
    organism = request.form.get('organism')
    skipORF = 'skipORF' in request.form  # True if checkbox is ticked, False otherwise

    # Check if a file and organism are provided
    if not file or file.filename == '':
        return "Please provide a valid file."
    if not organism:
        return "Please select an organism."

    # Save the uploaded file to the temporary upload folder
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)

    # Path to the script and output file, using the organism name in the output filename
    script_path = os.path.join(app.root_path, 'static', 'scripts', 'test.py')
    output_filename = f"{organism}_output.txt"
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)

    # Construct the command with conditional skipORF argument
    command = ['python', script_path, file_path, organism]
    if skipORF:
        command.append('--skipORF')

    # Run the script with the constructed command
    with open(output_path, 'w') as output_file:
        subprocess.run(command, stdout=output_file, stderr=output_file)

    # Send the output as a downloadable .txt file with organism name in the filename
    return send_file(output_path, as_attachment=True, download_name=output_filename)

if __name__ == '__main__':
    app.run()
