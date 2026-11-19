import sys
import os
from datetime import datetime
from PyQt6 import QtWidgets, uic
from connect_db import DatabaseConnect


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class LoginWindow(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi(resource_path("ui/login.ui"), self)
        self.db = DatabaseConnect()
        self.is_admin = False

        # Garante máscara de senha mesmo se esquecer no Qt Designer
        self.lineEdit_pass.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.btn_login.clicked.connect(self.fazer_login)
        

    def fazer_login(self):
        usuario = self.lineEdit_user.text().strip()
        senha = self.lineEdit_pass.text().strip()

        sucesso, is_admin = self.db.verificar_login(usuario, senha)
        if not sucesso:
            QtWidgets.QMessageBox.warning(self, "Erro", "Usuário ou senha incorretos!")
            return

        validade_str = self.db.obter_validade()

        # Bloqueia se o arquivo .db foi adulterado manualmente
        if validade_str is None:
            if is_admin:
                QtWidgets.QMessageBox.critical(
                    self, "Alerta de Segurança",
                    "A assinatura da data de validade foi violada ou corrompida!\nEntre como Admin para redefinir a validade."
                )
                self.is_admin = True
                self.accept()
                return
            else:
                QtWidgets.QMessageBox.critical(self, "Erro Crítico", "Licença corrompida. Contate o Administrador.")
                return

        data_validade = datetime.strptime(validade_str, "%Y-%m-%d").date()
        hoje = datetime.now().date()
        dias_restantes = (data_validade - hoje).days

        if dias_restantes < 0:
            if is_admin:
                QtWidgets.QMessageBox.warning(
                    self, "Licença Expirada", 
                    f"A validade expirou em {data_validade.strftime('%d/%m/%Y')}.\nComo Administrador, você pode entrar para renovar."
                )
            else:
                QtWidgets.QMessageBox.critical(
                    self, "Sistema Bloqueado", 
                    "A validade deste aplicativo expirou. Contate o Administrador."
                )
                return
        elif dias_restantes <= 30:
            QtWidgets.QMessageBox.information(
                self, "Aviso de Licença",
                f"Atenção: A licença do sistema vence em {dias_restantes} dia(s) ({data_validade.strftime('%d/%m/%Y')})."
            )

        # Só libera a entrada depois de passar por todas as verificações acima
        self.is_admin = is_admin
        self.accept()
