import sqlite3
import hashlib
import hmac
import base64
import os
from pathlib import Path


class DatabaseConnect:
    # 1. ADICIONADO: Chave secreta necessária para assinar a data de validade
    CHAVE_SECRETA = b"MinhaChaveSuperSecreta_Estoque_2026!@#"

    def __init__(self):
        self.db_folder = "./db"
        self.db_path = f"{self.db_folder}/products_db.db"
        self.table_name = "product_master"
        self.connection = None
        self.cursor = None

        # 2. CORRIGIDO: Primeiro cria a pasta e o banco, depois cria as tabelas de segurança
        self.init_database()
        self.criar_tabelas_seguranca()

    def connector(self):
        """Abre a conexão com o banco de dados e o cursor."""
        self.connection = sqlite3.connect(self.db_path)
        self.cursor = self.connection.cursor()

    def init_database(self):
        # Garante que a pasta ./db existe antes de conectar
        folder_path = Path(self.db_folder)
        if not folder_path.exists():
            folder_path.mkdir(parents=True, exist_ok=True)

        self.connector()
        try:
            sql = f"SELECT name FROM sqlite_master WHERE type='table' AND name='{self.table_name}'"
            self.cursor.execute(sql)
            result = self.cursor.fetchone()

            if not result:
                sql = f"""CREATE TABLE "{self.table_name}" (
                    "product_name" TEXT NOT NULL,
                    "cost" NUMERIC,
                    "price" NUMERIC,
                    "location" INTEGER,
                    "reorder_level" INTEGER,
                    "stock" INTEGER DEFAULT 0, 
                    PRIMARY KEY("product_name")
                )"""
                self.cursor.execute(sql)
                self.connection.commit()

        except Exception as e:
            if self.connection:
                self.connection.rollback()
            print(f"Erro ao inicializar o banco: {e}")
            raise e
        finally:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()

    def criar_tabelas_seguranca(self):
        self.connector()
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    senha_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    is_admin INTEGER DEFAULT 0
                )
            """)

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS config_sistema (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    token_validade TEXT NOT NULL
                )
            """)
            self.connection.commit()

            # Verifica se já existe algum usuário cadastrado
            self.cursor.execute("SELECT COUNT(*) FROM usuarios")
            qtd_usuarios = self.cursor.fetchone()[0]

            # Verifica se já existe data de validade cadastrada
            self.cursor.execute("SELECT COUNT(*) FROM config_sistema")
            qtd_config = self.cursor.fetchone()[0]

        finally:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()

        # Cria o admin padrão fora do bloco acima (pois cadastrar_usuario abre sua própria conexão)
        if qtd_usuarios == 0:
            self.cadastrar_usuario("admin", "admin123", is_admin=1)

        if qtd_config == 0:
            self.atualizar_validade("2026-12-31", inserir=True)

    # --- PROTEÇÃO ANTI-ADULTERAÇÃO DA DATA DE VALIDADE ---
    def _criptografar_data(self, data_str):
        assinatura = hmac.new(self.CHAVE_SECRETA, data_str.encode('utf-8'), hashlib.sha256).hexdigest()
        pacote = f"{data_str}|{assinatura}".encode('utf-8')
        return base64.b64encode(pacote).decode('utf-8')

    def _descriptografar_data(self, token_b64):
        try:
            pacote = base64.b64decode(token_b64.encode('utf-8')).decode('utf-8')
            data_str, assinatura_salva = pacote.split("|")
            assinatura_esperada = hmac.new(self.CHAVE_SECRETA, data_str.encode('utf-8'), hashlib.sha256).hexdigest()

            if hmac.compare_digest(assinatura_salva, assinatura_esperada):
                return data_str
        except Exception:
            pass
        return None

    def obter_validade(self):
        self.connector()
        try:
            self.cursor.execute("SELECT token_validade FROM config_sistema WHERE id = 1")
            res = self.cursor.fetchone()
            if res:
                return self._descriptografar_data(res[0])
            return None
        finally:
            self.cursor.close()
            self.connection.close()

    def atualizar_validade(self, nova_data_str, inserir=False):
        token = self._criptografar_data(nova_data_str)
        self.connector()
        try:
            if inserir:
                self.cursor.execute("INSERT INTO config_sistema (id, token_validade) VALUES (1, ?)", (token,))
            else:
                self.cursor.execute("UPDATE config_sistema SET token_validade = ? WHERE id = 1", (token,))
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            raise e
        finally:
            self.cursor.close()
            self.connection.close()

    # --- CRIPTOGRAFIA E GESTÃO DE USUÁRIOS ---
    def gerar_hash(self, senha, salt=None):
        if salt is None:
            salt = os.urandom(16).hex()
        hash_obj = hashlib.pbkdf2_hmac('sha256', senha.encode('utf-8'), salt.encode('utf-8'), 100000)
        return hash_obj.hex(), salt

    def cadastrar_usuario(self, username, senha, is_admin=0):
        senha_hash, salt = self.gerar_hash(senha)
        self.connector()
        try:
            self.cursor.execute(
                "INSERT INTO usuarios (username, senha_hash, salt, is_admin) VALUES (?, ?, ?, ?)",
                (username, senha_hash, salt, is_admin)
            )
            self.connection.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            self.cursor.close()
            self.connection.close()

    def verificar_login(self, username, senha_digitada):
        self.connector()
        try:
            self.cursor.execute("SELECT senha_hash, salt, is_admin FROM usuarios WHERE username = ?", (username,))
            resultado = self.cursor.fetchone()
            if resultado:
                senha_hash_banco, salt, is_admin = resultado
                hash_tentativa, _ = self.gerar_hash(senha_digitada, salt)
                if hash_tentativa == senha_hash_banco:
                    return True, bool(is_admin)
            return False, False
        finally:
            self.cursor.close()
            self.connection.close()

    # --- SEUS MÉTODOS ORIGINAIS DE PRODUTOS CONTINUAM AQUI ABAIXO ---
    def com_update_execute(self, sql, params=None):
        self.connector()
        try:
            if params:
                self.cursor.execute(sql, params)
            else:
                self.cursor.execute(sql)
            self.connection.commit()
            return None
        except Exception as e:
            self.connection.rollback()
            raise e
        finally:
            self.cursor.close()
            self.connection.close()


    def com_update_execute(self, sql, params=None):
        self.connector()
        try:
            if params:
                self.cursor.execute(sql, params)
            else: 
                self.cursor.execute(sql)   
            self.connection.commit()  # Adicionado commit para salvar as alterações
            return None        
        except Exception as e:
            self.connection.rollback()
            raise e
        finally:
            self.cursor.close()
            self.connection.close()  # Corrigido: conection -> connection


    def com_search_one_execute(self, sql):
        self.connector()
        try:
            self.cursor.execute(sql)
            result = self.cursor.fetchone()
            return result
        except Exception:
            return None
        finally:
            self.cursor.close()
            self.connection.close()  # Corrigido: conection -> connection


    def com_search_all_execute(self, sql):
        self.connector()
        try:
            self.cursor.execute(sql)
            result = self.cursor.fetchall()
            return result
        except Exception:
            return None
        finally:
            self.cursor.close()
            self.connection.close()  # Corrigido: conection -> connection


    def get_all_locations(self):
        sql = f"SELECT DISTINCT location FROM {self.table_name}"  # Corrigido: self, table_name -> self.table_name
        result = self.com_search_all_execute(sql=sql)
        return result
      

    def add_new_product(self, **kwargs):
        column_name = tuple(kwargs.keys())
        values = tuple(kwargs.values())
        
        sql = f"INSERT INTO {self.table_name} {column_name} VALUES {values}"
        result = self.com_update_execute(sql=sql)

        return result


    def update_product(self, **kwargs):
        values = tuple(kwargs.values())

        sql =f"""UPDATE {self.table_name} SET 
        price = {kwargs["price"]},
        location = {kwargs["location"]},
        reorder_level = {kwargs["reorder_level"]},
        stock = {kwargs["stock"]}
        WHERE product_name='{values[0]}'"""

        result = self.com_update_execute(sql=sql)
        return result    
    


    def get_data(self, search_flag="", product_name=""):
        
        if search_flag=="ALL":
            sql=f"SELECT product_name, cost, price, stock, location, reorder_level FROM {self.table_name}"
        elif search_flag=="IN_STOCK":
            sql=(f"SELECT product_name, cost, price, stock, location, reorder_level FROM {self.table_name} "    
                f"WHERE stock>0")
        elif search_flag=="NO_STOCK":
            sql=(f"SELECT product_name, cost, price, stock, location, reorder_level FROM {self.table_name} " 
                f"WHERE stock<=0")   
        elif search_flag=="RE_ORDER":
            sql=(f"SELECT product_name, cost, price, stock, location, reorder_level FROM {self.table_name} " 
                f"WHERE stock<=reorder_level AND stock > 0")    
        else:
            sql=(f"SELECT product_name, cost, price, stock, location, reorder_level FROM {self.table_name} "
                f"WHERE product_name='{product_name}'")  


        result = self.com_search_all_execute(sql=sql) 
        return result 

    
    def delete_product(self, product_name):
        sql = f"DELETE from {self.table_name} WHERE product_name='{product_name}'"
        result = self.com_update_execute(sql=sql)
        return result
    

    def get_product_names(self, product_name):
        sql = f"SELECT product_name FROM {self.table_name} WHERE product_name LIKE '%{product_name}%'"
        search_result = self.com_search_all_execute(sql=sql)
        return search_result

    
    def get_single_product_info(self, product_name):
        self.connector()
        try:
            sql = f"""
                SELECT stock, reorder_level, location, cost, price 
                FROM {self.table_name}
                WHERE product_name = '{product_name}'
            """
            self.cursor.execute(sql)
            resultado = self.cursor.fetchone()
            return resultado  # Retorna a tupla com os 5 valores
        except Exception as e:
            #print(f"Erro ao buscar informações do produto: {e}")
            return None
        finally:
            self.cursor.close()
            self.connection.close()
     


    def get_current_stock(self):
        sql = f"SELECT sum(stock) FROM {self.table_name}"
        search_result = self.com_search_one_execute(sql=sql)
        return search_result


    def get_stock_value(self):
        sql = f"SELECT sum(price*stock) FROM {self.table_name}"
        search_result = self.com_search_one_execute(sql=sql)
        return search_result


    def get_stock_cost(self):
        sql = f"SELECT sum(cost*stock) FROM {self.table_name}"
        search_result = self.com_search_one_execute(sql=sql)
        return search_result                
    

    def get_reorder_product(self):
        sql = f"SELECT COUNT(*) FROM {self.table_name} WHERE stock <= reorder_level AND stock > 0"
        #search_result = self.com_search_one_execute(sql=sql)
        return self.com_search_one_execute(sql)


    def get_no_stock_product(self):   
        sql = f"SELECT count(*) FROM {self.table_name} WHERE stock<=0"
        search_result = self.com_search_one_execute(sql=sql)
        return search_result 

    
    def update_stock(self, **kwargs):
        sql = f""" UPDATE {self.table_name} SET stock={kwargs["stock"]} 
        WHERE product_name='{kwargs["product_name"]}'"""

        result = self.com_update_execute(sql)
        return result


# Para testar a criação automática, basta instanciar a classe:
if __name__ == "__main__":
    db = DatabaseConnect()
    print("Banco de dados e tabela verificados/criados com sucesso!")



