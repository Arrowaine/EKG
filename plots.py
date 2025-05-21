import matplotlib.pyplot as plt
import numpy as np

def plot_sin():
    """График синуса"""
    fig, ax = plt.subplots()
    x = np.linspace(0, 2 * np.pi, 100)
    ax.plot(x, np.sin(x), label="sin(x)")
    ax.set_title("Синус")
    ax.legend()
    return fig

def plot_cos():
    """График косинуса"""
    fig, ax = plt.subplots()
    x = np.linspace(0, 2 * np.pi, 100)
    ax.plot(x, np.cos(x), label="cos(x)", color="red")
    ax.set_title("Косинус")
    ax.legend()
    return fig

def plot_random():
    """Случайные данные"""
    fig, ax = plt.subplots()
    data = np.random.randn(1000)
    ax.hist(data, bins=30, alpha=0.7, color="green")
    ax.set_title("Гистограмма случайных данных")
    return fig