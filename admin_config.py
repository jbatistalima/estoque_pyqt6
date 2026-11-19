from PyQt6 import QtWidgets, QtCore
from connect_db import DatabaseConnect

class AdminConfigWindow(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Painel do Administrador")
        self.setFixedSize(360, 260)
        self.db = DatabaseConnect()

        layout_principal = QtWidgets.QVBoxLayout(self)
        tabs = QtWidgets.QTabWidget()

        # --- ABA 1: CADASTRAR NOVO USUÁRIO ---
        tab_usuarios = QtWidgets.QWidget()
        layout_user = QtWidgets.QVBoxLayout(tab_usuarios)

        self.novo_user = QtWidgets.QLineEdit()
        self.novo_user.setPlaceholderText("Nome de usuário (ex: joao)")

        self.nova_senha = QtWidgets.QLineEdit()
        self.nova_senha.setPlaceholderText("Senha")
        self.nova_senha.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)

        self.check_admin = QtWidgets.QCheckBox("Este usuário é Administrador")

        btn_add_user = QtWidgets.QPushButton("Cadastrar Usuário")
        btn_add_user.clicked.connect(self.salvar_usuario)

        layout_user.addWidget(QtWidgets.QLabel("Novo Usuário:"))
        layout_user.addWidget(self.novo_user)
        layout_user.addWidget(self.nova_senha)
        layout_user.addWidget(self.check_admin)
        layout_user.addWidget(btn_add_user)

        # --- ABA 2: DATA DE VALIDADE ---
        tab_validade = QtWidgets.QWidget()
        layout_val = QtWidgets.QVBoxLayout(tab_validade)

        layout_val.addWidget(QtWidgets.QLabel("Nova Data de Validade do Sistema:"))
        self.date_edit = QtWidgets.QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yyyy")

        data_atual_str = self.db.obter_validade()
        if data_atual_str:
            self.date_edit.setDate(QtCore.QDate.fromString(data_atual_str, "yyyy-MM-dd"))
        else:
            self.date_edit.setDate(QtCore.QDate.currentDate())

        btn_salvar_val = QtWidgets.QPushButton("Salvar Nova Validade")
        btn_salvar_val.clicked.connect(self.salvar_validade)

        layout_val.addWidget(self.date_edit)
        layout_val.addWidget(btn_salvar_val)
        layout_val.addStretch()

        tabs.addTab(tab_usuarios, "Usuários")
        tabs.addTab(tab_validade, "Validade do App")
        layout_principal.addWidget(tabs)


    def salvar_usuario(self):
        user = self.novo_user.text().strip()
        senha = self.nova_senha.text().strip()
        is_admin = 1 if self.check_admin.isChecked() else 0

        if not user or not senha:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Preencha usuário e senha.")
            return

        if self.db.cadastrar_usuario(user, senha, is_admin):
            QtWidgets.QMessageBox.information(self, "Sucesso", f"Usuário '{user}' cadastrado!")
            self.novo_user.clear()
            self.nova_senha.clear()
            self.check_admin.setChecked(False)
        else:
            QtWidgets.QMessageBox.warning(self, "Erro", "Este nome de usuário já existe.")


    def salvar_validade(self):
        nova_data = self.date_edit.date().toString("yyyy-MM-dd")
        self.db.atualizar_validade(nova_data)
        QtWidgets.QMessageBox.information(self, "Sucesso", "Data de validade atualizada e assinada!")
