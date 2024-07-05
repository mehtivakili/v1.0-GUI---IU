import serial
import struct
import zlib

# Assuming serial_port is already defined and opened
# Read the expected number of bytes (28 data bytes + 4 CRC bytes)
serial_port = serial.Serial('COM6', 115200, timeout=1)
# Assuming serial_port is already defined and opened
# Read the debug information first
# Read the debug information first
debug_info = serial_port.read_until(b'\nCRC value: ')
# Read the rest of the debug information
debug_info += serial_port.read(8)  # 8 characters for the CRC value and newline

# Print debug information
print(debug_info.decode('utf-8'))

# Read the expected number of bytes (28 data bytes + 4 CRC bytes)
data = serial_port.read(32)

# Ensure we have read the correct amount of data
if len(data) != 32:
    raise RuntimeError(f"Expected 32 bytes, got {len(data)} bytes")

# Separate the data and the CRC
data_bytes = data[:28]
crc_bytes = data[28:]

# Unpack the data into floats
numbers = struct.unpack('<7f', data_bytes)

# Extract individual values
Tio = numbers[0]
accel = numbers[1:4]
gyro = numbers[4:7]

# Compute the CRC of the received data
computed_crc = zlib.crc32(data_bytes) & 0xFFFFFFFF

# Unpack the received CRC
(received_crc,) = struct.unpack('<I', crc_bytes)

# Print debug information
print(f"Data bytes: {data_bytes}")
print("Data bytes in hex:")
print(" ".join(f"{byte:02X}" for byte in data_bytes))
print(f"CRC bytes: {crc_bytes}")
print("CRC bytes in hex:")
print(" ".join(f"{byte:02X}" for byte in crc_bytes))
print(f"Computed CRC: {computed_crc:08X}")
print(f"Received CRC: {received_crc:08X}")

# Compare the received CRC with the computed CRC
if computed_crc == received_crc:
    print("CRC check passed")
    print(f"Tio: {Tio}")
    print(f"Accel: {accel}")
    print(f"Gyro: {gyro}")
else:
    print("CRC check failed")