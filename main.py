import os
import shutil
import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from queue import Queue
from threading import Thread
from typing import List, Dict, Any

from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from joblib import dump

from scanner import FileMonitor
from analyzer import FileAnalyzer
from config import CATEGORY_FOLDERS, DIRECTORIES_TO_WATCH, MODEL_PATH, TEXT_EXTENSIONS, IMAGE_EXTENSIONS

# --- App Setup ---
app = FastAPI()
app.mount('/static', StaticFiles(directory='static'), name='static')

# --- In-Memory State ---
# This holds suggestions in memory. In a real app, this would be a database.
app.state.suggestions: List[Dict[str, Any]] = []

# Default training data, loaded on startup.
# This makes the "Model Training" tab in the UI functional immediately.
app.state.training_data = [
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


# --- Core Components ---
class Broadcaster:
    def __init__(self):
        self.conns = set()
        self.loop = None

    async def register(self, ws):
        await ws.accept()
        self.conns.add(ws)

    def unregister(self, ws):
        self.conns.discard(ws)

    def send_sync(self, message):
        if not self.loop:
            return
        asyncio.run_coroutine_threadsafe(self._broadcast(message), self.loop)

    async def _broadcast(self, message):
        to_remove = []
        for ws in list(self.conns):
            try:
                await ws.send_text(message)
            except Exception:
                to_remove.append(ws)
        for r in to_remove:
            self.conns.discard(r)


broadcaster = Broadcaster()
queue = Queue()
analyzer = FileAnalyzer(queue, broadcaster.send_sync)
monitor = FileMonitor(queue)


# --- Background Workers ---
@app.on_event('startup')
async def startup():
    broadcaster.loop = asyncio.get_running_loop()

    # Start the file monitor in a background thread
    Thread(target=monitor.start, daemon=True).start()

    # Start the analysis worker in a background thread
    Thread(target=analysis_worker, daemon=True).start()

    # Train a baseline model on startup if one doesn't exist
    if not os.path.exists(MODEL_PATH):
        print("No model found. Training initial model...")
        train_model(app.state.training_data)
        analyzer.reload_model()


def analysis_worker():
    """Worker thread to analyze files from the queue."""
    while True:
        res = analyzer.analyze_once()
        if res:
            # Add new suggestions to the beginning of the list
            app.state.suggestions.insert(0, res)


def train_model(data):
    """Internal function to train and save the model."""
    texts, labels = zip(*data)
    pipe = Pipeline([
        ('tfidf', TfidfVectorizer(stop_words='english', max_features=2000)),
        ('clf', LogisticRegression(max_iter=400))
    ])
    pipe.fit(texts, labels)
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    dump(pipe, MODEL_PATH)
    print(f"✅ Model trained and saved at {MODEL_PATH}")


# --- API Endpoints ---
@app.get('/')
async def root():
    """Serves the main HTML page."""
    return FileResponse('static/index.html')


@app.get('/api/suggestions')
async def suggestions(limit: int = 50):
    """Gets all current pending suggestions."""
    return app.state.suggestions[:limit]


@app.post('/api/apply')
async def apply_file(path: str, accept: bool = True):
    """Applies or rejects a suggestion."""
    s = app.state.suggestions
    match = next((i for i in s if i['path'] == path), None)

    if not match:
        raise HTTPException(status_code=404, detail='Suggestion not found. It might have been processed already.')

    if accept:
        # User accepted, move the file
        dest_folder = CATEGORY_FOLDERS.get(match['suggested_category'], CATEGORY_FOLDERS['Others'])
        dest_path = os.path.join(dest_folder, os.path.basename(path))

        try:
            os.makedirs(dest_folder, exist_ok=True)
            shutil.move(path, dest_path)
            s.remove(match)
            return {'moved_to': dest_path}
        except FileNotFoundError:
            s.remove(match)  # Remove suggestion if file is already gone
            raise HTTPException(status_code=404, detail='File not found. It may have been moved or deleted.')
        except Exception as e:
            raise HTTPException(status_code=500, detail=f'Failed to move file: {e}')

    else:
        # User rejected, just remove the suggestion
        s.remove(match)
        return {'rejected': path}


@app.get('/api/config')
async def get_config():
    """Endpoint to show the user the current configuration."""
    return {
        'watched_directories': DIRECTORIES_TO_WATCH,
        'category_folders': CATEGORY_FOLDERS,
        'text_extensions': TEXT_EXTENSIONS,
        'image_extensions': IMAGE_EXTENSIONS
    }


@app.get('/api/training_data')
async def get_training_data():
    """Gets the current list of training data samples."""
    return app.state.training_data


@app.post('/api/train')
async def trigger_training(new_samples: List[Dict[str, str]]):
    """
    Triggers a model retrain.
    Receives new samples from the UI and retrains the model.
    """
    # Add new samples to the in-memory list
    for sample in new_samples:
        if sample.get('text') and sample.get('label'):
            app.state.training_data.append((sample['text'], sample['label']))

    try:
        # Run the training logic
        train_model(app.state.training_data)

        # Tell the live analyzer to reload the new model
        analyzer.reload_model()

        return {'status': 'success', 'samples_trained': len(app.state.training_data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Model training failed: {e}')


# --- WebSocket Endpoint ---
@app.websocket('/ws')
async def ws(ws: WebSocket):
    """WebSocket for real-time updates."""
    await broadcaster.register(ws)
    try:
        while True:
            # Keep the connection alive
            await ws.receive_text()
    except WebSocketDisconnect:
        broadcaster.unregister(ws)
