from flask import Flask, request, render_template, jsonify, send_from_directory
from flask_cors import CORS
import os
import esptool
import serial.tools.list_ports
import socket
import subprocess
import serial
import struct
import threading
import time
import zlib

app = Flask(__name__)
CORS(app)

FIRMWARE_BASE_PATH = 'firmwares'
serial_port = None
serial_thread = None
serial_running = False

def get_network_info():
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    ssid = get_connected_ssid()
    network_info = {
        "hostname": hostname,
        "local_ip": local_ip,
        "ssid": ssid
    }
    return network_info

def get_connected_ssid():
    try:
        result = subprocess.check_output("netsh wlan show interfaces", shell=True).decode()
        for line in result.split("\n"):
            if "SSID" in line:
                ssid = line.split(":")[1].strip()
                return ssid
    except Exception as e:
        print(f"Could not get SSID: {e}")
        return "Unknown"

@app.route('/')
def index():
    network_info = get_network_info()
    return render_template('index.html', network_info=network_info)

@app.route('/firmware')
def firmware():
    network_info = get_network_info()
    return render_template('firmware.html', network_info=network_info)

@app.route('/data_acquisition')
def data_acquisition():
    network_info = get_network_info()
    return render_template('data_acquisition.html', network_info=network_info)

@app.route('/calibration')
def calibration():
    network_info = get_network_info()
    return render_template('calibration.html', network_info=network_info)

@app.route('/python_serial', methods=['GET', 'POST'])
def python_serial():
    if request.method == 'POST':
        # try:
        #     port = request.form['port']
        #     baudrate = int(request.form['baudrate'])
        #     is_binary = request.form.get('is_binary', 'false') == 'true'
        #     open_serial_port(port, baudrate, is_binary)
        #     return jsonify(status='success')
        # except KeyError as e:
        #     return jsonify(status='error', message=f"Missing form key: {str(e)}")
        # except Exception as e:
        #     return jsonify(status='error', message=str(e))
    # else:
        network_info = get_network_info()
        return render_template('python_serial.html', network_info=network_info)

@app.route('/get_ports', methods=['GET'])
def get_ports():
    ports = list(serial.tools.list_ports.comports())
    port_list = [{'device': port.device, 'description': port.description} for port in ports]
    return jsonify(port_list)

@app.route('/open_serial', methods=['POST'])
def open_serial():
    try:
        port = request.form['port']
        baudrate = int(request.form['baudrate'])
        is_binary = request.form.get('is_binary', 'false') == 'true'
        open_serial_port(port, baudrate, is_binary)
        return jsonify(status='success')
    except KeyError as e:
        return jsonify(status='error', message=f"Missing form key: {str(e)}")
    except Exception as e:
        return jsonify(status='error', message=str(e))

def open_serial_port(port, baudrate, is_binary):
    global serial_port, serial_thread, serial_running

    if serial_port and serial_port.is_open:
        serial_port.close()

    serial_port = serial.Serial(port, baudrate, timeout=1)
    serial_running = True
    serial_thread = threading.Thread(target=read_serial_data, args=(is_binary,))
    serial_thread.start()


def calculate_checksum(data):
    return sum(data) & 0xFF

def read_serial_data(is_binary):
    global serial_running
    while serial_running:
        if serial_port.in_waiting >= 36:  # Wait for the full packet
            data = serial_port.read(36)
            
            # Extract data
            Tio, = struct.unpack('d', data[0:8])
            accel = struct.unpack('fff', data[8:20])
            gyro = struct.unpack('fff', data[20:32])
            received_crc, = struct.unpack('I', data[32:36])
            
            # Calculate CRC32 to verify data integrity
            calculated_crc = zlib.crc32(data[0:32]) & 0xFFFFFFFF
            
            if received_crc == calculated_crc:
                message = f'Time: {Tio}, Accel: {accel}, Gyro: {gyro}'
            else:
                message = 'CRC mismatch, invalid data received.'
            
            socketio.emit('serial_data', {'data': message})
        time.sleep(0.05)

@app.route('/close_serial', methods=['POST'])
def close_serial():
    global serial_port, serial_running
    serial_running = False
    if serial_port and serial_port.is_open:
        serial_port.close()
    return jsonify(status='success')

if __name__ == "__main__":
    from flask_socketio import SocketIO
    socketio = SocketIO(app)
    socketio.run(app, debug=True)
