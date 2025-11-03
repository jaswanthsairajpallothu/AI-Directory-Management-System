import os
import shutil
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from queue import Queue
from threading import Thread
from scanner import FileMonitor
from analyzer import FileAnalyzer
from config import CATEGORY_FOLDERS

app = FastAPI()
app.mount('/static', StaticFiles(directory='static'), name='static')

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

@app.on_event('startup')
async def startup():
    broadcaster.loop = asyncio.get_running_loop()
    Thread(target=monitor.start, daemon=True).start()
    Thread(target=analysis_worker, daemon=True).start()

def analysis_worker():
    while True:
        res = analyzer.analyze_once()
        if res:
            app.state.suggestions = getattr(app.state, 'suggestions', [])
            app.state.suggestions.insert(0, res)

@app.get('/api/suggestions')
async def suggestions(limit: int = 50):
    return getattr(app.state, 'suggestions', [])[:limit]

@app.post('/api/apply')
async def apply_file(path: str, accept: bool = True):
    s = getattr(app.state, 'suggestions', [])
    match = next((i for i in s if i['path'] == path), None)
    if not match:
        raise HTTPException(status_code=404, detail='Not found')
    if accept:
        dest = CATEGORY_FOLDERS.get(match['suggested_category'], CATEGORY_FOLDERS['Others'])
        os.makedirs(dest, exist_ok=True)
        shutil.move(path, os.path.join(dest, os.path.basename(path)))
        return {'moved_to': dest}
    s.remove(match)
    return {'rejected': path}

@app.websocket('/ws')
async def ws(ws: WebSocket):
    await broadcaster.register(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        broadcaster.unregister(ws)
