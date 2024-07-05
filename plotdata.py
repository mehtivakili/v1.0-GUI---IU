import pandas as pd
import matplotlib.pyplot as plt

# Define the column names
column_names = ['Tio', 'Accel X', 'Accel Y', 'Accel Z', 'Gyro X', 'Gyro Y', 'Gyro Z']

# Read the CSV file with the defined column names
data = pd.read_csv('data_log.csv', names=column_names)

# Plotting the acceleration data
plt.figure(figsize=(12, 6))

plt.subplot(2, 1, 1)
plt.plot(data['Tio'], data['Accel X'], label='Accel X')
plt.plot(data['Tio'], data['Accel Y'], label='Accel Y')
plt.plot(data['Tio'], data['Accel Z'], label='Accel Z')
plt.xlabel('Time')
plt.ylabel('Acceleration')
plt.title('Acceleration Data')
plt.legend()

# Plotting the gyroscope data
plt.subplot(2, 1, 2)
plt.plot(data['Tio'], data['Gyro X'], label='Gyro X')
plt.plot(data['Tio'], data['Gyro Y'], label='Gyro Y')
plt.plot(data['Tio'], data['Gyro Z'], label='Gyro Z')
plt.xlabel('Time')
plt.ylabel('Gyroscope')
plt.title('Gyroscope Data')
plt.legend()

# Show the plot
plt.tight_layout()
plt.show()
