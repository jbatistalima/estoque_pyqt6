import sys
import os
from PyQt6 import QtWidgets, uic
from connect_db import DatabaseConnect


def resource_path(relative_path):
    """ Retorna o caminho absoluto para o recurso, funcionando em desenvolvimento e no PyInstaller """
    try:
        # O PyInstaller cria uma pasta temporária e armazena o caminho em _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class UpdateStockWindow(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        # CORREGIDO: Carrega a UI diretamente na instância (self)
        uic.loadUi(resource_path("ui/update_stock.ui"), self)
        self.connect_db = DatabaseConnect()

        # CORREGIDO: Mapeamento direto sem o prefixo '.ui'
        self.input_product_name = self.lineEdit       
        self.cost_unit = self.doubleSpinBox           
        self.price_unit = self.doubleSpinBox_2         
        self.location_box = self.comboBox             
        self.product_level = self.spinBox             
        self.current_stock = self.spinBox_2           
        self.save_btn = self.pushButton               
        self.cancel_btn = self.pushButton_2           

        self.input_product_name.setEnabled(True) 
        self.init_locations()

        self.save_btn.clicked.connect(self.submit)
        self.cancel_btn.clicked.connect(self.reject)


    def init_locations(self):
        locations_result = self.connect_db.get_all_locations()
        if locations_result:
            locations_list = [str(item[0]) if isinstance(item, tuple) else str(item) for item in locations_result]
            self.location_box.clear()
            self.location_box.addItems(locations_list)


    def load_product_data(self, product_name):
        self.input_product_name.setText(product_name)
        product_info = self.connect_db.get_single_product_info(product_name=product_name)
        
        # ALERTA: Verifique se sua função 'get_single_product_info' realmente traz 5 colunas.
        # Se ela trouxer apenas 3 colunas, mude a verificação abaixo para '>= 3'
        if product_info and len(product_info) >= 5:
            try:
                # Ordem presumida das colunas em inglês: (stock, reorder_level, location, cost, price)
                self.current_stock.setValue(int(product_info[0]))
                self.product_level.setValue(int(product_info[1]))
                self.location_box.setCurrentText(str(product_info[2]))
                self.cost_unit.setValue(float(product_info[3]))
                self.price_unit.setValue(float(product_info[4]))
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Aviso", "Erro ao converter colunas da tabela.")
                #print(f"Erro ao converter colunas da tabela: {e}")
        else:
            QtWidgets.QMessageBox.warning(self, "Aviso", "get_single_product_info retornou menos de 5 colunas. Custo e Preço não foram preenchidos.")
            #print("Aviso: get_single_product_info retornou menos de 5 colunas. Custo e Preço não foram preenchidos.")


    def submit(self):
        product_name = self.input_product_name.text().strip()
        if not product_name: 
            QtWidgets.QMessageBox.warning(self, "Aviso", "O nome do produto não pode estar vazio.")
            return

                # Coleta dos dados dos componentes da tela
        cost = self.cost_unit.value()
        price = self.price_unit.value()
        location = self.location_box.currentText()
        level = self.product_level.value()
        stock = self.current_stock.value()
        product_name = self.input_product_name.text().strip() # Garante o nome para o WHERE

        try:
            # 1. String SQL limpa utilizando os marcadores '?'
            sql = """
                UPDATE product_master 
                SET stock=?, cost=?, price=?, location=?, reorder_level=? 
                WHERE product_name=?
            """            
            
            valores = (stock, cost, price, location, level, product_name)
            
            # DEBUG: Exibe no terminal para acompanhamento seguro
            #print(f"Executando SQL Update Seguro: {sql} com os parâmetros: {valores}")
            
            # 3. Executa passando o SQL e os valores separadamente
            self.connect_db.com_update_execute(sql, params=valores)
            
            QtWidgets.QMessageBox.information(self, "Sucesso", "Dados atualizados com sucesso!")
            self.accept()  # Fecha o QDialog e avisa o main.py para atualizar a tabela
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Erro no banco de dados:\n{e}")

