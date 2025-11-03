from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from joblib import dump
import os
from config import MODEL_PATH

# --- Expanded samples for a better baseline model ---
samples = [
    ('invoice for october payment', 'Invoices'),
    ('attached is our bill for services', 'Invoices'),
    ('payment due for invoice 992A', 'Invoices'),
    ('quarterly performance report', 'Reports'),
    ('annual summary sales report', 'Reports'),
    ('end of year business report', 'Reports'),
    ('john doe resume software engineer', 'Resumes'),
    ('jane smith cv marketing', 'Resumes'),
    ('application for project manager role', 'Resumes'),
    ('attached is my resume', 'Resumes'),
    ('family photo vacation', 'Photos'),
    ('team picture at retreat', 'Photos'),
    ('random text note', 'Others'),
    ('meeting minutes', 'Others'),
    ('project proposal draft', 'Others'),
    ('shopping list groceries', 'Others'),
    ('company update newsletter', 'Reports'),
    ('receipt for new laptop', 'Invoices'),
    ('candidate profile: senior developer', 'Resumes'),
    ('holiday trip photos', 'Photos')
]

texts, labels = zip(*samples)

pipe = Pipeline([
    ('tfidf', TfidfVectorizer(stop_words='english', max_features=2000)),
    ('clf', LogisticRegression(max_iter=400))
])

pipe.fit(texts, labels)
os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
dump(pipe, MODEL_PATH)
print(f"✅ Model trained with {len(samples)} samples and saved at {MODEL_PATH}")
