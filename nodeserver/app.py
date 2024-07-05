from flask import Flask, render_template
from flask_socketio import SocketIO, send
import socketio
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio_server = SocketIO(app)

# Flask route to serve the HTML file
@app.route('/')
def index():
    return render_template('index.html')

# Flask-SocketIO server event handler
@socketio_server.on('message')
def handle_message(msg):
    print('Message from client: ' + msg)
    send(msg, broadcast=True)

# Create a Socket.IO client
sio_client = socketio.Client()

# Handle connection event for the client
@sio_client.event
def connect():
    print('Client connection established')
    sio_client.send('Hello from Flask Client!')

# Handle message event for the client
@sio_client.event
def message(data):
    print('Message received by client: ', data)

# Handle disconnection event for the client
@sio_client.event
def disconnect():
    print('Client disconnected from server')

# Function to start the Socket.IO client
def start_client():
    sio_client.connect('http://localhost:3000')
    sio_client.wait()

if __name__ == '__main__':
    # Start the Socket.IO client in a separate thread
    client_thread = threading.Thread(target=start_client)
    client_thread.start()

    # Start the Flask server
    socketio_server.run(app, debug=True)
