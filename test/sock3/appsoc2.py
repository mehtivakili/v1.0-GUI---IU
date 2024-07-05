from flask import Flask, render_template
from flask_socketio import SocketIO
from datetime import datetime
import eventlet

# Allow the server to handle more simultaneous connections
eventlet.monkey_patch()

app = Flask(__name__)
socketio = SocketIO(app)

@app.route('/')
def index():
    return render_template('index.html')

def send_time():
    while True:
        socketio.sleep(1)  # Send the time every second
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        socketio.emit('time', {'time': current_time})

@socketio.on('connect')
def handle_connect():
    socketio.start_background_task(send_time)

if __name__ == '__main__':
    socketio.run(app, debug=True)
