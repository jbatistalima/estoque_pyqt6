import sys
import os
from PyQt6 import QtWidgets, uic, QtCore # Adicionado QtCore para os Sinais
from connect_db import DatabaseConnect

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

ui_path = resource_path("ui/search.ui")
Ui_MainWindow, QtWidgetsBaseClass = uic.loadUiType(ui_path)

class SearchWindow(QtWidgets.QDialog):
    # CRIA O SINAL PERSONALIZADO: Ele vai enviar uma string ("ALL", "IN_STOCK", etc) para o main.py
    filter_changed = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()
        uic.loadUi(resource_path("ui/search.ui"), self)
        self.connect_db = DatabaseConnect()

        # Componentes do XML
        self.product_name_LW = self.listWidget
        self.input_product_name_LE = self.lineEdit
        self.current_stock_label = self.label_2
        self.reorder_label = self.label_4
        self.location_number_label = self.label_6
        # Estilização básica opcional para os botões ficarem elegantes (pode ajustar como quiser)
        
        # Botões
        # self.all_product_btn = self.pushButton
        # self.current_stock_btn = self.pushButton_2
        # self.reorder_btn = self.pushButton_3
        # self.no_stock_btn = self.pushButton_4
        self.detaill_btn = self.pushButton_5  # Atualizar Estoque
        
        self.init_search_dialog()

        # Conexões de Eventos dos Inputs
        self.input_product_name_LE.textChanged.connect(self.update_product_name_list)
        self.product_name_LW.currentTextChanged.connect(self.search_product_info)

        # --- CONECTA OS CLIQUES DOS BOTÕES PARA EMITIR O SINAL REPASSA-FILTRO ---
        # self.all_product_btn.clicked.connect(lambda: self.emit_filter("ALL"))
        # self.current_stock_btn.clicked.connect(lambda: self.emit_filter("IN_STOCK"))
        # self.no_stock_btn.clicked.connect(lambda: self.emit_filter("NO_STOCK"))
        # self.reorder_btn.clicked.connect(lambda: self.emit_filter("RE_ORDER"))
        
        # Estilização básica opcional para os botões ficarem elegantes (pode ajustar como quiser)          
        self.detaill_btn.setStyleSheet("""
            QPushButton { 
                background-color: #DCDCDC; 
                color: black;
            }
        """)
           

    def emit_filter(self, filter_type):
        """Dispara o sinal avisando a tela principal qual filtro carregar."""
        self.filter_changed.emit(filter_type)

    def init_search_dialog(self):
        search_result = self.connect_db.get_product_names("")
        product_name_list = [str(item[0]) if isinstance(item, tuple) else str(item) for item in search_result]
        self.product_name_LW.clear()
        self.product_name_LW.addItems(product_name_list)

        self.current_stock_label.setText("-")
        self.reorder_label.setText("-")
        self.location_number_label.setText("-")
        self.input_product_name_LE.clear()
    
    def get_more_detaill(self):
        product_name_obj = self.product_name_LW.currentItem() 
        if product_name_obj:
            return product_name_obj.text()
        else:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione o produto na lista primeiro.")
            return None 
          

    def search_product_info(self, product_name):
        if product_name:
            search_result = self.connect_db.get_single_product_info(product_name=product_name)
            if search_result and len(search_result) >= 3:
                self.current_stock_label.setText(str(search_result[0]))
                self.reorder_label.setText("Não" if search_result[0] > search_result[1] else "Sim")
                self.location_number_label.setText(str(search_result[2]))
        else:
            self.current_stock_label.setText("-")
            self.reorder_label.setText("-")
            self.location_number_label.setText("-")
            

    def update_product_name_list(self, text):
       
        self.product_name_LW.clear()

  
        search_result = self.connect_db.get_product_names(text)
        product_name_list = [item[0] for item in search_result]
        self.product_name_LW.addItems(product_name_list)
