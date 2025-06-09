import pytest
from utils.database_manager import DatabaseManager

def test_validate_identifier():
    dbm = DatabaseManager()
    assert dbm._validate_identifier("tabela_valida")
    assert dbm._validate_identifier("schema.tabela")
    assert not dbm._validate_identifier("tabela;drop table")
    assert not dbm._validate_identifier("tabela--comentario")

def test_connect_invalid_connection():
    dbm = DatabaseManager()
    # Conexão inválida deve retornar False
    assert not dbm.connect("postgresql://usuario:senha@localhost:9999/db_inexistente") 