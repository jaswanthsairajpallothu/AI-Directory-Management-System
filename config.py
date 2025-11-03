import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

DIRECTORIES_TO_WATCH = [os.path.join(BASE_DIR, 'watched')]

CATEGORY_FOLDERS = {
    'Invoices': os.path.join(BASE_DIR, 'sorted', 'Invoices'),
    'Reports': os.path.join(BASE_DIR, 'sorted', 'Reports'),
    'Photos': os.path.join(BASE_DIR, 'sorted', 'Photos'),
    'Resumes': os.path.join(BASE_DIR, 'sorted', 'Resumes'),
    'Others': os.path.join(BASE_DIR, 'sorted', 'Others'),
}

MODEL_PATH = os.path.join(BASE_DIR, 'models', 'text_classifier.joblib')

# Create directories automatically
for path in DIRECTORIES_TO_WATCH + list(CATEGORY_FOLDERS.values()):
    os.makedirs(path, exist_ok=True)

TEXT_EXTENSIONS = ['.pdf', '.txt', '.docx']
IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg']
