from flask import Flask, request, render_template, jsonify, send_from_directory, send_file
from flask_cors import CORS
import os
import esptool
import serial.tools.list_ports
import socket
import subprocess
import serial
import struct
import threading 
from threading import Thread
import time
import zlib
import csv
import queue
from flask_socketio import SocketIO
# import eventlet
import socketio

import matplotlib
matplotlib.use('Agg')  # Use a non-GUI backend

import matplotlib.pyplot as plt

import pandas as pd

sio_client = socketio.Client()

data_queue = queue.Queue()
# Allow the server to handle more simultaneous connections
# eventlet.monkey_patch()

app = Flask(__name__)

socketio = SocketIO(app)

message_queue = queue.Queue()

CORS(app)

# Calibration parameters
calibration_enabled = False
Ta = [[1, -0.00546066, 0.00101399], [0, 1, 0.00141895], [0, 0, 1]]
Ka = [[0.00358347, 0, 0], [0, 0.00358133, 0], [0, 0, 0.00359205]]
Tg = [[1, -0.00614889, -0.000546488], [0.0102258, 1, 0.000838491], [0.00412113, 0.0020154, 1]]
Kg = [[0.000531972, 0, 0], [0, 0.000531541, 0], [0, 0, 0.000531]]
acce_bias = [-8.28051, -4.6756, -0.870355]
gyro_bias = [4.53855, 4.001, -1.9779]

# calibration_enabled = False
# Ta = [[1, -0.0033593, -0.00890639], [0, 1, -0.0213341], [0, 0, 1]]
# Ka = [[0.00241278, 0, 0], [0, 0.00242712, 0], [0, 0, 0.00241168]]
# Tg = [[1, 0.00593634, 0.00111101], [0.00808812, 1, -0.0535569], [0.0253076, -0.0025513, 1]]
# Kg = [[0.000209295, 0, 0], [0, 0.000209899, 0], [0, 0, 0.000209483]]
# acce_bias = [33124.2, 33275.2, 32364.4]
# gyro_bias = [32777.1, 32459.8, 32511.8]



def apply_calibration(accel, gyro):
    acce_calibrated = [
        ((int)(((Ka[0][0] * Ta[0][0]) + (Ka[0][1] * Ta[1][1]) + (Ka[0][2] * Ta[2][2])) * (accel[0] - acce_bias[0]) * 1000)) / 1000.0,
        ((int)(((Ka[1][1] * Ta[1][1]) + (Ka[1][2] * Ta[2][2])) * (accel[1] - acce_bias[1]) * 1000)) / 1000.0,
        ((int)(((Ka[2][2] * Ta[2][2])) * (accel[2] - acce_bias[2]) * 1000)) / 1000.0
    ]
    gyro_calibrated = [
        ((int)(((Kg[0][0] * Tg[0][0]) + (Kg[0][1] * Tg[1][1]) + (Kg[0][2] * Tg[2][2])) * (gyro[0] - gyro_bias[0]) * 1000)) / 1000.0,
        ((int)(((Kg[1][0] * Tg[1][0]) + (Kg[1][1] * Tg[1][1]) + (Kg[1][2] * Tg[2][2])) * (gyro[1] - gyro_bias[1]) * 1000)) / 1000.0,
        ((int)(((Kg[2][0] * Tg[2][0]) + (Kg[2][1] * Tg[2][1]) + (Kg[2][2] * Tg[2][2])) * (gyro[2] - gyro_bias[2]) * 1000)) / 1000.0
    ]
    return acce_calibrated, gyro_calibrated


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

@app.route('/flash', methods=['POST'])
def flash():
    port = request.form['port']
    baudrate = request.form['baudrate']
    group = request.form['group']


    folder_path = os.path.join(FIRMWARE_BASE_PATH, group)
    print(folder_path)
    if not os.path.exists(folder_path):
        return 'Invalid group selected'

    bootloader_path = os.path.join(folder_path, 'bootloader.bin')
    partitions_path = os.path.join(folder_path, 'partitions.bin')
    firmware_path = os.path.join(folder_path, 'firmware.bin')

    

    flash_firmware(port, baudrate, bootloader_path, partitions_path, firmware_path)
    
    return 'Firmware flashed successfully'

def flash_firmware(port, baudrate, bootloader_path, partitions_path, firmware_path):
    esptool_args = [
        '--chip', 'esp32',
        '--port', port,
        '--baud', baudrate,
        'write_flash',
        '0x1000', bootloader_path,
        '0x8000', partitions_path,
        '0x10000', firmware_path
    ]
    esptool.main(esptool_args)
    
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
    # sss.emit("data_rate","aaaa")
    # print(sss)
    # print("ashfuiahf")
    serial_port = serial.Serial(port, baudrate, timeout=1)
    serial_running = True
    serial_thread = threading.Thread(target=read_serial_data, args=(is_binary,))
    serial_thread.start()



def calculate_checksum(data):
    return sum(data) & 0xFF

offset = 0
from datetime import datetime

def read_serial_data(true):
    global serial_running
    global last_Tio 
    global packets_count
    global current_second_start
    global offset
    global Timer
    global count
    global set_offset
    global most_recent_acc_file
    global most_recent_gyro_file
    global calibration_enabled

    # offset = 0  # Set this to your required offset
    last_Tio = 0
    # Timer = 10000
    current_second_start = 0
    packets_count = 0
    set_offset = False
    start_time =0
    end_time = 0
    time_IO = 0
    cycle_counter = 0  # Counter to keep track of cycles
    # Send the 'c' character to request data
    check = 'c'
    serial_port.write(check.encode())
    # with open('data_log.csv', mode='a', newline='') as file:
    #     writer = csv.writer(file)
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    acc_filename = f"acc-{timestamp}.csv"
    gyro_filename = f"gyro-{timestamp}.csv"


    # Update the most recent filenames
    most_recent_acc_file = acc_filename
    most_recent_gyro_file = gyro_filename

    # most_recent_acc_file = "test_imu_acc.calib"
    # most_recent_gyro_file = "test_imu_gyro.calib"



    while serial_running:
        if serial_port.in_waiting >= 29:  # Wait for the full packet
            first_byte = serial_port.read(1)  # Read the first byte
            if first_byte == check.encode():  # Check if it matches 'c'
                data = serial_port.read(28)  # Read the remaining 28 bytes
                if len(data) == 28:
                    global numbers
                    numbers = struct.unpack('<7f', data)  # Unpack the 7 floats
                    if set_offset == False:
                        offset = numbers[0]
                        set_offset = True
                    # Extract data
                    Tio = numbers[0] - offset
                    accel = numbers[1:4]
                    gyro = numbers[4:7]

                    if calibration_enabled:
                        accel, gyro = apply_calibration(accel, gyro)

                    # Initialize the first Tio and current second start
                    if last_Tio is None:
                        last_Tio = Tio
                        current_second_start = int(Tio)
                                            # Increment the cycle counter
                    cycle_counter += 1

                    # Emit data every 20 cycles
                    if cycle_counter >= 35:
                        sio_client.emit('sensor_data', {'Tio': Tio, 'accel': accel, 'gyro': gyro})
                        cycle_counter = 0  # Reset the counter
                    # Write data to CSV file

                    # Check for Tio change and calculate rate
                    if int(Tio) != current_second_start:
                        # Print the rate for the last second
                        print(f"Tio: {Tio}, Data rate: {packets_count} packets in the last second")
                    # Emit data to all connected clients through the Flask server
                        # socketio.emit('sensor_data', {'Tio': Tio, 'accel': accel, 'gyro': gyro})
                    
                    # Emit data to the Node.js server
                        # sio_client.emit('sensor_data', {'Tio': Tio, 'accel': accel, 'gyro': gyro})

                        count = packets_count
                        # data_queue.put(packets_count)
                        # print(offset)
                        # Reset the packet count for the new second
                        packets_count = 0
                        current_second_start = int(Tio)

                    # Increment the packet count for the current second
                    packets_count += 1
                    last_Tio = Tio

                    if (Timer != 0) :
                        if (start_time != 0):
                            # Save data to CSV
                            # writer.writerow([Tio, accel[0], accel[1], accel[2], gyro[0], gyro[1], gyro[2]])
                            end_time = time.time()
                            if (end_time - start_time < Timer):
                                # break
                                # Open the CSV file in append mode
                                # with open('data_log.csv', mode='a', newline='') as file:
                                #     writer = csv.writer(file)
                                #     # Save data to CSV
                                #     writer.writerow([Tio, accel[0], accel[1], accel[2], gyro[0], gyro[1], gyro[2]])
                                # with open(acc_filename, mode='a', newline='') as acc_file:
                                #     acc_writer = csv.writer(acc_file)
                                #     # acc_writer.writerow([Tio, accel[0], accel[1], accel[2]])
                                #     acc_writer.writerow([f"{Tio:.7e}", f"{accel[0]:.7e}", f"{accel[1]:.7e}", f"{accel[2]:.7e}"])
                                # with open(gyro_filename, mode='a', newline='') as gyro_file:
                                #     gyro_writer = csv.writer(gyro_file)
                                #     # gyro_writer.writerow([Tio, gyro[0], gyro[1], gyro[2]])
                                #     gyro_writer.writerow([f"{Tio:.7e}", f"{gyro[0]:.7e}", f"{gyro[1]:.7e}", f"{gyro[2]:.7e}"])

                                formatted_accel = [f"{Tio:.7e}", f"{accel[0]:.7e}", f"{accel[1]:.7e}", f"{accel[2]:.7e}"]
                                formatted_gyro = [f"{Tio:.7e}", f"{gyro[0]:.7e}", f"{gyro[1]:.7e}", f"{gyro[2]:.7e}"]

                                # formatted_accel_str = "   ".join(formatted_accel)
                                # formatted_gyro_str = "   ".join(formatted_gyro)

                                with open(acc_filename, mode='a', newline='') as acc_file:
                                    acc_writer = csv.writer(acc_file, delimiter=' ', quoting=csv.QUOTE_MINIMAL)
                                    acc_writer.writerow(formatted_accel)
                                with open(gyro_filename, mode='a', newline='') as gyro_file:
                                    gyro_writer = csv.writer(gyro_file, delimiter=' ', quoting=csv.QUOTE_MINIMAL)
                                    gyro_writer.writerow(formatted_gyro)                        
                        else: 
                            start_time = time.time()


                else:
                    print(f"Expected 28 bytes but received {len(data)} bytes.")
            else:
                print("First byte did not match expected 'c' character.")
                # Handle unexpected first byte case if needed

Timer = 0

# def send_data():
#     global count
#     while True:
#         if count != 0:
#             print(count)
#         else:
#             print("No data to send")
#             time.sleep(1)

def start_client():
    sio_client.connect('http://localhost:3000')  # Connect to Node.js server on port 3000
    sio_client.wait()


@app.route('/start_recording', methods=['POST'])
def start_recording():
    print('haha')
    
    global offset, Timer, acc_filename, gyro_filename
    Timer = float(request.form['offset'])
    if True:
        # serial_port.write(b'c')
        # time.sleep(0.1)
        # data = serial_port.read(28)
        if True:
            # numbers = struct.unpack('<7f', data)
            offset = numbers[0]
            timestamp = datetime.now().strftime("%Y%m%d%H%M")
            acc_filename = f"acc-{timestamp}.csv"
            gyro_filename = f"gyro-{timestamp}.csv"


            # Update the most recent filenames
            most_recent_acc_file = acc_filename
            most_recent_gyro_file = gyro_filename

            # print(offset)
            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'error', 'message': 'Failed to read offset'})
    return jsonify({'status': 'error', 'message': 'Serial port not opened'})

count = 0

@app.route('/close_serial', methods=['POST'])
def close_serial():
    global serial_port, serial_running, set_offset
    set_offset = False
    serial_running = False
    if serial_port and serial_port.is_open:
        serial_port.close()
    return jsonify(status='success')

@app.route('/stop_recording', methods=['GET'])
def stop_recording():
    print("hahahasdfafafads")
    # Implement your stop recording logic here
        # Delete the most recent files
    if most_recent_acc_file and os.path.exists(most_recent_acc_file):
        os.remove(most_recent_acc_file)
        print(f"Deleted file: {most_recent_acc_file}")
    if most_recent_gyro_file and os.path.exists(most_recent_gyro_file):
        os.remove(most_recent_gyro_file)
        print(f"Deleted file: {most_recent_gyro_file}")
    return jsonify(status='successfully stopped')


@app.route('/plot_data', methods=['GET'])
def plot_data():
    global most_recent_acc_file, most_recent_gyro_file
    # recording_name = request.args.get('recordingName')
    # if not recording_name:
    #     return jsonify(status='error', message='Recording name not provided'), 400

    # # Construct file paths based on recording name
    # acc_file_path = most_recent_acc_file
    # gyro_file_path = most_recent_gyro_file

    try:
        # Call the plotting script as a subprocess
        result = subprocess.run(
            ["python3", "plot_script.py", most_recent_acc_file, most_recent_gyro_file],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            # Log the stderr output for debugging
            print(f"Error: {result.stderr.strip()}")
            return jsonify(status='error', message=result.stderr.strip()), 500

        plot_file_path = result.stdout.strip()

        return send_file(plot_file_path, mimetype='image/png')
    except FileNotFoundError as e:
        return jsonify(status='error', message=str(e)), 404

import requests  # Ensure you have requests module installed

@app.route('/calibrate', methods=['GET'])
def calibrate():
    # most_recent_acc_file ="xsens_acc.mat"
    # most_recent_gyro_file = "xsens_gyro.mat"
    if most_recent_acc_file and most_recent_gyro_file:
        command = f"./test_imu_calib {most_recent_acc_file} {most_recent_gyro_file}"
        try:
            child = pexpect.spawn(command)
            for _ in range(3):
                child.sendline("")  # Send "Enter" key press
                time.sleep(3)  # Wait for 2 seconds
            child.expect(pexpect.EOF)
            output = child.before.decode('utf-8')

            # Read the calibration files
            try:
                with open("test_imu_acc.calib", "r") as acc_calib_file:
                    acc_calib_data = acc_calib_file.read()
                with open("test_imu_gyro.calib", "r") as gyro_calib_file:
                    gyro_calib_data = gyro_calib_file.read()
                
                calib_params = {
                    'acc_calib': acc_calib_data,
                    'gyro_calib': gyro_calib_data
                }
                
                # Return the calibration data as a JSON response
                return jsonify({'status': 'success', 'output': output, 'calib_params': calib_params})
                
                if response.status_code == 200:
                    return jsonify({'status': 'success', 'output': output, 'server_response': response.json()})
                else:
                    return jsonify({'status': 'error', 'message': 'Failed to send calibration data to the server'})
                
            except Exception as e:
                return jsonify({'status': 'error', 'message': f'Failed to read calibration files: {str(e)}'})
            

            # return jsonify({'status': 'success', 'output': output})
        except pexpect.ExceptionPexpect as e:
            return jsonify({'status': 'error', 'message': str(e)})
    else:
        return jsonify({'status': 'error', 'message': 'No recent files to calibrate'})

@app.route('/get_calibrated_data', methods=['GET'])
def get_calibrated_data():
    global calibration_enabled
    calibration_enabled = True
    return jsonify(status='success', message='Calibrated data will now be applied')

import re

def parse_calibration_data(data):
    lines = data.strip().split('\n')
    parsed_data = []
    for line in lines:
        numbers = re.findall(r'[-+]?\d*\.\d+|\d+', line)
        if numbers:
            parsed_data.append([float(num) for num in numbers])
    return parsed_data

@app.route('/upload_calibration_files', methods=['POST'])
def upload_calibration_files():
    data = request.json
    acc_data = data['accData']
    gyro_data = data['gyroData']

    try:
        global Ta, Ka, acce_bias
        global Tg, Kg, gyro_bias

        acc_parsed = parse_calibration_data(acc_data)
        gyro_parsed = parse_calibration_data(gyro_data)

        if len(acc_parsed) < 9 or len(gyro_parsed) < 9:
            raise ValueError("Incomplete calibration data")

        Ta = acc_parsed[:3]
        Ka = acc_parsed[3:6]
        acce_bias = [row[0] for row in acc_parsed[6:9]]

        Tg = gyro_parsed[:3]
        Kg = gyro_parsed[3:6]
        gyro_bias = [row[0] for row in gyro_parsed[6:9]]
        print(Ta, Ka, acce_bias)
        print(Tg, Kg, gyro_bias)

        return jsonify(status='success', message='Calibration parameters updated')
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify(status='error', message=str(e)), 400


import pexpect

# @app.route('/receive_calib_params', methods=['POST'])
# def receive_calib_params():
#     data = request.json
#     if 'acc_calib' in data and 'gyro_calib' in data:
#         acc_calib = data['acc_calib']
#         gyro_calib = data['gyro_calib']
#         print("Received Accelerometer Calibration Data:", acc_calib)
#         print("Received Gyroscope Calibration Data:", gyro_calib)
#         return jsonify({'status': 'success', 'message': 'Calibration data received'})
#     else:
#         return jsonify({'status': 'error', 'message': 'Invalid calibration data'}), 400


# @socketio.on('connect')
# def handle_connect(socket):
#     # while not message_queue.empty():
#     #     print("oomad")   
#     # print(socket)
#     socketio.emit('connect', {'data': 'Connected'})

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


if __name__ == "__main__":
    # Start the Socket.IO client in a separate thread
    client_thread = threading.Thread(target=start_client)
    client_thread.start()
    socketio.run(app, debug=True)

        

