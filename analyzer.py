import os
import json
import time
from queue import Empty
from joblib import load
from feature_extractor import extract_text
from config import MODEL_PATH, TEXT_EXTENSIONS, IMAGE_EXTENSIONS


class FileAnalyzer:
    def __init__(self, q, ws_broadcaster=None):
        self.q = q
        self.ws_broadcaster = ws_broadcaster
        self.model = self._load_model()

    def _load_model(self):
        """Loads the scikit-learn model from disk."""
        try:
            if os.path.exists(MODEL_PATH):
                print("Loading existing model...")
                return load(MODEL_PATH)
            else:
                print("⚠️ Model file not found. Analyzer will use rule-based logic.")
        except Exception as e:
            print(f'⚠️ Model load failed: {e}. Analyzer will use rule-based logic.')
        return None

    def reload_model(self):
        """Reloads the model, typically after a retrain."""
        print("🔄 Reloading model...")
        self.model = self._load_model()
        print("✅ Model reloaded.")

    def rule_based(self, text):
        """Fallback rule-based classifier."""
        t = text.lower() if text else ''
        if 'invoice' in t or 'bill' in t:
            return 'Invoices', 0.6
        if 'report' in t or 'summary' in t:
            return 'Reports', 0.6
        if 'resume' in t or 'cv' in t:
            return 'Resumes', 0.7
        # This part is mostly for empty text files
        if 'photo' in t or 'image' in t:
            return 'Photos', 0.5
        return 'Others', 0.4

    def analyze_once(self, timeout=1.0):
        """Pulls one item from the queue and analyzes it."""
        try:
            path = self.q.get(timeout=timeout)
        except Empty:
            return None

        # Check if file still exists before processing
        if not os.path.exists(path):
            return None

        _, ext = os.path.splitext(path.lower())
        category = 'Others'
        conf = 0.1

        if ext in IMAGE_EXTENSIONS:
            # --- Image Pipeline ---
            # Hard-code images to 'Photos' category.
            # This is much more reliable than text analysis of metadata.
            category = 'Photos'
            conf = 0.90  # High confidence, it's a rule

        elif ext in TEXT_EXTENSIONS:
            # --- Text Pipeline ---
            text = extract_text(path)

            if not text.strip():
                # Use rule-based for empty files
                category, conf = self.rule_based(text)
            else:
                # Use ML model for files with text
                try:
                    if self.model:
                        category = self.model.predict([text])[0]
                        conf = float(max(self.model.predict_proba([text])[0]))
                    else:
                        # Fallback if model isn't loaded
                        category, conf = self.rule_based(text)
                except Exception:
                    # Fallback if model prediction fails
                    category, conf = self.rule_based(text)

        else:
            # Unknown file type, skip it
            return None

        result = {
            'path': path,
            'suggested_category': category,
            'confidence': conf,
            'timestamp': time.time()
        }

        # Send result to the web dashboard
        if self.ws_broadcaster:
            try:
                self.ws_broadcaster(json.dumps(result))
            except Exception as e:
                print(f"Failed to broadcast: {e}")

        return result
