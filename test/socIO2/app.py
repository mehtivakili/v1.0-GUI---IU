from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import serial
import struct
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# Serial port configuration
# serial_port = serial.Serial('COM6', 115200, timeout=1)  # Update with your serial port and baud rate
serial_running = True

def read_serial_data():
    global serial_running
    global last_Tio 
    global packets_count
    global current_second_start
    global offset
    global Timer

    while True:
        # Send data to the client
        socketio.emit('aa', {
            'Tio': 'Tio',
            'accel': 'accel',
            'gyro': 'gyro'
        })

    last_Tio = 0
    current_second_start = 0
    packets_count = 0
    start_time =0
    end_time = 0
    check = 'c'
    # serial_port.write(check.encode())
    set_offset = False
    socket_count = 0

    while False:
        if serial_port.in_waiting >= 0:  # Wait for the full packet
            first_byte = serial_port.read(1)  # Read the first byte
            if first_byte == b'c':  # Check if it matches 'c'
                data = serial_port.read(28)  # Read the remaining 28 bytes
                if len(data) == 28:
                    socket_count += 1
                    numbers = struct.unpack('<7f', data)  # Unpack the 7 floats
                    if not set_offset:
                        offset = numbers[0]
                        set_offset = True
                    # Extract data
                    Tio = numbers[0] - offset
                    accel = numbers[1:4]
                    gyro = numbers[4:7]
                    if socket_count == 19:
                        socket_count = 0
                        # Send data to the client
                        socketio.emit('aa', {
                            'Tio': Tio,
                            'accel': accel,
                            'gyro': gyro
                        })

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    # Start the serial data reading in a separate thread
    threading.Thread(target=read_serial_data).start()

if __name__ == '__main__':
    socketio.run(app, debug=True)
