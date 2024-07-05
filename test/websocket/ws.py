import asyncio
import websockets
from flask import Flask, render_template
from threading import Thread
import time
import queue

app = Flask(__name__)

data_queue = queue.Queue()

@app.route('/')
def index():
    return render_template('index.html')

async def send_data(websocket, path):
    while True:
        if not data_queue.empty():
            data = data_queue.get()
            await websocket.send(data)
        await asyncio.sleep(1)  # Check queue every second

def start_websocket_server():
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    start_server = websockets.serve(send_data, "localhost", 6789)
    loop.run_until_complete(start_server)
    loop.run_forever()

def generate_data():
    while True:
        current_time = f"Server time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        data_queue.put(current_time)
        time.sleep(2)  # Generate data every 2 seconds

if __name__ == '__main__':
    websocket_thread = Thread(target=start_websocket_server)
    websocket_thread.start()

    data_thread = Thread(target=generate_data)
    data_thread.start()

    app.run(debug=True, use_reloader=False)
