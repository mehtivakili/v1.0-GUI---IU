import serial
import struct
import zlib

def receive_imu_data(serial_port):
    ser = serial.Serial(serial_port, 115200, timeout=1)
    
    while True:
        if ser.in_waiting >= 36:  # Wait for the full packet
            data = ser.read(36)
            
            # Extract data
            Tio, = struct.unpack('d', data[0:8])
            accel = struct.unpack('fff', data[8:20])
            gyro = struct.unpack('fff', data[20:32])
            received_crc, = struct.unpack('I', data[32:36])
            
            # Calculate CRC32 to verify data integrity
            calculated_crc = zlib.crc32(data[0:32]) & 0xFFFFFFFF
            
            if received_crc == calculated_crc:
                print(f'Time: {Tio}, Accel: {accel}, Gyro: {gyro}')
            else:
                print('CRC mismatch, invalid data received.')

if __name__ == '__main__':
    receive_imu_data('COM6')  # Adjust the serial port name as necessary
