# utils/rag_module_optimized.py

import pandas as pd
import numpy as np
from typing import Tuple, Optional, Dict, List
import json
import textwrap
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from utils.logger import log_info, log_error, log_warning, log_debug

# LlamaIndex
LLAMA_INDEX_AVAILABLE = False
Document = None
VectorStoreIndex = None
Settings = None
OllamaLLMLlamaIndex = None
OllamaEmbedding = None
# For PydanticProgram or FunctionTool (conceptual for now)
# from llama_index.core.program import LLMTextCompletionProgram, PydanticProgram
# from llama_index.core.bridge.pydantic import BaseModel, Field


try:
    from llama_index.core import Document as LlamaDocument, VectorStoreIndex as LlamaVectorStoreIndex, Settings as LlamaSettings
    from llama_index.llms.ollama import Ollama as LlamaOllamaLLM
    from llama_index.embeddings.ollama import OllamaEmbedding as LlamaOllamaEmbedding

    Document = LlamaDocument
    VectorStoreIndex = LlamaVectorStoreIndex
    Settings = LlamaSettings
    OllamaLLMLlamaIndex = LlamaOllamaLLM
    OllamaEmbedding = LlamaOllamaEmbedding

    LLAMA_INDEX_AVAILABLE = True
    log_info("Componentes principais do LlamaIndex carregados com sucesso")
except ImportError as e_li:
    log_warning("Bibliotecas LlamaIndex não instaladas ou com erro", extra={"error": str(e_li)})

# LLMs (Ollama e Groq imports)
OLLAMA_AVAILABLE = False
try:
    import ollama
    OLLAMA_AVAILABLE = True
    log_info("Biblioteca Ollama carregada com sucesso")
except ImportError:
    log_warning("Biblioteca 'ollama' não instalada")

GROQ_AVAILABLE = False
try:
    from groq import Groq
    GROQ_AVAILABLE = True
    log_info("Biblioteca Groq carregada com sucesso")
except ImportError:
    log_warning("Biblioteca 'groq' não instalada")

RAG_INDEX_CACHE_PREFIX = "rag_index_for_"
SUMMARY_CACHE_PREFIX = "summary_for_"

def get_dataframe_hash(df: pd.DataFrame) -> str:
    """Gera hash único do DataFrame para cache inteligente"""
    df_string = df.to_string()
    return hashlib.md5(df_string.encode()).hexdigest()[:16]

def get_dataframe_simple_summary(df: pd.DataFrame, max_unique_to_list=5, max_string_length=80) -> str:
    if df.empty:
        return "O DataFrame fornecido está vazio."

    num_rows, num_cols = df.shape
    lines = [f"O conjunto de dados contém {num_rows} linhas e {num_cols} colunas.", "Colunas e seus tipos:"]

    for col in df.columns:
        dtype = str(df[col].dtype)
        unique_count = df[col].nunique()
        line = f"- '{col}' (Tipo: {dtype}, Únicos: {unique_count})"

        if pd.api.types.is_numeric_dtype(df[col]):
            desc = df[col].describe().round(2)
            line += f", Média: {desc.get('mean', 'N/A')}, Min: {desc.get('min', 'N/A')}, Max: {desc.get('max', 'N/A')}"
        elif unique_count > 0 and unique_count <= max_unique_to_list:
            top_values = df[col].value_counts(normalize=False, dropna=False).head(max_unique_to_list)
            val_str_list = [f"'{str(idx)[:max_string_length]}' ({cnt})" for idx, cnt in top_values.items()]
            line += f", Comuns: {'; '.join(val_str_list)}"

        lines.append(f"  {line}")

    return "\n".join(lines)

def create_smart_chunks(df: pd.DataFrame, chunk_size: int = 50, overlap: int = 5) -> List[pd.DataFrame]:
    """
    Cria chunks inteligentes do DataFrame com sobreposição para manter contexto
    """
    chunks = []
    total_rows = len(df)

    for start in range(0, total_rows, chunk_size - overlap):
        end = min(start + chunk_size, total_rows)
        chunk = df.iloc[start:end].copy()
        chunks.append(chunk)

        if end >= total_rows:
            break

    log_info("DataFrame dividido em chunks", extra={
        "total_chunks": len(chunks),
        "chunk_size": chunk_size,
        "total_rows": total_rows,
        "overlap": overlap
    })
    return chunks

def convert_numpy_to_python(obj):
    """Converte tipos NumPy para tipos Python nativos para serialização"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_to_python(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_to_python(item) for item in obj]
    else:
        return obj

def create_comprehensive_summary(df: pd.DataFrame, original_data_key: str) -> List[Document]:
    """
    Cria documentos abrangentes SEM LIMITAÇÃO DE DADOS: sumário + chunks completos + análises especiais
    """
    log_info("Iniciando criação de sumário abrangente", extra={
        "data_key": original_data_key,
        "rows": len(df),
        "columns": len(df.columns),
        "memory_usage_mb": df.memory_usage(deep=True).sum() / 1024 / 1024
    })
    
    documents = []

    # 1. Documento de sumário geral COMPLETO
    general_summary = get_dataframe_simple_summary(df)
    summary_doc = Document(
        text=f"SUMÁRIO GERAL COMPLETO do dataset {original_data_key} ({len(df)} linhas):\n{general_summary}",
        doc_id=f"{original_data_key}_summary",
        metadata={"doc_type": "summary", "importance": "high", "total_rows": len(df)}
    )
    documents.append(summary_doc)

    # 2. Documentos por chunks COMPLETOS - sem limitação de tamanho
    if len(df) <= 1000:
        chunk_size = 100
    elif len(df) <= 5000:
        chunk_size = 200
    elif len(df) <= 20000:
        chunk_size = 500
    else:
        chunk_size = 1000
    
    log_debug("Estratégia de chunking definida", extra={
        "chunk_size": chunk_size,
        "total_rows": len(df),
        "strategy": "adaptive_based_on_size"
    })

    chunks = create_smart_chunks(df, chunk_size=chunk_size, overlap=min(20, chunk_size//10))

    for i, chunk in enumerate(chunks):
        chunk_summary = []
        numeric_cols = chunk.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            try:
                stats = chunk[col].describe()
                chunk_summary.append(f"{col}: média={stats['mean']:.2f}, std={stats['std']:.2f}")
            except:
                pass

        categorical_cols = chunk.select_dtypes(include=['object', 'string', 'category']).columns # Added category
        categorical_info = []
        for col in categorical_cols[:5]:
            try:
                top_values = chunk[col].value_counts().head(3)
                cat_text = f"{col}: {dict(top_values)}"
                categorical_info.append(cat_text)
            except:
                pass

        chunk_content = [
            f"CHUNK COMPLETO {i+1}/{len(chunks)} do dataset {original_data_key}",
            f"Linhas {int(chunk.index[0])} a {int(chunk.index[-1])} (total: {len(chunk)} linhas)",
            f"Estatísticas numéricas: {'; '.join(chunk_summary) if chunk_summary else 'Nenhuma coluna numérica'}",
            f"Principais valores categóricos: {'; '.join(categorical_info) if categorical_info else 'Sem análise categórica'}",
            "\n=== DADOS COMPLETOS DO CHUNK ==="
        ]
        chunk_data_text = chunk.to_string(max_rows=None, max_cols=None)
        chunk_content.append(chunk_data_text)

        metadata = {
            "doc_type": "chunk_complete",
            "chunk_index": int(i),
            "start_row": int(chunk.index[0]),
            "end_row": int(chunk.index[-1]),
            "chunk_size": int(len(chunk)),
            "importance": "high"
        }
        metadata = convert_numpy_to_python(metadata)

        chunk_doc = Document(
            text="\n".join(chunk_content),
            doc_id=f"{original_data_key}_chunk_complete_{i}",
            metadata=metadata
        )
        documents.append(chunk_doc)

    for col in df.columns:
        try:
            col_analysis = [
                f"ANÁLISE COMPLETA DA COLUNA '{col}' no dataset {original_data_key}",
                f"Tipo de dados: {df[col].dtype}",
                f"Valores únicos: {df[col].nunique()} de {len(df)} total",
                f"Valores nulos: {df[col].isnull().sum()}"
            ]

            if pd.api.types.is_numeric_dtype(df[col]):
                stats = df[col].describe()
                col_analysis.extend([
                    f"Estatísticas: min={stats.get('min', 'N/A')}, max={stats.get('max', 'N/A')}, média={stats.get('mean', 'N/A'):.2f}",
                    f"Quartis: Q1={stats.get('25%', 'N/A')}, Q2={stats.get('50%', 'N/A')}, Q3={stats.get('75%', 'N/A')}"
                ])
                Q1, Q3 = df[col].quantile([0.25, 0.75])
                IQR = Q3 - Q1
                outliers = df[(df[col] < Q1 - 1.5*IQR) | (df[col] > Q3 + 1.5*IQR)]
                if not outliers.empty:
                    col_analysis.append(f"Outliers detectados: {len(outliers)} valores extremos")
            else:
                value_counts = df[col].value_counts()
                col_analysis.append(f"Top 10 valores mais frequentes:")
                for idx, (value, count) in enumerate(value_counts.head(10).items()):
                    percentage = (count / len(df)) * 100
                    col_analysis.append(f"  {idx+1}. '{str(value)[:50]}': {count} ocorrências ({percentage:.1f}%)")

            metadata = {
                "doc_type": "column_analysis",
                "column_name": str(col),
                "data_type": str(df[col].dtype),
                "importance": "medium"
            }
            metadata = convert_numpy_to_python(metadata)

            col_doc = Document(
                text="\n".join(col_analysis),
                doc_id=f"{original_data_key}_column_{col}",
                metadata=metadata
            )
            documents.append(col_doc)

        except Exception as e:
            log_warning("Erro ao analisar coluna", extra={
                "column_name": str(col),
                "error": str(e),
                "data_key": original_data_key
            })
            continue

    log_info("Documentos RAG criados com sucesso", extra={
        "total_documents": len(documents),
        "summary_docs": 1,
        "chunk_docs": len(chunks),
        "column_analysis_docs": len(df.columns),
        "data_key": original_data_key,
        "strategy": "comprehensive"
    })
    return documents

def prepare_dataframe_for_chat_optimized(
    original_data_key: str,
    df: pd.DataFrame,
    cache_instance,
    ollama_embedding_model: str = "nomic-embed-text",
    use_cache: bool = True,
    strategy: str = "comprehensive"
) -> Tuple[bool, str, Optional[str]]:
    
    log_info("Iniciando preparação de dados para chat", extra={
        "data_key": original_data_key,
        "rows": len(df) if df is not None else 0,
        "columns": len(df.columns) if df is not None else 0,
        "embedding_model": ollama_embedding_model,
        "use_cache": use_cache,
        "strategy": strategy
    })

    if not LLAMA_INDEX_AVAILABLE:
        log_warning("LlamaIndex não disponível, usando sumário textual simples")
        if df is None or df.empty:
            return False, "DataFrame vazio.", None
        try:
            summary_text = get_dataframe_simple_summary(df)
            summary_key = f"{SUMMARY_CACHE_PREFIX}{original_data_key}"
            cache_instance.set(summary_key, summary_text, timeout=3600)
            log_info("Sumário textual simples criado", extra={
                "summary_key": summary_key,
                "summary_length": len(summary_text)
            })
            return True, "Sumário textual simples preparado!", summary_key
        except Exception as e_sum:
            log_error("Erro ao gerar sumário textual", extra={
                "error": str(e_sum),
                "data_key": original_data_key
            })
            return False, f"Erro ao gerar sumário textual: {e_sum}", None

    df_hash = get_dataframe_hash(df)
    index_cache_key = f"{RAG_INDEX_CACHE_PREFIX}{original_data_key}_{df_hash}_{strategy}"

    if use_cache and cache_instance.has(index_cache_key):
        log_info("Índice RAG encontrado no cache", extra={
            "cache_key": index_cache_key,
            "data_key": original_data_key,
            "strategy": strategy
        })
        return True, "Dados já indexados encontrados no cache!", index_cache_key

    log_info("Iniciando indexação RAG", extra={
        "data_key": original_data_key,
        "rows": len(df),
        "strategy": strategy,
        "embedding_model": ollama_embedding_model
    })

    try:
        if not OLLAMA_AVAILABLE: # Should be LLAMA_INDEX_AVAILABLE for embedding model too
            log_error("Biblioteca Ollama não disponível para embedding")
            return False, "Biblioteca 'ollama' (para embedding) não disponível.", None

        try:
            Settings.embed_model = OllamaEmbedding(model_name=ollama_embedding_model)
            Settings.llm = None # LLM for query is set later
            log_info("Modelo de embedding configurado", extra={
                "embedding_model": ollama_embedding_model,
                "data_key": original_data_key
            })
        except Exception as e_settings:
            log_error("Erro ao configurar embedding LlamaIndex", extra={
                "error": str(e_settings),
                "embedding_model": ollama_embedding_model,
                "data_key": original_data_key
            })
            return False, f"Erro ao configurar embedding LlamaIndex: {e_settings}", None

        if strategy == "comprehensive":
            documents = create_comprehensive_summary(df, original_data_key)
        elif strategy == "hierarchical":
            documents = create_hierarchical_summary(df, original_data_key) # Assuming this function exists or is similar
        elif strategy == "chunked":
            chunks_data = create_smart_chunks(df, chunk_size=200, overlap=20)
            documents = []
            for i, chunk_df in enumerate(chunks_data):
                chunk_text = chunk_df.to_string(max_rows=None)
                metadata = {"chunk_index": int(i), "doc_type": "chunk", "total_rows": int(len(chunk_df))}
                metadata = convert_numpy_to_python(metadata)
                doc = Document(
                    text=f"Chunk COMPLETO {i+1}/{len(chunks_data)} do dataset {original_data_key} ({len(chunk_df)} linhas):\n{chunk_text}",
                    doc_id=f"{original_data_key}_chunk_{i}",
                    metadata=metadata
                )
                documents.append(doc)
        elif strategy == "sample":
            sample_size = min(1000, max(1, len(df) // 10)) # Ensure sample_size is at least 1
            if len(df) > sample_size :
                sample_df = df.sample(n=sample_size, random_state=42) if sample_size > 0 else df.head(1) # Handle tiny dfs
                log_warning("Criando amostra de dados para indexação", extra={
                    "sample_size": len(sample_df),
                    "total_size": len(df),
                    "data_key": original_data_key,
                    "strategy": strategy
                })
            else:
                sample_df = df
            documents = create_comprehensive_summary(sample_df, f"{original_data_key}_sample")
        else:
            return False, f"Estratégia '{strategy}' não reconhecida.", None

        if not documents:
            return False, "Nenhum documento criado para indexação.", None

        log_info("Construindo VectorStoreIndex", extra={
            "document_count": len(documents),
            "data_key": original_data_key,
            "strategy": strategy
        })
        index = VectorStoreIndex.from_documents(documents, show_progress=True)
        log_info("VectorStoreIndex construído com sucesso", extra={
            "data_key": original_data_key,
            "strategy": strategy,
            "document_count": len(documents)
        })

        cache_instance.set(index_cache_key, index, timeout=14400) # 4 horas
        if cache_instance.has(index_cache_key):
            log_info("Índice RAG salvo no cache com sucesso", extra={
                "cache_key": index_cache_key,
                "data_key": original_data_key,
                "strategy": strategy,
                "document_count": len(documents),
                "rows_processed": len(df),
                "cache_timeout_hours": 4
            })
            return True, f"Dados indexados com estratégia '{strategy}' ({len(documents)} docs, {len(df)} linhas processadas)!", index_cache_key
        else: # Should ideally not happen if set was successful
            log_error("Falha ao salvar índice no cache", extra={
                "cache_key": index_cache_key,
                "data_key": original_data_key,
                "strategy": strategy
            })
            return False, "Erro ao salvar índice no cache.", None

    except Exception as e:
        log_error("Erro crítico na indexação RAG", extra={
            "error": str(e),
            "data_key": original_data_key,
            "strategy": strategy,
            "embedding_model": ollama_embedding_model,
            "traceback": traceback.format_exc()
        })
        import traceback
        traceback.print_exc()
        return False, f"Erro crítico na indexação: {e}", None


def create_hierarchical_summary(df: pd.DataFrame, original_data_key: str) -> List[Document]:
    """
    Cria documentos hierárquicos: sumário geral + chunks + amostras importantes.
    (Implementation based on the provided code)
    """
    documents = []
    general_summary = get_dataframe_simple_summary(df)
    summary_doc = Document(
        text=f"SUMÁRIO GERAL do dataset {original_data_key}:\n{general_summary}",
        doc_id=f"{original_data_key}_summary",
        metadata={"doc_type": "summary", "importance": "high"}
    )
    documents.append(summary_doc)

    chunks_data = create_smart_chunks(df, chunk_size=150, overlap=15)
    for i, chunk_df in enumerate(chunks_data):
        chunk_summary_stats = []
        for col in chunk_df.select_dtypes(include=[np.number]).columns:
            stats = chunk_df[col].describe()
            chunk_summary_stats.append(f"{col}: média={stats['mean']:.2f}, std={stats['std']:.2f}")

        chunk_content_list = [
            f"CHUNK {i+1}/{len(chunks_data)} do dataset {original_data_key}",
            f"Linhas {int(chunk_df.index[0])} a {int(chunk_df.index[-1])} (total: {len(chunk_df)} linhas)",
            f"Estatísticas numéricas: {'; '.join(chunk_summary_stats) if chunk_summary_stats else 'Nenhuma coluna numérica'}",
            "\nAmostras representativas:"
        ]
        num_samples = min(10, len(chunk_df))
        sample_indices = np.linspace(0, len(chunk_df) - 1, num_samples, dtype=int) if len(chunk_df) > 0 else []


        for idx_pos in sample_indices:
            row = chunk_df.iloc[idx_pos]
            row_text = ". ".join([f"{col_name}: {str(val)[:80]}" for col_name, val in row.items()])
            chunk_content_list.append(f"Linha {int(chunk_df.index[idx_pos])}: {row_text}")

        metadata = {
            "doc_type": "chunk", "chunk_index": int(i),
            "start_row": int(chunk_df.index[0]), "end_row": int(chunk_df.index[-1]),
            "importance": "medium"
        }
        metadata = convert_numpy_to_python(metadata)
        chunk_doc = Document(text="\n".join(chunk_content_list), doc_id=f"{original_data_key}_chunk_{i}", metadata=metadata)
        documents.append(chunk_doc)

    for col in df.select_dtypes(include=[np.number]).columns:
        try:
            Q1, Q3 = df[col].quantile([0.25, 0.75])
            IQR = Q3 - Q1
            lower_bound, upper_bound = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
            outliers_df = df[(df[col] < lower_bound) | (df[col] > upper_bound)]

            if not outliers_df.empty and len(outliers_df) <= 100:
                outlier_content_list = [
                    f"VALORES EXTREMOS da coluna '{col}' no dataset {original_data_key}",
                    f"Encontrados {len(outliers_df)} outliers (Q1-1.5*IQR = {float(lower_bound):.2f}, Q3+1.5*IQR = {float(upper_bound):.2f})",
                    "Registros com valores extremos:"
                ]
                for _, row_series in outliers_df.head(50).iterrows():
                    row_text = ". ".join([f"{c_name}: {str(v)[:50]}" for c_name, v in row_series.items()])
                    outlier_content_list.append(f"Linha {int(row_series.name)}: {row_text}")
                metadata = {"doc_type": "outliers", "column": str(col), "importance": "high"}
                metadata = convert_numpy_to_python(metadata)
                outlier_doc = Document(text="\n".join(outlier_content_list), doc_id=f"{original_data_key}_outliers_{col}", metadata=metadata)
                documents.append(outlier_doc)
        except Exception as e_outlier:
            log_warning("Erro ao processar outliers da coluna", extra={
                "column_name": str(col),
                "error": str(e_outlier),
                "data_key": original_data_key
            })
            continue
    
    log_info("Documentos hierárquicos criados", extra={
        "total_documents": len(documents),
        "data_key": original_data_key,
        "strategy": "hierarchical"
    })
    return documents


def query_data_with_llm_optimized(
    context_cache_key: str,
    cache_instance,
    user_question: str,
    llm_provider: str,
    ollama_model_name: Optional[str] = "llama3.2:latest",
    groq_api_key: Optional[str] = None,
    groq_model_name: Optional[str] = "llama3-8b-8192",
    similarity_top_k: int = 8
) -> Tuple[str, Optional[str]]:

    log_info("Iniciando consulta RAG otimizada", extra={
        "context_cache_key": context_cache_key,
        "user_question": user_question[:100] + "..." if len(user_question) > 100 else user_question,
        "llm_provider": llm_provider,
        "model_name": ollama_model_name if llm_provider == "ollama" else groq_model_name,
        "similarity_top_k": similarity_top_k
    })
    
    context_object = cache_instance.get(context_cache_key)

    if not context_object:
        log_warning("Contexto não encontrado no cache", extra={
            "context_cache_key": context_cache_key,
            "user_question": user_question[:50] + "..." if len(user_question) > 50 else user_question
        })
        return "", "Contexto não encontrado no cache. Prepare os dados novamente."

    is_llama_index = LLAMA_INDEX_AVAILABLE and isinstance(context_object, VectorStoreIndex)

    if is_llama_index:
        log_info("Usando índice LlamaIndex para consulta", extra={
            "context_cache_key": context_cache_key,
            "llm_provider": llm_provider
        })
        try:
            query_llm_instance = None
            if llm_provider == "ollama":
                if not OLLAMA_AVAILABLE: 
                    log_error("Ollama não disponível para consulta")
                    return "", "Ollama não disponível."
                query_llm_instance = OllamaLLMLlamaIndex(model=ollama_model_name, request_timeout=180.0)
            elif llm_provider == "groq":
                if not GROQ_AVAILABLE or not groq_api_key: 
                    log_error("Groq não configurado adequadamente", extra={
                        "groq_available": GROQ_AVAILABLE,
                        "has_api_key": bool(groq_api_key)
                    })
                    return "", "Groq não configurado adequadamente."
                try:
                    from llama_index.llms.langchain import LangChainLLM # Compatibility for LlamaIndex v0.9.x
                    from langchain_groq import ChatGroq # Ensure langchain_groq is installed
                    lc_llm = ChatGroq(temperature=0.1, groq_api_key=groq_api_key, model_name=groq_model_name, max_tokens=4000)
                    query_llm_instance = LangChainLLM(llm=lc_llm)
                except ImportError: # Fallback for LlamaIndex v0.10.x+ direct integration
                    try:
                        from llama_index.llms.groq import Groq as LlamaGroqLLM # Check if this class exists
                        query_llm_instance = LlamaGroqLLM(model=groq_model_name, api_key=groq_api_key)
                        log_info("Usando LlamaIndex Groq LLM direto")
                    except ImportError:
                        log_error("Bibliotecas Langchain/Groq ou LlamaIndex Groq não encontradas")
                        return "", "Bibliotecas Langchain/Groq ou LlamaIndex Groq não encontradas."


            if query_llm_instance:
                current_settings_llm = Settings.llm # Store current global llm if any
                Settings.llm = query_llm_instance # Set for this query
                log_info("LLM para query configurado", extra={
                    "llm_provider": llm_provider,
                    "model_name": ollama_model_name if llm_provider == "ollama" else groq_model_name,
                    "context_cache_key": context_cache_key
                })


            query_engine = context_object.as_query_engine(
                similarity_top_k=similarity_top_k,
                response_mode="tree_summarize", # Good for summarization over multiple documents
            )

            # Enhanced prompt for data analysis and chart suggestions with improved column interpretation
            enhanced_question = f"""
            Você é um analista de dados especializado. Analise TODOS os dados fornecidos e responda à seguinte pergunta de forma precisa, detalhada e abrangente.

            PERGUNTA: {user_question}

            INSTRUÇÕES IMPORTANTES:
            1. Base sua resposta EXCLUSIVAMENTE nos dados fornecidos no contexto.
            2. Utilize TODOS os chunks e documentos relevantes disponíveis.
            3. Cite números específicos, estatísticas e valores exatos quando disponíveis.
            4. Se a pergunta envolve contagens, some TODOS os registros dos chunks relevantes.
            5. Se a pergunta envolve tendências ou padrões, analise TODOS os dados disponíveis.
            6. Se a informação completa não estiver disponível, indique isso explicitamente.
            7. Para análises estatísticas, considere TODOS os valores presentes nos dados.
            8. Para análises categóricas, considere TODAS as categorias e suas frequências.
            9. Se houver análises por colunas específicas, utilize essas informações detalhadas.
            10. Sempre mencione o total de registros analisados quando relevante.

            INTERPRETAÇÃO DE COLUNAS:
            - Identifique o tipo de cada coluna (numérica, categórica, data/hora, texto) e seu significado no contexto dos dados.
            - Para colunas numéricas, identifique se representam valores contínuos (como preços, idades) ou discretos (como contagens).
            - Para colunas categóricas, identifique os valores possíveis e suas frequências.
            - Para colunas de data/hora, identifique o intervalo temporal e a granularidade (diária, mensal, etc.).
            - Identifique relações entre colunas, como correlações entre variáveis numéricas ou associações entre categorias.

            SUGESTÃO DE GRÁFICOS:
            - Se a sua análise revelar padrões visuais interessantes, sugira um tipo de gráfico apropriado.
            - Escolha o tipo de gráfico mais adequado para o tipo de dados e a pergunta:
              * 'bar' (barras): Para comparar categorias ou valores discretos
              * 'line' (linhas): Para tendências temporais ou sequências ordenadas
              * 'scatter' (dispersão): Para relações entre duas variáveis numéricas
              * 'pie' (pizza): Para proporções de um todo (use apenas quando apropriado)
              * 'histogram': Para distribuições de variáveis numéricas
              * 'boxplot': Para distribuições e outliers de variáveis numéricas
              * 'heatmap': Para correlações ou dados bidimensionais
              * 'area': Para valores cumulativos ou composição ao longo do tempo
              * 'violin': Para distribuições detalhadas comparativas
            - Exemplo de sugestão: "Parece haver uma tendência de crescimento nas vendas ao longo do tempo. Um gráfico de linhas da coluna 'Vendas' pela coluna 'Data' poderia visualizar isso."
            - Se você sugerir um gráfico, SEMPRE extraia os parâmetros para ele no seguinte formato JSON:
              `CHART_PARAMS_JSON: {{"chart_type": "tipo_do_grafico", "x_column": "nome_coluna_x", "y_column": "nome_coluna_y", "color_column": "nome_coluna_cor_opcional", "title": "titulo_sugerido"}}`
              (Não inclua este JSON se nenhum gráfico for relevante ou se a extração dos parâmetros for ambígua).

            11. Responda em português brasileiro de forma clara e estruturada.

            IMPORTANTE: NÃO faça inferências além dos dados fornecidos. Seja preciso e completo.
            """

            log_info("Executando consulta RAG", extra={
                "similarity_top_k": similarity_top_k,
                "question_length": len(enhanced_question),
                "context_cache_key": context_cache_key,
                "llm_provider": llm_provider
            })
            response = query_engine.query(enhanced_question)
            
            log_info("Consulta RAG executada com sucesso", extra={
                "response_length": len(str(response)),
                "context_cache_key": context_cache_key,
                "llm_provider": llm_provider,
                "model_name": ollama_model_name if llm_provider == "ollama" else groq_model_name
            })
            
            if query_llm_instance and 'current_settings_llm' in locals(): # Restore global LLM if changed
                 Settings.llm = current_settings_llm

            return str(response), None

        except Exception as e:
            log_error("Erro na consulta RAG", extra={
                "error": str(e),
                "context_cache_key": context_cache_key,
                "llm_provider": llm_provider,
                "model_name": ollama_model_name if llm_provider == "ollama" else groq_model_name,
                "user_question": user_question[:50] + "..." if len(user_question) > 50 else user_question,
                "traceback": traceback.format_exc()
            })
            import traceback
            traceback.print_exc()
            if 'current_settings_llm' in locals() and query_llm_instance: # Restore on error too
                 Settings.llm = current_settings_llm
            return "", f"Erro na consulta: {str(e)}"

    else: # Fallback for simple text summary
        log_info("Usando sumário textual para consulta", extra={
            "context_cache_key": context_cache_key,
            "llm_provider": llm_provider,
            "fallback_reason": "no_llama_index_or_simple_summary"
        })
        data_summary = str(context_object) # This is just a string summary
        # Simplified prompt for text summary
        prompt = f"""Você é um analista de dados. Analise o sumário do dataset e responda à pergunta.
        Sumário: {data_summary}
        Pergunta: {user_question}
        Resposta (em português brasileiro):"""

        try:
            if llm_provider == "ollama":
                if not OLLAMA_AVAILABLE: 
                    log_error("Ollama não disponível para consulta fallback")
                    return "", "Ollama não disponível."
                log_info("Executando consulta fallback com Ollama", extra={
                    "model_name": ollama_model_name,
                    "prompt_length": len(prompt)
                })
                ollama_response = ollama.chat(model=ollama_model_name, messages=[{'role': 'user', 'content': prompt}])
                return ollama_response['message']['content'], None
            elif llm_provider == "groq":
                if not GROQ_AVAILABLE or not groq_api_key: 
                    log_error("Groq não configurado para consulta fallback")
                    return "", "Groq não configurado."
                log_info("Executando consulta fallback com Groq", extra={
                    "model_name": groq_model_name,
                    "prompt_length": len(prompt)
                })
                client = Groq(api_key=groq_api_key)
                completion = client.chat.completions.create(
                    model=groq_model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1, max_tokens=3000
                )
                return completion.choices[0].message.content, None
        except Exception as e_llm_fallback:
            log_error("Erro na consulta com sumário textual", extra={
                "error": str(e_llm_fallback),
                "llm_provider": llm_provider,
                "model_name": ollama_model_name if llm_provider == "ollama" else groq_model_name,
                "context_cache_key": context_cache_key
            })
            return "", f"Erro na comunicação com LLM (fallback): {str(e_llm_fallback)}"


# Aliases and utility functions (mostly unchanged, ensure they call optimized versions)
def get_recommended_strategy(df_size: int, force_complete: bool = False) -> str:
    if force_complete: return "comprehensive"
    if df_size < 2000: return "comprehensive"
    elif df_size < 10000: return "hierarchical"
    elif df_size < 50000: return "chunked"
    else: return "sample"

def prepare_dataframe_for_chat(
    original_data_key: str,
    df: pd.DataFrame,
    cache_instance,
    ollama_embedding_model: str = "nomic-embed-text",
    force_complete_processing: bool = True # Defaulting to comprehensive as per user request
) -> Tuple[bool, str, Optional[str]]:
    # Determinar estratégia primeiro
    if force_complete_processing:
        strategy = "comprehensive"
    else:
        strategy = get_recommended_strategy(len(df), force_complete_processing)
    
    log_info("Iniciando preparação de dados para chat", extra={
        "data_key": original_data_key,
        "total_records": len(df),
        "strategy": strategy,
        "force_complete": force_complete_processing
    })

    if force_complete_processing:
        log_info("Forçando estratégia COMPREHENSIVE", extra={
            "data_key": original_data_key,
            "total_records": len(df),
            "strategy": strategy,
            "force_complete": True
        })
    else:
        log_info("Auto-selecionando estratégia RAG", extra={
            "data_key": original_data_key,
            "total_records": len(df),
            "strategy": strategy,
            "force_complete": False
        })

    return prepare_dataframe_for_chat_optimized(
        original_data_key=original_data_key, df=df, cache_instance=cache_instance,
        ollama_embedding_model=ollama_embedding_model, strategy=strategy, use_cache=True # use_cache=True is reasonable here
    )

def query_data_with_llm(
    context_cache_key: str, cache_instance, user_question: str, llm_provider: str,
    ollama_model_name: Optional[str] = "llama3.2:latest",
    groq_api_key: Optional[str] = None, groq_model_name: Optional[str] = "llama3-8b-8192"
) -> Tuple[str, Optional[str]]:
    return query_data_with_llm_optimized(
        context_cache_key, cache_instance, user_question, llm_provider,
        ollama_model_name, groq_api_key, groq_model_name,
        similarity_top_k=8 # Using the optimized version's default
    )

def verify_data_completeness(context_cache_key: str, cache_instance, expected_total_rows: int) -> Dict[str, any]:
    log_info("Verificando completude dos dados RAG", extra={
        "context_cache_key": context_cache_key,
        "expected_total_rows": expected_total_rows
    })
    
    context_object = cache_instance.get(context_cache_key)
    if not context_object: 
        log_warning("Contexto não encontrado para verificação", extra={
            "context_cache_key": context_cache_key
        })
        return {"status": "error", "message": "Contexto não encontrado"}
    if not (LLAMA_INDEX_AVAILABLE and isinstance(context_object, VectorStoreIndex)):
        log_info("Usando sumário textual para verificação", extra={
            "context_cache_key": context_cache_key,
            "llama_index_available": LLAMA_INDEX_AVAILABLE
        })
        return {"status": "warning", "message": "Usando sumário textual, não índice completo"}
    try:
        docstore = context_object.docstore
        all_docs = list(docstore.docs.values())
        chunk_docs = [doc for doc in all_docs if doc.metadata.get("doc_type") in ["chunk_complete", "chunk"]] # Consider both
        summary_docs = [doc for doc in all_docs if doc.metadata.get("doc_type") == "summary"]
        total_indexed_rows = 0
        # This logic for total_indexed_rows might be complex if chunks overlap significantly
        # A simpler proxy might be to check if a 'summary' doc metadata has total_rows
        summary_meta_rows = 0
        if summary_docs and summary_docs[0].metadata.get("total_rows"):
            summary_meta_rows = summary_docs[0].metadata.get("total_rows",0)

        if summary_meta_rows == expected_total_rows : # A good sign
             total_indexed_rows = expected_total_rows # Assume if summary matches, chunks cover it.
        else: # Fallback to summing chunk sizes (less accurate due to overlap or if not all chunks are 'chunk_complete')
            # For "comprehensive", "chunk_size" in "chunk_complete" should sum up correctly
            # For other strategies, this might not perfectly match expected_total_rows.
            for doc in chunk_docs:
                # Heuristic: if it's not a complete chunk, it's harder to sum accurately.
                # The 'comprehensive' strategy has 'chunk_complete' docs with 'chunk_size'.
                 total_indexed_rows += doc.metadata.get("chunk_size", 0) if doc.metadata.get("doc_type") == "chunk_complete" else doc.metadata.get("total_rows",0)


        # Due to potential overlaps or varying chunk strategies, direct sum might not be perfect.
        # The presence of 'summary_doc' with 'total_rows' metadata matching 'expected_total_rows' is a strong indicator.
        is_complete_check = False
        if summary_docs and summary_docs[0].metadata.get("doc_type") == "summary":
            if summary_docs[0].metadata.get("total_rows", -1) == expected_total_rows:
                 is_complete_check = True

        completeness_ratio = (total_indexed_rows / expected_total_rows) * 100 if expected_total_rows > 0 else 0
        # If using 'comprehensive' strategy, `total_indexed_rows` from `chunk_complete`'s `chunk_size` should be accurate.

        result = {
            "status": "success", "total_documents": len(all_docs),
            "chunk_documents": len(chunk_docs), "summary_documents": len(summary_docs),
            "total_indexed_rows_from_chunks": total_indexed_rows, # Might be > expected due to overlap in some strategies
            "expected_rows": expected_total_rows,
            "completeness_percentage_from_chunks": round(completeness_ratio, 2),
            "is_complete_by_summary_metadata": is_complete_check,
            "is_complete_heuristic": is_complete_check or completeness_ratio >= 95 # Heuristic
        }
        
        log_info("Verificação de completude concluída", extra={
            "context_cache_key": context_cache_key,
            "total_documents": len(all_docs),
            "chunk_documents": len(chunk_docs),
            "summary_documents": len(summary_docs),
            "expected_rows": expected_total_rows,
            "indexed_rows": total_indexed_rows,
            "completeness_percentage": round(completeness_ratio, 2),
            "is_complete": is_complete_check or completeness_ratio >= 95
        })
        
        return result
    except Exception as e:
        log_error("Erro ao verificar completude dos dados", extra={
            "context_cache_key": context_cache_key,
            "expected_total_rows": expected_total_rows,
            "error": str(e)
        })
        return {"status": "error", "message": f"Erro ao verificar completude: {e}"}


def force_complete_reindexing(
    original_data_key: str, df: pd.DataFrame, cache_instance,
    ollama_embedding_model: str = "nomic-embed-text"
) -> Tuple[bool, str, Optional[str]]:
    log_info("FORÇANDO reprocessamento completo", extra={
        "data_key": original_data_key,
        "total_records": len(df),
        "force_reprocess": True
    })
    
    df_hash = get_dataframe_hash(df)
    removed_keys = []
    for strategy_key_part in ["comprehensive", "hierarchical", "chunked", "sample"]:
        old_cache_key = f"{RAG_INDEX_CACHE_PREFIX}{original_data_key}_{df_hash}_{strategy_key_part}"
        if cache_instance.has(old_cache_key):
            cache_instance.delete(old_cache_key)
            removed_keys.append(old_cache_key)
    
    if removed_keys:
        log_info("Cache RAG removido", extra={
            "data_key": original_data_key,
            "removed_keys": removed_keys,
            "count": len(removed_keys)
        })
    
    # Also remove simple summary key if it exists
    simple_summary_key = f"{SUMMARY_CACHE_PREFIX}{original_data_key}"
    if cache_instance.has(simple_summary_key):
        cache_instance.delete(simple_summary_key)
        log_info("Cache de sumário simples removido", extra={
            "data_key": original_data_key,
            "summary_key": simple_summary_key
        })


    return prepare_dataframe_for_chat_optimized(
        original_data_key=original_data_key, df=df, cache_instance=cache_instance,
        ollama_embedding_model=ollama_embedding_model, strategy="comprehensive", use_cache=False
    )

log_info("Módulo RAG carregado", extra={
    "strategy": "COMPREHENSIVE",
    "features": ["processamento_completo", "sugestoes_graficos"],
    "llama_index_available": LLAMA_INDEX_AVAILABLE,
    "ollama_available": OLLAMA_AVAILABLE,
    "groq_available": GROQ_AVAILABLE
})