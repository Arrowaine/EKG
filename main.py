from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import QDir, QModelIndex
from PyQt5.QtWidgets import QFileDialog, QFileSystemModel, QMainWindow, QFileDialog, QMessageBox, QDialog, QApplication
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from ui_file import Ui_MainWindow
import sys
import ekg

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        self.raw_data = None
        self.filtered_data = None
        
        self.ui.File_button.clicked.connect(self.load_file)
        self.ui.Directory_button.clicked.connect(self.load_directory)
        self.ui.treeView.doubleClicked.connect(self.tree_item_double_clicked)


        self.ui.label_4.setText('Сначала загрузите ЭКГ')

        self.ui.File_button.setText("Выбрать файл")
        self.ui.Directory_button.setText("Выбрать папку")
       
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
            
            self.ui.treeView.setColumnWidth(0, 125)  
            self.ui.treeView.setSortingEnabled(True)

            
    def tree_item_double_clicked(self, index: QModelIndex):
        """Обработчик двойного клика по элементу в treeView"""
        if not self.current_directory:
            return
            
        model = self.ui.treeView.model()
    
        file_path = model.filePath(index)
        
        if model.isDir(index):
            return
            
        self.ui.ChooseFile.setText(file_path)
        
        self.plot_data(file_path)

    def plot_data(self, file_path):
        """Чтение и построение графиков."""
        try:
            self.raw_data = ekg.parse_file(file_path)
            self.filtered_data = self.raw_data.copy()
            
            self.setup_empty_plots()
            
            self.setup_plots(file_path)
            

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки файла:\n{str(e)}")
            self.setup_empty_plots()

    def setup_plots(self, filename):
        """Создание и отображение графиков"""
        self.setup_empty_plots()
        try:
            parsed_data = ekg.parse_file(filename)

            fig1 = ekg.upload_ecg(parsed_data)
            fig2 = ekg.upload_eeg(parsed_data)
            fig3 = ekg.upload_pulse(parsed_data)
            
            canvas1 = FigureCanvas(fig1[0])
            canvas2 = FigureCanvas(fig2)
            canvas3 = FigureCanvas(fig3)
            
            self.ui.Cardio.scene().addWidget(canvas1)
            self.ui.Eeg.scene().addWidget(canvas2)
            self.ui.Pulse.scene().addWidget(canvas3)

            self.ui.label_4.setText(fig1[1])
            
            self.ui.Shapka.setText('\n'.join(parsed_data['shapka']))
                
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка построения графиков:\n{str(e)}")
            self.setup_empty_plots()

  
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
   
    sys.exit(app.exec_())