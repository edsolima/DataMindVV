# utils/query_manager.py
import os
import yaml
from typing import Dict, List, Optional

class QueryManager:
    def __init__(self):
        self.query_file = "config/saved_queries.yml"
        self.ensure_directories()
        print("QueryManager initialized.")
        
    def ensure_directories(self):
        """Ensure necessary directories exist for saved queries"""
        os.makedirs("config", exist_ok=True)
        if not os.path.exists(self.query_file):
            with open(self.query_file, 'w') as f:
                yaml.dump({}, f) # Cria arquivo vazio se não existir
            print(f"Saved queries file created at {self.query_file}")


    def save_query(self, name: str, query_string: str, description: str = "") -> bool:
        """Save a custom SQL query"""
        try:
            queries = self.load_queries()
            queries[name] = {'query': query_string, 'description': description}
            with open(self.query_file, 'w') as f:
                yaml.dump(queries, f, default_flow_style=False, sort_keys=False)
            print(f"Query '{name}' saved.")
            return True
        except Exception as e:
            print(f"Error saving query '{name}': {e}")
            return False

    def load_queries(self) -> Dict[str, Dict]:
        """Load all saved queries"""
        queries = {}
        if os.path.exists(self.query_file):
            try:
                with open(self.query_file, 'r') as f:
                    loaded_data = yaml.safe_load(f)
                    if loaded_data and isinstance(loaded_data, dict): # Verificar se o arquivo não está vazio ou malformado
                        queries = loaded_data
            except Exception as e:
                print(f"Error loading queries from {self.query_file}: {e}")
                # Retornar vazio em caso de erro
        return queries

    def get_query(self, name: str) -> Optional[Dict]:
        """Get a specific saved query"""
        queries = self.load_queries()
        return queries.get(name)

    def delete_query(self, name: str) -> bool:
        """Delete a saved query"""
        try:
            queries = self.load_queries()
            if name in queries:
                del queries[name]
                with open(self.query_file, 'w') as f:
                    yaml.dump(queries, f, default_flow_style=False, sort_keys=False)
                print(f"Query '{name}' deleted.")
                return True
            print(f"Query '{name}' not found for deletion.")
            return False
        except Exception as e:
            print(f"Error deleting query '{name}': {e}")
            return False

    def list_query_names(self) -> List[str]:
        """List all saved query names"""
        queries = self.load_queries()
        return list(queries.keys())

    def get_standard_queries(self) -> Dict[str, Dict]:
        """Returns a dictionary of common standard queries."""
        # {table_name} e {column_name} são placeholders a serem substituídos
        return {
            "Select All From Table": {
                "query": "SELECT * FROM {table_name};",
                "description": "Selects all data from a table. Replace {table_name}."
            },
            "Count Rows in Table": {
                "query": "SELECT COUNT(*) AS total_rows FROM {table_name};",
                "description": "Counts total rows in a table. Replace {table_name}."
            },
            "Show Top 10 Rows": {
                "query": "-- For PostgreSQL/MySQL/SQLite:\nSELECT * FROM {table_name} LIMIT 10;\n\n-- For SQL Server:\n-- SELECT TOP 10 * FROM {table_name};",
                "description": "Selects the first 10 rows. Adjust for your DB. Replace {table_name}."
            },
            "List Distinct Values in Column": {
                "query": "SELECT DISTINCT {column_name} FROM {table_name} ORDER BY {column_name};",
                "description": "Unique values from a column. Replace {table_name} and {column_name}."
            },
            "Count by Category": {
                "query": "SELECT {category_column}, COUNT(*) AS count_per_category \nFROM {table_name} \nGROUP BY {category_column} \nORDER BY count_per_category DESC;",
                "description": "Counts rows per category. Replace {table_name} and {category_column}."
            },
            "Sum Numeric Column by Category": {
                "query": "SELECT {category_column}, SUM({numeric_column}) AS total_sum \nFROM {table_name} \nGROUP BY {category_column} \nORDER BY total_sum DESC;",
                "description": "Sums a numeric column grouped by category. Replace all placeholders."
            },
            "Average Numeric Column by Category": {
                "query": "SELECT {category_column}, AVG({numeric_column}) AS average_value \nFROM {table_name} \nGROUP BY {category_column} \nORDER BY average_value DESC;",
                "description": "Calculates average of a numeric column by category. Replace all placeholders."
            }
        }