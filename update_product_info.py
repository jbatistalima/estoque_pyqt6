import sys

from PyQt6 import QtWidgets, uic
from PyQt6.QtCore import pyqtSignal
from connect_db import DatabaseConnect
import os


def resource_path(relative_path):
    """ Retorna o caminho absoluto para o recurso, funcionando em desenvolvimento e no PyInstaller """
    try:
        # O PyInstaller cria uma pasta temporária e armazena o caminho em _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

ui_path = resource_path("ui/update_product_info.ui")
Ui_MainWindow, QtWidgetsBaseClass = uic.loadUiType(ui_path)


class UpdateProductWindow(QtWidgets.QDialog):
    # Sinal personalizado para notificar o main.py de que houve movimentação de estoque
    stock_updated_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # CORREGIDO: Carrega a UI diretamente no self
        uic.loadUi(resource_path("ui/update_product_info.ui"), self)
        self.connect_db = DatabaseConnect()

        # CORREGIDO: Mapeamento direto dos componentes injetados pelo uic
        self.search_input = self.lineEdit            
        self.search_btn = self.pushButton            
        self.product_list_widget = self.listWidget    
        self.display_product_name = self.lineEdit_2  
        self.radio_in = self.radioButton             
        self.radio_out = self.radioButton_2           
        self.quantity_spin = self.spinBox            
        self.product_update_button_box = self.pushButton_2  # Botão Cadastrar

        self.init_search_list()

        # Eventos locais
        self.search_input.textChanged.connect(self.init_search_list)
        self.search_btn.clicked.connect(self.init_search_list)
        self.product_list_widget.itemClicked.connect(self.select_product_from_list)
        self.product_update_button_box.clicked.connect(self.update_product_save)

        self.product_update_button_box.setStyleSheet("""
            QPushButton { 
                background-color: #DCDCDC; 
                color: black;
            }
        """)
        self.search_btn.setStyleSheet("""
            QPushButton { 
                background-color: #DCDCDC; 
                color: black;
            }
        """)

        
    def init_search_list(self):
        text = self.search_input.text()
        search_result = self.connect_db.get_product_names(text)
        product_names = [str(item[0]) if isinstance(item, tuple) else str(item) for item in search_result]
        self.product_list_widget.clear()
        self.product_list_widget.addItems(product_names)


    def select_product_from_list(self, item):
        self.display_product_name.setText(item.text())


    def init_product_list(self, product_name):
        """Preenche o nome caso venha da tela de pesquisa."""
        self.display_product_name.setText(product_name)
        

    def update_product_save(self):
        product_name = self.display_product_name.text().strip()
        qty_change = self.quantity_spin.value()

        if not product_name:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione um produto.")
            return
        if qty_change <= 0:
            QtWidgets.QMessageBox.warning(self, "Aviso", "A quantidade de movimentação deve ser maior que zero.")
            return

        # Puxa informações do banco (índice 0 é o estoque atual no seu get_single_product_info)
        product_info = self.connect_db.get_single_product_info(product_name=product_name)
        current_stock = product_info[0] if isinstance(product_info, (list, tuple)) else (product_info or 0)

        # Determina o cálculo baseado no Radio Button ativo
        if self.radio_in.isChecked():
            new_stock = current_stock + qty_change
        else:
            new_stock = current_stock - qty_change
            if new_stock < 0:
                QtWidgets.QMessageBox.warning(self, "Erro", f"Estoque insuficiente! Estoque atual é de apenas {current_stock} unidades.")
                return

        try:
            # CORREGIDO: Reescrevemos a query local usando parâmetros '?' anti SQL Injection
            sql = f"UPDATE {self.connect_db.table_name} SET stock=? WHERE product_name=?"
            valores = (new_stock, product_name)
            
            #print(f"Executando Movimentação Segura: {sql} com {valores}")
            self.connect_db.com_update_execute(sql, params=valores)
            
            QtWidgets.QMessageBox.information(self, "Sucesso", f"Estoque atualizado com sucesso para {new_stock}!")
            self.quantity_spin.setValue(0)
            
            # Avisa o main.py para dar refresh instantâneo nos dados da tela de fundo
            self.stock_updated_signal.emit()
            
            self.accept()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Erro ao salvar alteração no banco de dados:\n{e}")
