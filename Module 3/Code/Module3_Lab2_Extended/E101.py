import numpy as np

true_data = np.array([2, 3, 1, 4, 3])  # Actual visits

true_avg = np.mean(true_data)
print(f"True Average: {true_avg:.2f}")

def dp_average(data, epsilon=1.0, sensitivity=1.0):
    avg = np.mean(data)
    scale = sensitivity / epsilon
    noise = np.random.laplace(loc=0.0, scale=scale)
    return avg + noise

for i in range(3):
    dp_avg = dp_average(true_data, epsilon=0.5)
    print(f"Differentially Private Average (run {i+1}): {dp_avg:.2f}")
