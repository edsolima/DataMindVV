# test_llama_import.py
try:
    from llama_index.readers.dataframe import PandasDataFrameReader
    print("SUCESSO: PandasDataFrameReader importado de llama_index.readers.dataframe")
    print(f"Localização: {PandasDataFrameReader.__file__}")
except ImportError as e1:
    print(f"FALHA ao importar de llama_index.readers.dataframe: {e1}")
    print("Tentando caminho alternativo/antigo...")
    try:
        from llama_index.core.readers.base import PandasDataFrameReader # Caminho mais antigo ou interno
        print("SUCESSO: PandasDataFrameReader importado de llama_index.core.readers.base")
        print(f"Localização: {PandasDataFrameReader.__file__}")
    except ImportError as e2:
        print(f"FALHA ao importar de llama_index.core.readers.base também: {e2}")
        print("Verifique se 'pip install llama-index --upgrade' foi executado no ambiente correto.")

print("\nVerificando importações para Ollama no LlamaIndex:")
try:
    from llama_index.llms.ollama import Ollama as OllamaLLMLlamaIndex
    print("SUCESSO: OllamaLLMLlamaIndex importado.")
except ImportError as e:
    print(f"FALHA ao importar OllamaLLMLlamaIndex: {e}")

try:
    from llama_index.embeddings.ollama import OllamaEmbedding
    print("SUCESSO: OllamaEmbedding importado.")
except ImportError as e:
    print(f"FALHA ao importar OllamaEmbedding: {e}")