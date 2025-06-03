# utils/dataframe_utils.py
import pandas as pd
import json
import numpy as np 

# CORRIGIDO: Nome da função alterado para corresponder à importação
def load_dataframe_from_store(stored_json_data): 
    """
    Converte dados do dcc.Store (string JSON ou dict Python, resultado de df.to_json(orient='split')) 
    de volta para um DataFrame Pandas.
    """
    if not stored_json_data:
        # print("load_dataframe_from_store: No data provided.")
        return pd.DataFrame()
    
    data_to_parse = stored_json_data
    
    if isinstance(stored_json_data, dict): 
        try:
            data_to_parse = json.dumps(stored_json_data) 
        except TypeError as te:
            print(f"TypeError ao fazer json.dumps do dict do store: {te}.")
            return pd.DataFrame()

    df = pd.DataFrame()
    try:
        df = pd.read_json(data_to_parse, orient='split')
        for col in df.columns:
            if df[col].dtype == 'object' or (pd.api.types.is_integer_dtype(df[col]) and df[col].abs().max() > 1e12):
                try:
                    converted_col = pd.to_datetime(df[col], errors='coerce', unit='ms' if pd.api.types.is_integer_dtype(df[col]) else None)
                    if converted_col.notna().sum() > 0.5 * len(df[col].dropna()):
                        df[col] = converted_col
                    else: 
                        if df[col].dtype == 'object':
                             temp_col_str_ignore = pd.to_datetime(df[col], errors='ignore')
                             if pd.api.types.is_datetime64_any_dtype(temp_col_str_ignore):
                                 df[col] = temp_col_str_ignore
                except Exception: pass 
        return df
    except ValueError as ve: 
        print(f"ValueError ao ler JSON com orient='split': {ve}. Data (início): {str(data_to_parse)[:200]}")
        if isinstance(data_to_parse, str):
            try:
                print("Tentando pd.read_json com orient='records' como fallback...")
                df_fallback = pd.read_json(data_to_parse, orient='records') 
                return df_fallback
            except Exception as e_inner_records:
                print(f"Falha com orient='records': {e_inner_records}. Tentando com orient='columns'...")
                try:
                    df_fallback_cols = pd.read_json(data_to_parse, orient='columns')
                    return df_fallback_cols
                except Exception as e_inner_cols:
                    print(f"Falha total ao tentar pd.read_json com fallbacks: {e_inner_cols}")
        return pd.DataFrame() 
    except Exception as e:
        print(f"Erro GERAL ao converter dados do Store para DataFrame: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()