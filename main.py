from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import QDir, QModelIndex
from PyQt5.QtWidgets import QFileDialog, QFileSystemModel, QApplication, QMainWindow, QFileDialog, QMessageBox, QDialog
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from ui_file import Ui_MainWindow
import os, sys
import ekg, plots

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # Инициализация переменных для данных
        self.raw_data = None
        self.filtered_data = None
        
        # Подключаем кнопки
        self.ui.File_button.clicked.connect(self.load_file)
        self.ui.Directory_button.clicked.connect(self.load_directory)
        self.ui.treeView.doubleClicked.connect(self.tree_item_double_clicked)
        # Настройка интерфейса
        self.ui.File_button.setText("Выбрать файл")
        self.ui.Directory_button.setText("Выбрать папку")
        self.ui.label_4.setText("Статус: готов к работе")
        
        # Очищаем графики при старте
        self.setup_empty_plots()

    def setup_empty_plots(self):
        """Очищает все графики."""
        self.cardio_view = self.ui.Cardio
        self.eeg_view = self.ui.Eeg
        self.pulse_view = self.ui.Pulse

        for view in [self.cardio_view, self.eeg_view, self.pulse_view]:
            scene = QtWidgets.QGraphicsScene()
            view.setScene(scene)

    def load_file(self):
        """Загрузка одиночного файла и построение графиков"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Выберите файл данных", 
            QDir.homePath(),
            "Данные (*.csv *.dat *.txt);;Все файлы (*)"
        )
        
        if file_path:
            self.ui.ChooseFile.setText(file_path)
            self.plot_data(file_path)

    def load_directory(self):
        """Загрузка директории"""
        dir_path = QFileDialog.getExistingDirectory(
            self, 
            "Выберите папку с данными",
            QDir.homePath()
        )
        
        if dir_path:
            self.current_directory = dir_path
            self.ui.ChooseDirectory.setText(dir_path)
            self.ui.label_4.setText(f"Загружена папка: {dir_path}")
            
            # Загрузка списка файлов в treeView
            model = QFileSystemModel()
            model.setRootPath(dir_path)
            self.ui.treeView.setModel(model)
            self.ui.treeView.setRootIndex(model.index(dir_path))
            
            # Настройка отображения (опционально)
            self.ui.treeView.setColumnWidth(0, 250)  # Ширина столбца с именем
            self.ui.treeView.setSortingEnabled(True)

            
    def tree_item_double_clicked(self, index: QModelIndex):
        """Обработчик двойного клика по элементу в treeView"""
        if not self.current_directory:
            return
            
        # Получаем модель из treeView
        model = self.ui.treeView.model()
        
        # Получаем полный путь к выбранному файлу
        file_path = model.filePath(index)
        
        # Проверяем, что это файл (а не папка)
        if model.isDir(index):
            return
            
        # Обновляем поле с выбранным файлом
        self.ui.ChooseFile.setText(file_path)
        
        # Строим графики для выбранного файла
        self.plot_data(file_path)

    def plot_data(self, file_path):
        """Чтение и построение графиков."""
        try:
            self.raw_data = ekg.parse_file(file_path)
            self.filtered_data = self.raw_data.copy()
            
            # Очистка графиков перед построением новых
            self.setup_empty_plots()
            
            # Построение графиков
            self.setup_plots(file_path)
            
            
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки файла:\n{str(e)}")
            self.setup_empty_plots()

    def setup_plots(self, filename):
        """Создание и отображение графиков"""
        try:
            # Получаем Figure объекты из вашего модуля ekg
            fig1 = ekg.upload_ecg(ekg.parse_file(filename))
            fig2 = ekg.upload_eeg(ekg.parse_file(filename))
            fig3 = ekg.upload_pulse(ekg.parse_file(filename))
            
            # Создаем canvas для каждого графика
            canvas1 = FigureCanvas(fig1[0] if isinstance(fig1, tuple) else fig1)
            canvas2 = FigureCanvas(fig2)
            canvas3 = FigureCanvas(fig3)
            
            # Добавляем canvas на соответствующие QGraphicsView
            self.ui.Cardio.scene().addWidget(canvas1)
            self.ui.Eeg.scene().addWidget(canvas2)
            self.ui.Pulse.scene().addWidget(canvas3)
            
            # Если есть дополнительная текстовая информация (как в случае с ECG)
            if isinstance(fig1, tuple) and len(fig1) > 1:
                self.ui.label_4.setText(fig1[1])
                
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка построения графиков:\n{str(e)}")
            self.setup_empty_plots()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
   
    sys.exit(app.exec_())