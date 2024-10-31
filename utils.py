import os
from config import Config

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def evaluate_submission(file_path):
    # Placeholder for the actual evaluation logic
    # For example, read the file, compute metrics, and return the result
    # Here, we'll just return a dummy result
    return "Evaluation metrics would be displayed here."
