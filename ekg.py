import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import find_peaks, butter, filtfilt, medfilt, savgol_filter

def parse_file(filename):
    with open(filename, 'r', encoding='ANSI') as file:
        lines = [line.strip() for line in file.readlines() if line.strip() != ""]

    # Извлекаем продолжительность (формат "этап 1, продолжительность 2:00")
    duration_str = None
    for line in lines:
        if "продолжительность" in line.lower():
            duration_str = line.split("продолжительность")[1].strip().split()[0]  # "2:00"
            break
    if not duration_str:
        raise ValueError("Не найдена продолжительность в файле!")
    
    minutes, seconds = map(int, duration_str.split(':'))
    total_duration = minutes * 60 + seconds  # В секундах

    # Ищем начало данных (после шапки)
    data_start = 8
    for i, line in enumerate(lines):
        if line.startswith("EEG"):
            data_start = i + 2
            break

    # Предполагаем, что данные идут после шапки в порядке: ЭЭГ, Пульс, ЭКГ
    # Если в файле есть явные разделители, уточните!
    eeg_data = []
    pulse_data = []
    ecg_data = []
    
    current_section = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Определяем текущую секцию
        if "EEG1_A" in line:
            current_section = "EEG"
        elif "CARDIO_S1" in line:
            current_section = "PULSE"
        elif "CARDIO_RAW" in line:
            current_section = "ECG"
        elif line.replace('.', '').isdigit() or (line.lstrip('-').replace('.', '').isdigit() and '-' in line):
            # Если строка — число (возможно, отрицательное)
            value = float(line)
            if current_section == "EEG":
                eeg_data.append(value)
            elif current_section == "PULSE":
                pulse_data.append(value)
            elif current_section == "ECG":
                ecg_data.append(value)

    # Создаем временные оси
    time_eeg = np.linspace(0, total_duration, len(eeg_data)) if eeg_data else []
    time_pulse = np.linspace(0, total_duration, len(pulse_data)) if pulse_data else []
    time_ecg = np.linspace(0, total_duration, len(ecg_data)) if ecg_data else []

    return {
        "eeg": {"time": time_eeg, "data": eeg_data},
        "pulse": {"time": time_pulse, "data": pulse_data},
        "ecg": {"time": time_ecg, "data": ecg_data},
        "time": total_duration
    }

def filter_ecg(ecg_signal, fs=1000, lowcut=5.0, highcut=15.0):
    """Бандажный фильтр для выделения QRS-комплексов."""
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(4, [low, high], btype='band')
    filtered_ecg = filtfilt(b, a, ecg_signal)
    return filtered_ecg

def detect_qrs_peaks(ecg_signal, fs=1000, min_peak_height=0.5, min_peak_distance=0.3):
    """Поиск R-пиков в ЭКГ."""
    # Фильтрация сигнала
    filtered_ecg = filter_ecg(ecg_signal, fs)
    
    # Нормализация (масштабирование до 0-1)
    normalized_ecg = (filtered_ecg - np.min(filtered_ecg)) / (np.max(filtered_ecg) - np.min(filtered_ecg))
    
    # Поиск пиков (min_peak_distance в секундах)
    min_samples = int(min_peak_distance * fs)
    peaks, _ = find_peaks(normalized_ecg, height=min_peak_height, distance=min_samples)
    
    return peaks, normalized_ecg


def preprocess_ecg(ecg_signal, fs=1000):
    """Предварительная обработка ЭКГ: медианный + полосовой фильтр."""
    # Медианный фильтр для удаления артефактов
    ecg_clean = medfilt(ecg_signal, kernel_size=5)
    
    # Полосовой фильтр (5-15 Гц)
    nyquist = 0.5 * fs
    low = 1 / nyquist
    high = 20 / nyquist
    b, a = butter(4, [low, high], btype='band')
    ecg_filtered = filtfilt(b, a, ecg_clean)
    
    return ecg_filtered

def detect_qrs_peaks(ecg_signal, fs=1000):
    """Детекция QRS-комплексов (упрощённый Пан-Томпкинс)."""
    # 1. Фильтрация
    ecg_filtered = preprocess_ecg(ecg_signal, fs)
    
    # 2. Возведение в квадрат для усиления R-пиков
    ecg_squared = np.square(ecg_filtered)
    
    # 3. Поиск пиков (мин. расстояние = 0.6 сек)
    peaks, _ = find_peaks(ecg_squared, distance=int(0.6*fs), prominence=np.std(ecg_squared))
    
    return peaks

def detect_qrs_complexes(ecg_signal, fs=1000):
    """Улучшенный детектор QRS-комплексов с анализом формы сигнала."""
    # 1. Предварительная фильтрация
    ecg_filtered = preprocess_ecg(ecg_signal, fs)
    
    # 2. Поиск областей с резкими перепадами (производная)
    derivative = np.gradient(ecg_filtered)
    derivative_smoothed = savgol_filter(derivative, window_length=21, polyorder=3)
    
    # 3. Поиск кандидатов в R-зубцы (положительные выбросы производной)
    r_peak_candidates, _ = find_peaks(
        derivative_smoothed, 
        height=np.percentile(derivative_smoothed, 95),  # Берём верхние 10% значений
        distance=int(0.2*fs)  # Минимум 400 мс между зубцами
    )
    
    # 4. Уточнение положения R-зубцов (максимум в исходном сигнале)
    r_peaks = []
    search_radius = int(0.3*fs)  # ±100 мс вокруг кандидата
    
    for candidate in r_peak_candidates:
        start = max(0, candidate - search_radius)
        end = min(len(ecg_filtered)-1, candidate + search_radius)
        local_max = start + np.argmax(ecg_filtered[start:end])
        r_peaks.append(local_max)
    
    return np.array(r_peaks)

def upload_eeg(data):
    fig, ax = plt.subplots()
    ax.plot(data["eeg"]["time"], data["eeg"]["data"], color='blue', label='EEG')
    ax.set_title("EEG Signal")
    ax.set_ylabel("Amplitude")
    return fig

def upload_ecg(data):
    fig, ax = plt.subplots()
    ax.plot(data["ecg"]["time"], data["ecg"]["data"], color='green', label='EEG')
    ax.set_title("ECG Signal")
    ax.set_ylabel("Amplitude")
    ecg_signal = np.array(data["ecg"]["data"])
    ecg_peaks = detect_qrs_complexes(ecg_signal, len(np.array(data["ecg"]["data"]))/data['time'])
    text = f"QRS-пиков: {len(ecg_peaks)}"
        #print(f"Средняя ЧСС: {len(ecg_peaks) / (data["ecg"]["time"][-1] / 60):.1f} уд/мин")
    ax.scatter(
                        data["ecg"]["time"][ecg_peaks],
                        ecg_signal[ecg_peaks],
                        color='red', marker='o', label='R-peaks'
                    )
                    
    # Пример определения Q и S для одного комплекса
    if len(ecg_peaks) > 2:
        r_pos = ecg_peaks[1]
        q_pos = r_pos - np.argmin(ecg_signal[max(0,r_pos-50):r_pos][::-1])  # Ищем минимум перед R
        s_pos = r_pos + np.argmin(ecg_signal[r_pos:min(len(ecg_signal),r_pos+50)])  # Ищем минимум после R
        
        ax.scatter(data["ecg"]["time"][q_pos], ecg_signal[q_pos], color='blue', marker='<', label='Q-point')
        ax.scatter(data["ecg"]["time"][s_pos], ecg_signal[s_pos], color='green', marker='>', label='S-point')

    return fig,text

def upload_pulse(data):
    fig, ax = plt.subplots()
    ax.plot(data["pulse"]["time"], data["pulse"]["data"], color='green', label='EEG')
    ax.set_title("Pulse")
    ax.set_ylabel("BPM")
    
    return fig

'''

try:
    data = parse_file("2.1.txt")
except Exception as e:
    print(f"Ошибка при чтении файла: {e}")
    exit()


# Построение графиков
if data["eeg"]["data"]:
    plt.figure(figsize=(12, 8))
    
    # График ЭЭГ
    plt.subplot(4, 1, 1)
    plt.plot(data["eeg"]["time"], data["eeg"]["data"], color='blue', label='EEG')
    plt.title("EEG Signal")
    plt.ylabel("Amplitude")
    plt.legend()

    # График Пульса (если есть данные)
    if data["pulse"]["data"]:
        
        plt.subplot(3, 1, 2)
        plt.plot(data["pulse"]["time"], data["pulse"]["data"], color='red', label='Pulse')
        plt.title("Pulse Signal")
        plt.ylabel("BPM")
        plt.legend()

    # График ЭКГ
    if data["ecg"]["data"]:
        plt.subplot(3, 1, 3)
        plt.plot(data["ecg"]["time"], data["ecg"]["data"], color='green', label='ECG')
        plt.title("ECG Signal")
        plt.xlabel("Time (s)")
        plt.ylabel("Amplitude")
        plt.legend()
        ecg_signal = np.array(data["ecg"]["data"])
        ecg_peaks = detect_qrs_complexes(ecg_signal, len(np.array(data["ecg"]["data"]))/data['time'])
        print(f"Найдено QRS-комплексов: {len(ecg_peaks)}")
        #print(f"Средняя ЧСС: {len(ecg_peaks) / (data["ecg"]["time"][-1] / 60):.1f} уд/мин")
        plt.scatter(
                        data["ecg"]["time"][ecg_peaks],
                        ecg_signal[ecg_peaks],
                        color='red', marker='o', label='R-peaks'
                    )
                    
    # Пример определения Q и S для одного комплекса
    if len(ecg_peaks) > 2:
        r_pos = ecg_peaks[1]
        q_pos = r_pos - np.argmin(ecg_signal[max(0,r_pos-50):r_pos][::-1])  # Ищем минимум перед R
        s_pos = r_pos + np.argmin(ecg_signal[r_pos:min(len(ecg_signal),r_pos+50)])  # Ищем минимум после R
        
        plt.scatter(data["ecg"]["time"][q_pos], ecg_signal[q_pos], color='blue', marker='<', label='Q-point')
        plt.scatter(data["ecg"]["time"][s_pos], ecg_signal[s_pos], color='green', marker='>', label='S-point')

    plt.tight_layout()
    plt.show()
else:
    print("Данные для построения графиков не найдены.")

'''