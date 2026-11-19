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

ui_path = resource_path("ui/new_product.ui")
Ui_MainWindow, QtWidgetsBaseClass = uic.loadUiType(ui_path)

class NewProductWindow(QtWidgets.QWidget):
    # Sinal personalizado correto
    product_saved_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # CORREÇÃO: Carrega a UI diretamente no 'self' (sem criar self.ui)
        uic.loadUi(resource_path("ui/new_product.ui"), self)

        # CORREÇÃO: Mapeamento direto dos componentes injetados pelo uic
        self.new_product_save_btn = self.pushButton_2
        self.new_product_cancel_btn = self.pushButton
        
        self.product_name = self.lineEdit
        self.cost = self.doubleSpinBox
        self.price = self.doubleSpinBox_2
        self.location = self.comboBox
        self.reorder_level = self.spinBox
        self.stock = self.spinBox_2
        
        # Configurações iniciais
        self.location.setEnabled(True) 
        self.new_product_save_btn.clicked.connect(self.add_new_product_and_close)
        self.new_product_cancel_btn.clicked.connect(self.close)
        
        self.connect_db = DatabaseConnect()

    def add_new_product_and_close(self):
        """Executa a gravação e fecha a janela em caso de sucesso."""
        result_error = self.add_new_product()
        
        if result_error is None:
            QtWidgets.QMessageBox.information(self, "Sucesso", "Novo produto cadastrado com sucesso!")
            self.product_saved_signal.emit()  # Emite o sinal para o main.py atualizar a tabela
            self.clear_data()
            self.close()      
        else:
            QtWidgets.QMessageBox.critical(self, "Erro", result_error)

    def new_product_data(self):
        """Coleta e valida os dados da interface de forma segura."""
        product_name = self.product_name.text().strip()
        cost = self.cost.value()
        price = self.price.value()
        
        location = self.location.currentText().strip()
        if location.startswith("(") and location.endswith(")"):
            location = location.replace("(", "").replace(")", "").replace("'", "").replace(",", "").strip()

        reorder_level = self.reorder_level.value()
        stock = self.stock.value()

        # Validação visual imediata
        if not product_name:
            return "Por favor, insira o nome do produto."
        if not location:
            return "Por favor, selecione ou insira um local."

        return {
            "product_name": product_name,
            "cost": cost,
            "price": price,
            "location": location,
            "reorder_level": reorder_level,
            "stock": stock,
        }

    def add_new_product(self):
        """Executa a query INSERT no banco de dados."""
        product_data = self.new_product_data()
        
        # Se retornar uma string, significa que falhou na validação de campos
        if isinstance(product_data, str):
            return product_data

        try:
            # 1. O comando SQL agora usa '?' no lugar dos valores. 
            # Note que não usamos mais aspas simples ('?') para textos! O SQLite resolve isso.
            sql = f"""
                INSERT INTO {self.connect_db.table_name} 
                (product_name, cost, price, location, reorder_level, stock)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            
            # 2. Criamos uma tupla com os valores exatamente na mesma ordem dos campos acima
            valores = (
                product_data["product_name"],
                product_data["cost"],
                product_data["price"],
                product_data["location"],
                product_data["reorder_level"],
                product_data["stock"]
            )
            
            # DEBUG: Mostra a estrutura segura no terminal
            #print(f"Executando SQL Seguro: {sql} com os parâmetros: {valores}")
            
            # 3. Passamos a query E os valores separadamente para o banco
            self.connect_db.com_update_execute(sql, params=valores)
            return None
        except Exception as e:
            print(f"Erro Crítico na Inserção SQL: {e}")
            return f"Erro ao gravar no banco de dados:\n{e}"


    def clear_data(self):
        """Limpa os campos para a próxima inserção."""
        self.product_name.clear()
        self.cost.setValue(0.0)
        self.price.setValue(0.0)
        if self.location.count() > 0:
            self.location.setCurrentIndex(0)
        self.reorder_level.setValue(0)
        self.stock.setValue(0)


