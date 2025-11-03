import os
import json
import time
from queue import Empty
from joblib import load
from feature_extractor import extract_text
from config import MODEL_PATH

class FileAnalyzer:
    def __init__(self, q, ws_broadcaster=None):
        self.q = q
        self.ws_broadcaster = ws_broadcaster
        self.model = self._load_model()

    def _load_model(self):
        try:
            if os.path.exists(MODEL_PATH):
                return load(MODEL_PATH)
        except Exception as e:
            print('⚠️ Model load failed:', e)
        return None

    def rule_based(self, text):
        t = text.lower() if text else ''
        if 'invoice' in t or 'bill' in t:
            return 'Invoices', 0.6
        if 'report' in t or 'summary' in t:
            return 'Reports', 0.6
        if 'resume' in t or 'cv' in t:
            return 'Resumes', 0.7
        if 'photo' in t or 'image' in t:
            return 'Photos', 0.5
        return 'Others', 0.4

    def analyze_once(self, timeout=1.0):
        try:
            path = self.q.get(timeout=timeout)
        except Empty:
            return None

        text = extract_text(path)
        if not text.strip():
            category, conf = self.rule_based(text)
        else:
            try:
                if self.model:
                    category = self.model.predict([text])[0]
                    conf = float(max(self.model.predict_proba([text])[0]))
                else:
                    category, conf = self.rule_based(text)
            except Exception:
                category, conf = self.rule_based(text)

        result = {
            'path': path,
            'suggested_category': category,
            'confidence': conf,
            'timestamp': time.time()
        }

        if self.ws_broadcaster:
            try:
                self.ws_broadcaster(json.dumps(result))
            except Exception:
                pass

        return result
