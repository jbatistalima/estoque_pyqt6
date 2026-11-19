import sys
import os
import sqlite3
import locale
import qdarktheme
import ctypes  
from PyQt6 import QtWidgets, uic, QtGui
from connect_db import DatabaseConnect
from new_product import NewProductWindow
from update_product_info import UpdateProductWindow
from update_stock import UpdateStockWindow
from search import SearchWindow
from admin_config import AdminConfigWindow
from login import LoginWindow


locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")


#Ui_MainWindow, QtWidgetsBaseClass = uic.loadUiType("./ui/main.ui")

# --- ADICIONE ESTE BLOCO LOGO AQUI NO TOPO ---
try:
    # Cria uma assinatura única para o Windows reconhecer o ícone na barra de tarefas
    myappid = 'meu_sistema.gerenciamento.estoque.1.0' 
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass



def resource_path(relative_path):
    """ Retorna o caminho absoluto para o recurso, funcionando em desenvolvimento e no PyInstaller """
    try:
        # O PyInstaller cria uma pasta temporária e armazena o caminho em _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# SUBSTITUA A SUA LINHA ANTIGA POR ESTA:
ui_path = resource_path("ui/main.ui")
Ui_MainWindow, QtWidgetsBaseClass = uic.loadUiType(ui_path)


class StockManagement(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, is_admin=False):
        super().__init__()
        self.setupUi(self)
        self.is_admin = is_admin
        self.reabrir_login = False

        # Instâncias Limpas
        self.new_product_dialog = NewProductWindow()
        self.update_product_dialog = UpdateProductWindow() # Entrada/Saída
        self.update_stock_dialog = UpdateStockWindow()     # Cadastro Completo
        self.search_dialog = SearchWindow()
        self.connect_db = DatabaseConnect()

        if hasattr(self, 'actionAdmin'):
            self.actionAdmin.setVisible(self.is_admin)
            self.actionAdmin.triggered.connect(self.abrir_painel_admin)

        # Sinais da Barra de Ferramentas / Menu (Ajuste para português se necessário)
        self.actionNovo_Produto.triggered.connect(self.open_new_product_dialog)
        self.actionAtualizar_Estoque.triggered.connect(self.open_update_stock_dialog)
        self.actionPesquisar.triggered.connect(self.open_search_dialog)

        # Filtros
        self.actionTodos_Produtos.triggered.connect(lambda: self.apply_search_filter("ALL"))
        self.actionReordenar.triggered.connect(lambda: self.apply_search_filter("RE_ORDER"))
        self.actionEstoque_atual.triggered.connect(lambda: self.apply_search_filter("IN_STOCK"))
        self.actionFora_de_estoque.triggered.connect(lambda: self.apply_search_filter("NO_STOCK"))
        
        self.actionSair.triggered.connect(self.fazer_logoff)

        # Sinais vindos da tela de Busca (search.py)
        self.search_dialog.detaill_btn.clicked.connect(self.search_more_detail)
        
        # --- ESSA É A LINHA QUE CONECTA OS FILTROS DA JANELA DE BUSCA ---
        self.search_dialog.filter_changed.connect(self.apply_search_filter)
        
        # Inicialização Padrão da Tabela da Tela Principal (Mostra todos os produtos ao abrir)
        self.apply_search_filter("ALL")

        # Atualizações Globais
        self.update_dashboard()

        # Configuração do ícone da aplicação (funciona no Windows e Linux)
        self.setWindowIcon(QtGui.QIcon(resource_path("icone.ico")))


    def abrir_painel_admin(self):
        if self.is_admin:
            dialog = AdminConfigWindow()
            dialog.exec()


    def fazer_logoff(self):
        msg = QtWidgets.QMessageBox(self)
        msg.setIcon(QtWidgets.QMessageBox.Icon.Question)
        msg.setWindowTitle("Sair / Trocar Usuário")
        msg.setText("Deseja voltar para a tela de login?")

        # Cria os botões personalizados em português
        btn_sim = msg.addButton("Sim", QtWidgets.QMessageBox.ButtonRole.YesRole)
        btn_nao = msg.addButton("Não", QtWidgets.QMessageBox.ButtonRole.NoRole)
        msg.setDefaultButton(btn_sim)

        msg.exec()

        if msg.clickedButton() == btn_sim:
            self.search_dialog.close()
            self.reabrir_login = True
            self.close()
        else:
            self.reabrir_login = False


    def open_new_product_dialog(self):
        try:
            self.new_product_dialog.product_saved_signal.disconnect()
        except TypeError:
            pass
        finally:
            pass
        self.new_product_dialog.product_saved_signal.connect(self.refresh_all)    
        self.new_product_dialog.show()

    def open_update_stock_dialog(self):        
        """Abre a tela de cadastro completo (UpdateStockWindow) baseado na linha selecionada."""
        selected_row = self.tableWidget.currentRow()
        if selected_row != -1:
            product_name = self.tableWidget.item(selected_row, 0).text()
            self.update_stock_dialog.load_product_data(product_name)
            
            # Conecta o sinal apenas uma vez (se possível, mova para o __init__)
            try:
                self.update_stock_dialog.accepted.disconnect()
            except TypeError:
                pass
            self.update_stock_dialog.accepted.connect(self.refresh_all)
            
            # Se for QDialog, use .exec() para travar a tela de trás com segurança
            self.update_stock_dialog.exec() 
        else:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione um produto na tabela da tela principal primeiro.")
    

    def open_search_dialog(self):
        """Abre a janela de pesquisa sem bloquear a tela principal."""
        self.search_dialog.init_search_dialog()
        
        # .show() abre a janela livremente (Não-Modal)
        self.search_dialog.show() 
        self.search_dialog.raise_()  # Garante que ela vai para a frente de todas as telas
        self.search_dialog.activateWindow() # Dá o foco do teclado para ela 

    
    def search_more_detail(self):
        """Ação do botão 'SALVAR DETALHES' da busca: Abre a tela de Entrada/Saída."""
        # Pega o nome do produto selecionado na lista da janela de pesquisa
        product_name = self.search_dialog.get_more_detaill()
        
        if product_name:
            # Exibe a janela de Entrada e Saída (UpdateProductWindow)
            self.update_product_dialog.show()
            self.update_product_dialog.init_product_list(product_name)
            
            # Garante que ao clicar em CADASTRAR dentro dela, a tela principal atualize os dados
            try:
                self.update_product_dialog.accepted.connect(self.refresh_all)
            except Exception:
                pass
            
            self.update_product_dialog.raise_()



    def refresh_all(self):
        self.update_dashboard()
        self.apply_search_filter("ALL") # Reseta a tabela para exibir tudo após atualizar dados
        #self.search_all_product()

    
    def show_data(self, data, title="Gerenciamento de Estoque"):
        table = self.tableWidget
        table.setRowCount(0)

        if data:
            table.setRowCount(len(data))
            for row, product in enumerate(data):
                # 1. Cria os dois botões diretamente como QPushButton
                btn_edit = QtWidgets.QPushButton("Editar", self)
                btn_delete = QtWidgets.QPushButton("Deletar", self)

                # 2. Conecta as funções de clique usando a linha (row) atual
                btn_edit.clicked.connect(lambda checked, r=row: self.action_edit_triggered(r))
                btn_delete.clicked.connect(lambda checked, r=row: self.action_delete_triggered(r))

                # Estilização básica opcional para os botões ficarem elegantes (pode ajustar como quiser)
                btn_edit.setStyleSheet("""
                    QPushButton:hover { 
                        background-color: #999888; 
                        color: black;
                    }
                """)

                btn_delete.setStyleSheet("""
                    QPushButton:hover { 
                        background-color: #ff0000; 
                        color: black;
                    }
                """)

                # 3. Cria um widget container para segurar ambos os botões lado a lado
                container_widget = QtWidgets.QWidget()
                layout = QtWidgets.QHBoxLayout(container_widget)
                
                # Adiciona os botões no layout horizontal
                layout.addWidget(btn_edit)
                layout.addWidget(btn_delete)
                
                # Ajusta as margens e o espaçamento para caber perfeitamente na célula
                layout.setContentsMargins(5, 2, 5, 2)
                layout.setSpacing(5)
                container_widget.setLayout(layout)
                
                
                # --- MAPEAMENTO CORRIGIDO BASEADO NO SEU SELECT REAL ---
                nome_produto = str(product[0])                        # [0] product_name
                custo_unitario = float(product[1] if product[1] else 0) # [1] cost
                preco_venda = float(product[2] if product[2] else 0)    # [2] price
                estoque_atual = int(product[3] if product[3] else 0)    # [3] stock (CORRIGIDO!)
                localizacao = str(product[4])                         # [4] location (CORRIGIDO!)
                pedido_nivel = int(product[5] if product[5] else 0)     # [5] reorder_level (CORRIGIDO!)

                # Cálculos de exibição para a tabela
                valor_estoque = estoque_atual * preco_venda
                custo_estoque = estoque_atual * custo_unitario
                
                # Lógica do "Pedido Requerido" (Se o estoque for menor ou igual ao nível, precisa pedir)
                pedido_requerido = "Sim" if estoque_atual <= pedido_nivel else "Não"
             
                # Inserindo os dados nas colunas certas do seu QTableWidget
                table.setItem(row, 0, QtWidgets.QTableWidgetItem(nome_produto))
                table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(estoque_atual)))
                valor_formatado = locale.currency(valor_estoque, grouping=True)
                table.setItem(row, 2, QtWidgets.QTableWidgetItem(valor_formatado))
                custo_formatado = locale.currency(custo_estoque, grouping=True)
                table.setItem(row, 3, QtWidgets.QTableWidgetItem(custo_formatado))
                table.setItem(row, 4, QtWidgets.QTableWidgetItem(str(pedido_nivel)))
                table.setItem(row, 5, QtWidgets.QTableWidgetItem(pedido_requerido))
                table.setItem(row, 6, QtWidgets.QTableWidgetItem(localizacao))
                
                # Cola o botão de opções na última coluna (Coluna 7)
                table.setCellWidget(row, 7, container_widget)
                #table.setCellWidget(row, 7, option_btn)
                table.setRowCount(len(data))


    def action_delete_triggered(self, row):
        """Executa a exclusão do produto selecionado após confirmação na tela."""
        product_name = self.tableWidget.item(row, 0).text()
        choice = QtWidgets.QMessageBox.warning(
            self, "Deletar !!!", f"Tem certeza que deseja deletar o produto '{product_name}'?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.Cancel
        )
        if choice == QtWidgets.QMessageBox.StandardButton.Yes:
            self.connect_db.delete_product(product_name=product_name)
            self.refresh_all()



    def action_edit_triggered(self, row):
        product_name = self.tableWidget.item(row, 0).text()
        self.update_stock_dialog.show()
        self.update_stock_dialog.load_product_data(product_name)
        self.update_stock_dialog.accepted.connect(self.refresh_all)

    def update_dashboard(self):
        # Proteção robusta contra None vindo do SQL SUM()
        c_stock = self.connect_db.get_current_stock()
        self.label_3.setText(f"Unidades: {c_stock[0] if c_stock and c_stock[0] else 0}")
        
        s_val = self.connect_db.get_stock_value()
        valor_bruto = s_val[0] if (s_val and isinstance(s_val, tuple)) else s_val
        valor_numerico = float(valor_bruto) if valor_bruto is not None else 0.0
        e_formatado = locale.currency(valor_numerico, grouping=True)
        self.label_5.setText(e_formatado)

        s_cost = self.connect_db.get_stock_cost()
        valor_bruto = s_cost[0] if (s_cost and isinstance(s_cost, tuple)) else s_cost
        valor_numerico = float(valor_bruto) if valor_bruto is not None else 0.0
        c_formatado = locale.currency(valor_numerico, grouping=True)
        self.label_7.setText(c_formatado)
                
        # Busca a contagem de produtos fora de estoque        
        no_stock_result = self.connect_db.get_no_stock_product()  

        reorder = self.connect_db.get_reorder_product()
        self.label_9.setText(f"Requeridos: {str(reorder[0] if reorder and reorder[0] else 0)}")

        # DEBUG: Veja no terminal o que o banco está retornando de verdade
        #print(f"DEBUG DASHBOARD: Retorno de get_no_stock_product = {no_stock_result}")

        # Tratamento correto caso o SQLite retorne uma tupla, ex: (0,)
        if isinstance(no_stock_result, tuple) and len(no_stock_result) > 0:
            qtd_fora_estoque = no_stock_result[0]
        else:
            qtd_fora_estoque = no_stock_result if no_stock_result else 0

        # Atualiza a interface de forma explícita
        self.label_11.setText(f"Produtos: {int(qtd_fora_estoque)}")
        
        # Força o componente visual do PyQt6 a se redesenhar na tela imediatamente
        self.label_11.repaint()


    def search_all_product(self): self.show_data(self.search_dialog.get_all_product(), "Todos os Produtos")
    def search_in_stock_product(self): self.show_data(self.search_dialog.get_in_stock_product(), "Produtos em Estoque")
    def search_reorder_product(self): self.show_data(self.search_dialog.get_reorder_product(), "Produtos para Reordenar")
    def search_no_stock_product(self): self.show_data(self.search_dialog.get_no_stock_product(), "Produtos Sem Estoque")


    def apply_search_filter(self, filter_type):
        """Recebe o comando da tela de busca, consulta o banco e atualiza a tabela principal."""

        try:
            # Consulta o banco usando as funções que você já deixou prontas
            data = self.connect_db.get_data(search_flag=filter_type)
            # Atualiza o QTableWidget da tela principal com o resultado filtrado
            self.show_data(data)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Erro ao filtrar tabela: {str(e)}")


    def closeEvent(self, event):
        """Intercepta o clique no X da janela principal."""
        # Verifica se a janela de busca existe e está visível na tela
        if hasattr(self, 'search_dialog') and self.search_dialog.isVisible():
            # Exibe o aviso na tela
            QtWidgets.QMessageBox.warning(self, "Aviso", "Feche primeiro o formulário aberto!")
            # Ignora o fechamento da janela principal (ela continua aberta)
            event.ignore()
        else:
            # Se a busca não estiver aberta, deixa o main.py fechar normalmente
            event.accept()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    
    while True:
        login = LoginWindow()
        # Se o usuário fizer login com sucesso:
        if login.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            window = StockManagement(is_admin=login.is_admin)
            window.show()
            app.exec()  # Aguarda a janela principal ser fechada

            # Se fechou pelo menu "Sair" escolhendo voltar ao login, o loop continua
            if not window.reabrir_login:
                break
        else:
            # Se fechou a tela de login no "X" sem entrar, encerra o programa
            break

    sys.exit(0)


'''
from PyQt6 import QtWidgets, uic, QtGui
import sys
import os
import sqlite3
import locale
from connect_db import DatabaseConnect
from new_product import NewProductWindow
from update_product_info import UpdateProductWindow
from update_stock import UpdateStockWindow
from search import SearchWindow
import qdarktheme
import ctypes  


locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")


#Ui_MainWindow, QtWidgetsBaseClass = uic.loadUiType("./ui/main.ui")

# --- ADICIONE ESTE BLOCO LOGO AQUI NO TOPO ---
try:
    # Cria uma assinatura única para o Windows reconhecer o ícone na barra de tarefas
    myappid = 'meu_sistema.gerenciamento.estoque.1.0' 
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass



def resource_path(relative_path):
    """ Retorna o caminho absoluto para o recurso, funcionando em desenvolvimento e no PyInstaller """
    try:
        # O PyInstaller cria uma pasta temporária e armazena o caminho em _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# SUBSTITUA A SUA LINHA ANTIGA POR ESTA:
ui_path = resource_path("ui/main.ui")
Ui_MainWindow, QtWidgetsBaseClass = uic.loadUiType(ui_path)


class StockManagement(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # Instâncias Limpas
        self.new_product_dialog = NewProductWindow()
        self.update_product_dialog = UpdateProductWindow() # Entrada/Saída
        self.update_stock_dialog = UpdateStockWindow()     # Cadastro Completo
        self.search_dialog = SearchWindow()
        self.connect_db = DatabaseConnect()

        # Sinais da Barra de Ferramentas / Menu (Ajuste para português se necessário)
        self.actionNovo_Produto.triggered.connect(self.open_new_product_dialog)
        self.actionAtualizar_Estoque.triggered.connect(self.open_update_stock_dialog)
        self.actionPesquisar.triggered.connect(self.open_search_dialog)

        # Filtros
        self.actionTodos_Produtos.triggered.connect(lambda: self.apply_search_filter("ALL"))
        self.actionReordenar.triggered.connect(lambda: self.apply_search_filter("RE_ORDER"))
        self.actionEstoque_atual.triggered.connect(lambda: self.apply_search_filter("IN_STOCK"))
        self.actionFora_de_estoque.triggered.connect(lambda: self.apply_search_filter("NO_STOCK"))
        
        self.actionSair.triggered.connect(self.close)

        # Sinais vindos da tela de Busca (search.py)
        self.search_dialog.detaill_btn.clicked.connect(self.search_more_detail)
        
        # --- ESSA É A LINHA QUE CONECTA OS FILTROS DA JANELA DE BUSCA ---
        self.search_dialog.filter_changed.connect(self.apply_search_filter)
        
        # Inicialização Padrão da Tabela da Tela Principal (Mostra todos os produtos ao abrir)
        self.apply_search_filter("ALL")

        # Atualizações Globais
        self.update_dashboard()

        # Configuração do ícone da aplicação (funciona no Windows e Linux)
        self.setWindowIcon(QtGui.QIcon(resource_path("icone.ico")))
    

    def open_new_product_dialog(self):
        try:
            self.new_product_dialog.product_saved_signal.disconnect()
        except TypeError:
            pass
        finally:
            pass
        self.new_product_dialog.product_saved_signal.connect(self.refresh_all)    
        self.new_product_dialog.show()

    def open_update_stock_dialog(self):        
        """Abre a tela de cadastro completo (UpdateStockWindow) baseado na linha selecionada."""
        selected_row = self.tableWidget.currentRow()
        if selected_row != -1:
            product_name = self.tableWidget.item(selected_row, 0).text()
            self.update_stock_dialog.load_product_data(product_name)
            
            # Conecta o sinal apenas uma vez (se possível, mova para o __init__)
            try:
                self.update_stock_dialog.accepted.disconnect()
            except TypeError:
                pass
            self.update_stock_dialog.accepted.connect(self.refresh_all)
            
            # Se for QDialog, use .exec() para travar a tela de trás com segurança
            self.update_stock_dialog.exec() 
        else:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione um produto na tabela da tela principal primeiro.")
    

    def open_search_dialog(self):
        """Abre a janela de pesquisa sem bloquear a tela principal."""
        self.search_dialog.init_search_dialog()
        
        # .show() abre a janela livremente (Não-Modal)
        self.search_dialog.show() 
        self.search_dialog.raise_()  # Garante que ela vai para a frente de todas as telas
        self.search_dialog.activateWindow() # Dá o foco do teclado para ela 

    
    def search_more_detail(self):
        """Ação do botão 'SALVAR DETALHES' da busca: Abre a tela de Entrada/Saída."""
        # Pega o nome do produto selecionado na lista da janela de pesquisa
        product_name = self.search_dialog.get_more_detaill()
        
        if product_name:
            # Exibe a janela de Entrada e Saída (UpdateProductWindow)
            self.update_product_dialog.show()
            self.update_product_dialog.init_product_list(product_name)
            
            # Garante que ao clicar em CADASTRAR dentro dela, a tela principal atualize os dados
            try:
                self.update_product_dialog.accepted.connect(self.refresh_all)
            except Exception:
                pass
            
            self.update_product_dialog.raise_()



    def refresh_all(self):
        self.update_dashboard()
        self.apply_search_filter("ALL") # Reseta a tabela para exibir tudo após atualizar dados
        #self.search_all_product()

    
    def show_data(self, data, title="Gerenciamento de Estoque"):
        table = self.tableWidget
        table.setRowCount(0)

        if data:
            table.setRowCount(len(data))
            for row, product in enumerate(data):
                # 1. Cria os dois botões diretamente como QPushButton
                btn_edit = QtWidgets.QPushButton("Editar", self)
                btn_delete = QtWidgets.QPushButton("Deletar", self)

                # 2. Conecta as funções de clique usando a linha (row) atual
                btn_edit.clicked.connect(lambda checked, r=row: self.action_edit_triggered(r))
                btn_delete.clicked.connect(lambda checked, r=row: self.action_delete_triggered(r))

                # Estilização básica opcional para os botões ficarem elegantes (pode ajustar como quiser)
                btn_edit.setStyleSheet("""
                    QPushButton:hover { 
                        background-color: #999888; 
                        color: black;
                    }
                """)

                btn_delete.setStyleSheet("""
                    QPushButton:hover { 
                        background-color: #ff0000; 
                        color: black;
                    }
                """)

                # 3. Cria um widget container para segurar ambos os botões lado a lado
                container_widget = QtWidgets.QWidget()
                layout = QtWidgets.QHBoxLayout(container_widget)
                
                # Adiciona os botões no layout horizontal
                layout.addWidget(btn_edit)
                layout.addWidget(btn_delete)
                
                # Ajusta as margens e o espaçamento para caber perfeitamente na célula
                layout.setContentsMargins(5, 2, 5, 2)
                layout.setSpacing(5)
                container_widget.setLayout(layout)
                
                
                # --- MAPEAMENTO CORRIGIDO BASEADO NO SEU SELECT REAL ---
                nome_produto = str(product[0])                        # [0] product_name
                custo_unitario = float(product[1] if product[1] else 0) # [1] cost
                preco_venda = float(product[2] if product[2] else 0)    # [2] price
                estoque_atual = int(product[3] if product[3] else 0)    # [3] stock (CORRIGIDO!)
                localizacao = str(product[4])                         # [4] location (CORRIGIDO!)
                pedido_nivel = int(product[5] if product[5] else 0)     # [5] reorder_level (CORRIGIDO!)

                # Cálculos de exibição para a tabela
                valor_estoque = estoque_atual * preco_venda
                custo_estoque = estoque_atual * custo_unitario
                
                # Lógica do "Pedido Requerido" (Se o estoque for menor ou igual ao nível, precisa pedir)
                pedido_requerido = "Sim" if estoque_atual <= pedido_nivel else "Não"
             
                # Inserindo os dados nas colunas certas do seu QTableWidget
                table.setItem(row, 0, QtWidgets.QTableWidgetItem(nome_produto))
                table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(estoque_atual)))
                valor_formatado = locale.currency(valor_estoque, grouping=True)
                table.setItem(row, 2, QtWidgets.QTableWidgetItem(valor_formatado))
                custo_formatado = locale.currency(custo_estoque, grouping=True)
                table.setItem(row, 3, QtWidgets.QTableWidgetItem(custo_formatado))
                table.setItem(row, 4, QtWidgets.QTableWidgetItem(str(pedido_nivel)))
                table.setItem(row, 5, QtWidgets.QTableWidgetItem(pedido_requerido))
                table.setItem(row, 6, QtWidgets.QTableWidgetItem(localizacao))
                
                # Cola o botão de opções na última coluna (Coluna 7)
                table.setCellWidget(row, 7, container_widget)
                #table.setCellWidget(row, 7, option_btn)
                table.setRowCount(len(data))


    def action_delete_triggered(self, row):
        """Executa a exclusão do produto selecionado após confirmação na tela."""
        product_name = self.tableWidget.item(row, 0).text()
        choice = QtWidgets.QMessageBox.warning(
            self, "Deletar !!!", f"Tem certeza que deseja deletar o produto '{product_name}'?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.Cancel
        )
        if choice == QtWidgets.QMessageBox.StandardButton.Yes:
            self.connect_db.delete_product(product_name=product_name)
            self.refresh_all()



    def action_edit_triggered(self, row):
        product_name = self.tableWidget.item(row, 0).text()
        self.update_stock_dialog.show()
        self.update_stock_dialog.load_product_data(product_name)
        self.update_stock_dialog.accepted.connect(self.refresh_all)

    def update_dashboard(self):
        # Proteção robusta contra None vindo do SQL SUM()
        c_stock = self.connect_db.get_current_stock()
        self.label_3.setText(f"Unidades: {c_stock[0] if c_stock and c_stock[0] else 0}")
        
        s_val = self.connect_db.get_stock_value()
        valor_bruto = s_val[0] if (s_val and isinstance(s_val, tuple)) else s_val
        valor_numerico = float(valor_bruto) if valor_bruto is not None else 0.0
        e_formatado = locale.currency(valor_numerico, grouping=True)
        self.label_5.setText(e_formatado)

        s_cost = self.connect_db.get_stock_cost()
        valor_bruto = s_cost[0] if (s_cost and isinstance(s_cost, tuple)) else s_cost
        valor_numerico = float(valor_bruto) if valor_bruto is not None else 0.0
        c_formatado = locale.currency(valor_numerico, grouping=True)
        self.label_7.setText(c_formatado)
                
        # Busca a contagem de produtos fora de estoque        
        no_stock_result = self.connect_db.get_no_stock_product()  

        reorder = self.connect_db.get_reorder_product()
        self.label_9.setText(f"Requeridos: {str(reorder[0] if reorder and reorder[0] else 0)}")

        # DEBUG: Veja no terminal o que o banco está retornando de verdade
        #print(f"DEBUG DASHBOARD: Retorno de get_no_stock_product = {no_stock_result}")

        # Tratamento correto caso o SQLite retorne uma tupla, ex: (0,)
        if isinstance(no_stock_result, tuple) and len(no_stock_result) > 0:
            qtd_fora_estoque = no_stock_result[0]
        else:
            qtd_fora_estoque = no_stock_result if no_stock_result else 0

        # Atualiza a interface de forma explícita
        self.label_11.setText(f"Produtos: {int(qtd_fora_estoque)}")
        
        # Força o componente visual do PyQt6 a se redesenhar na tela imediatamente
        self.label_11.repaint()


    def search_all_product(self): self.show_data(self.search_dialog.get_all_product(), "Todos os Produtos")
    def search_in_stock_product(self): self.show_data(self.search_dialog.get_in_stock_product(), "Produtos em Estoque")
    def search_reorder_product(self): self.show_data(self.search_dialog.get_reorder_product(), "Produtos para Reordenar")
    def search_no_stock_product(self): self.show_data(self.search_dialog.get_no_stock_product(), "Produtos Sem Estoque")


    def apply_search_filter(self, filter_type):
        """Recebe o comando da tela de busca, consulta o banco e atualiza a tabela principal."""

        try:
            # Consulta o banco usando as funções que você já deixou prontas
            data = self.connect_db.get_data(search_flag=filter_type)
            # Atualiza o QTableWidget da tela principal com o resultado filtrado
            self.show_data(data)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Erro ao filtrar tabela: {str(e)}")


    def closeEvent(self, event):
        """Intercepta o clique no X da janela principal."""
        # Verifica se a janela de busca existe e está visível na tela
        if hasattr(self, 'search_dialog') and self.search_dialog.isVisible():
            # Exibe o aviso na tela
            QtWidgets.QMessageBox.warning(self, "Aviso", "Feche primeiro o formulário aberto!")
            # Ignora o fechamento da janela principal (ela continua aberta)
            event.ignore()
        else:
            # Se a busca não estiver aberta, deixa o main.py fechar normalmente
            event.accept()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    qdarktheme.setup_theme("light")  # Pode usar "light", "dark" ou "auto"
    window = StockManagement()
    window.show()
    sys.exit(app.exec())



'''