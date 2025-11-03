from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from joblib import dump
import os
from config import MODEL_PATH

samples = [
    ('invoice for october payment', 'Invoices'),
    ('quarterly performance report', 'Reports'),
    ('john doe resume software engineer', 'Resumes'),
    ('family photo vacation', 'Photos'),
    ('random text note', 'Others'),
]

texts, labels = zip(*samples)

pipe = Pipeline([
    ('tfidf', TfidfVectorizer(stop_words='english', max_features=2000)),
    ('clf', LogisticRegression(max_iter=400))
])

pipe.fit(texts, labels)
os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
dump(pipe, MODEL_PATH)
print(f"✅ Model trained and saved at {MODEL_PATH}")
