import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import find_peaks, butter, filtfilt, medfilt, savgol_filter

def parse_file(filename):
    with open(filename, 'r', encoding='ANSI') as file:
        lines = [line.strip() for line in file.readlines() if line.strip() != ""]

    duration_str = None
    for line in lines:
        if "продолжительность" in line.lower():
            duration_str = line.split("продолжительность")[1].strip().split()[0] 
            break
    if not duration_str:
        raise ValueError("Не найдена продолжительность в файле!")
    
    minutes, seconds = map(int, duration_str.split(':'))
    total_duration = minutes * 60 + seconds 

    data_start = 0
    shapka = []

    for i, line in enumerate(lines):
        if "\t" in line:
            shapka.extend(line.split("\t"))
        else:
            shapka.append(line)
        
        if line.startswith("EEG"):
            data_start = i + 2
            break

    shapka.pop(-1)
    temp_line = shapka[1].split(';')
    shapka.insert(1,temp_line[0])
    shapka.insert(2,temp_line[1][1:])  
    shapka[3] = ''
    shapka.insert(8,'')
    shapka.insert(14,'')
    shapka.insert(-1,'')

    #print(shapka)
    eeg_data = []
    pulse_data = []
    ecg_data = [] 
    

    current_section = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if "EEG1_A" in line:
            current_section = "EEG"
        elif "CARDIO_S1" in line:
            current_section = "PULSE"
        elif "CARDIO_RAW" in line:
            current_section = "ECG"
        elif line.replace('.', '').isdigit() or (line.lstrip('-').replace('.', '').isdigit() and '-' in line): 
            value = float(line)
            if current_section == "EEG":
                eeg_data.append(value)
            elif current_section == "PULSE":
                pulse_data.append(value)
            elif current_section == "ECG":
                ecg_data.append(value)

    time_eeg = np.linspace(0, total_duration, len(eeg_data)) if eeg_data else []
    time_pulse = np.linspace(0, total_duration, len(pulse_data)) if pulse_data else []
    time_ecg = np.linspace(0, total_duration, len(ecg_data)) if ecg_data else []

    return {
        "eeg": {"time": time_eeg, "data": eeg_data},
        "pulse": {"time": time_pulse, "data": pulse_data},
        "ecg": {"time": time_ecg, "data": ecg_data},
        "time": total_duration,
        'shapka': shapka
    }

def filter_ecg(ecg_signal, fs=1000, lowcut=5.0, highcut=15.0):
    """Бандажный фильтр для выделения QRS-комплексов."""
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(4, [low, high], btype='band')
    filtered_ecg = filtfilt(b, a, ecg_signal)
    return filtered_ecg


def preprocess_ecg(ecg_signal, fs=1000):
    """Предварительная обработка ЭКГ: медианный + полосовой фильтр."""
    ecg_clean = medfilt(ecg_signal, kernel_size=5)
    
    nyquist = 0.5 * fs
    low = 1 / nyquist
    high = 20 / nyquist
    b, a = butter(4, [low, high], btype='band')
    ecg_filtered = filtfilt(b, a, ecg_clean)
    
    return ecg_filtered

def detect_qrs_peaks(ecg_signal, fs=1000):
    """Детекция QRS-комплексов (упрощённый Пан-Томпкинс)."""
    ecg_filtered = preprocess_ecg(ecg_signal, fs)
    
    ecg_squared = np.square(ecg_filtered)
    
    peaks, _ = find_peaks(ecg_squared, distance=int(0.6*fs), prominence=np.std(ecg_squared))
    
    return peaks

def detect_qrs_complexes(ecg_signal, fs=1000):
    """Улучшенный детектор QRS-комплексов с анализом формы сигнала."""
    ecg_filtered = preprocess_ecg(ecg_signal, fs)
    
    derivative = np.gradient(ecg_filtered)
    derivative_smoothed = savgol_filter(derivative, window_length=21, polyorder=3)
    
    r_peak_candidates, _ = find_peaks(
        derivative_smoothed, 
        height=np.percentile(derivative_smoothed, 95), 
        distance=int(0.2*fs)  
    )
    
    r_peaks = []
    search_radius = int(0.3*fs) 
    
    for candidate in r_peak_candidates:
        start = max(0, candidate - search_radius)
        end = min(len(ecg_filtered)-1, candidate + search_radius)
        local_max = start + np.argmax(ecg_filtered[start:end])
        r_peaks.append(local_max)
    
    return np.array(r_peaks)

def upload_ecg(data):
    plt.close()
    fig, ax = plt.subplots(figsize=(9.69, 4.60))  # (10.115, 4.802) - window size
    ax.set_ylabel("Amplitude")

    ax.plot(data["ecg"]["time"], data["ecg"]["data"], color='green', )  #label='EEG'
    #ax.set_title("ECG Signal")
    
    ecg_signal = np.array(data["ecg"]["data"])
    ecg_peaks = detect_qrs_complexes(ecg_signal, len(np.array(data["ecg"]["data"]))/data['time'])
    text = f"QRS-пиков: {len(ecg_peaks)}"
        
    ax.scatter(
                        data["ecg"]["time"][ecg_peaks],
                        ecg_signal[ecg_peaks],
                        color='red', marker='o', label='R-peaks'
                    )
    ax.grid()                

    if len(ecg_peaks) > 2:
        r_pos = ecg_peaks[1]
        q_pos = r_pos - np.argmin(ecg_signal[max(0,r_pos-50):r_pos][::-1])  
        s_pos = r_pos + np.argmin(ecg_signal[r_pos:min(len(ecg_signal),r_pos+50)]) 
        
        ax.scatter(data["ecg"]["time"][q_pos], ecg_signal[q_pos], color='blue', marker='<', label='Q-point')
        ax.scatter(data["ecg"]["time"][s_pos], ecg_signal[s_pos], color='green', marker='>', label='S-point')

    return fig,text
   
def upload_eeg(data):
    plt.close()
    fig, ax = plt.subplots(figsize=(4.69, 4.10)) # (4.906, 4.281) - window size
    
    ax.plot(data["eeg"]["time"], data["eeg"]["data"], color='blue', )  #label='EEG'
    #ax.set_title("EEG Signal")
    ax.set_ylabel("Amplitude")
    ax.grid()

    return fig

def upload_pulse(data):
    plt.close()
    fig, ax = plt.subplots(figsize=(4.69, 4.10)) # (4.906, 4.281) - window size
    ax.plot(data["pulse"]["time"], data["pulse"]["data"], color='green', )#label='EEG'
    #ax.set_title("Pulse")
    ax.set_ylabel("BPM")
    ax.grid()

    return fig
