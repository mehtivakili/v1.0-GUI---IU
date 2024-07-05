import socketio

# Create a Socket.IO client
sio = socketio.Client()
sio.connect('http://localhost:5000')

@sio.on('update_dataa')
def on_message():
    print('I received a message!')

while True:
    on_message()



# # Define the event handler for the 'sensor_data' event
# @sio.event
# def sensor_data(data):
#     # print('Received sensor data:')
#     # print(f"Tio: {data['Tio']}")
#     # print(f"Accel: X: {data['acc'][0]}, Y: {data['acc'][1]}, Z: {data['acc'][2]}")
#     # print(f"Gyro: X: {data['gyro'][0]}, Y: {data['gyro'][1]}, Z: {data['gyro'][2]}")
#     print(data)

# # Define the event handler for connection
# @sio.event
# def connect():
#     print('Connection established')

# # Define the event handler for disconnection
# @sio.event
# def disconnect():
#     print('Disconnected from server')

# # Connect to the Socket.IO server
# sio.connect('http://localhost:5000')

# # Wait indefinitely for incoming messages
# sio.wait()
