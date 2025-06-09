# test_llama_import.py
try:
    from llama_index.readers.dataframe import PandasDataFrameReader
    log_info("SUCESSO: PandasDataFrameReader importado de llama_index.readers.dataframe")
    log_info(f"Localização: {PandasDataFrameReader.__file__}")
except ImportError as e1:
    log_error("FALHA ao importar de llama_index.readers.dataframe:", exception=e1)
    log_info("Tentando caminho alternativo/antigo...")
    try:
        from llama_index.core.readers.base import PandasDataFrameReader # Caminho mais antigo ou interno
        log_info("SUCESSO: PandasDataFrameReader importado de llama_index.core.readers.base")
        log_info(f"Localização: {PandasDataFrameReader.__file__}")
    except ImportError as e2:
        log_error("FALHA ao importar de llama_index.core.readers.base também:", exception=e2)
        log_info("Verifique se 'pip install llama-index --upgrade' foi executado no ambiente correto.")

print("\nVerificando importações para Ollama no LlamaIndex:")
try:
    from llama_index.llms.ollama import Ollama as OllamaLLMLlamaIndex
    log_info("SUCESSO: OllamaLLMLlamaIndex importado.")
except ImportError as e:
    log_error("FALHA ao importar OllamaLLMLlamaIndex:", exception=e)

try:
    from llama_index.embeddings.ollama import OllamaEmbedding
    log_info("SUCESSO: OllamaEmbedding importado.")
except ImportError as e:
    log_error("FALHA ao importar OllamaEmbedding:", exception=e)