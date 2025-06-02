import streamlit as st
import os
import sqlite3
import ollama
import pandas as pd
import re # <-- NEW: Import the regex module

# --- Streamlit Page Configuration ---
st.set_page_config(page_title="NL2SQL with Qwen3:8B", layout="centered")

# --- 1. Database Schema Definition ---
DB_SCHEMA_PRODUCTS = """
CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT,
    price REAL,
    stock_quantity INTEGER
);
"""

# --- 2. Local Database File Path ---
DB_FILE = 'products.db'
DB_PATH = os.path.join(os.getcwd(), DB_FILE)

# --- 3. Function to Generate SQL using Qwen3:8B via Ollama ---
def generate_sql_qwen(natural_language_query: str, db_schema: str) -> str:
    """
    Generates a SQL query from a natural language query using Qwen3:8B via Ollama.
    Includes stronger prompt engineering and robust post-processing to extract only SQL.

    Args:
        natural_language_query (str): The user's natural language question.
        db_schema (str): The database schema (DDL or descriptive text) to guide the LLM.

    Returns:
        str: The generated SQL query. Returns an empty string if an error occurs or SQL is not found.
    """

    # --- REVISED PROMPT: Stronger directives to only output SQL ---
    prompt_template = f"""
    You are an expert SQL generator.
    Your ONLY task is to convert natural language questions into accurate SQL queries.
    You MUST respond with *only* the SQL query.
    Do NOT include any explanations, internal thoughts, conversational text, markdown formatting (like ```sql), or any other text before or after the SQL.
    Your response should be *solely* the SQL query.

    Here is the database schema:
    {db_schema}

    Question: {natural_language_query}
    SQL:
    """

    messages = [
        {"role": "user", "content": prompt_template}
    ]

    try:
        response = ollama.chat(model='qwen3:8b', messages=messages, stream=False)
        raw_llm_output = response['message']['content'].strip()

        # --- Robust Post-processing to extract ONLY SQL ---
        # This regex attempts to find and extract the SQL query by looking for common SQL keywords
        # at the start of a line, and then captures everything until a semicolon or the end of the string.
        # It handles potential markdown blocks and common LLM "thought" patterns like <think>.

        # 1. Aggressively remove common LLM "thought" tags and code block delimiters
        cleaned_output = re.sub(r'</?think>', '', raw_llm_output, flags=re.IGNORECASE).strip()
        # Remove markdown fences and "SQL:" prefix if present
        cleaned_output = re.sub(r'^(```sql|```|SQL:)\s*', '', cleaned_output, flags=re.IGNORECASE|re.MULTILINE).strip()


        # 2. Attempt to find the SQL statement using regex
        # This regex looks for lines starting with common SQL DML/DDL keywords
        # and captures content until a semicolon, the end of string, or a blank line.
        sql_match = re.search(
            r'^(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\s+.*?(;|$)',
            cleaned_output,
            re.IGNORECASE | re.DOTALL | re.MULTILINE
        )

        final_sql = ""
        if sql_match:
            final_sql = sql_match.group(0).strip()
            # Ensure it ends with a semicolon if it's a full statement
            if not final_sql.endswith(';'):
                final_sql += ";"
        else:
            # Fallback if regex doesn't match: try to find the first line starting with a SQL keyword
            # This is less robust but might catch some cases.
            sql_keywords = ['select', 'insert', 'update', 'delete', 'create', 'alter', 'drop']
            potential_lines = cleaned_output.split('\n')
            for i, line in enumerate(potential_lines):
                if line.strip().lower().startswith(tuple(sql_keywords)):
                    # Assume this line and possibly subsequent non-empty lines are the SQL
                    temp_sql_lines = [line.strip()]
                    for j in range(i + 1, len(potential_lines)):
                        if potential_lines[j].strip():
                            temp_sql_lines.append(potential_lines[j].strip())
                        else:
                            break # Stop at first blank line
                    final_sql = " ".join(temp_sql_lines).strip()
                    break # Stop after finding the first potential SQL

        # Final check to ensure semicolon and remove any remaining trailing markdown if LLM misbehaves
        if final_sql and final_sql.endswith('```'):
            final_sql = final_sql[:-3].strip()
        if final_sql and not final_sql.endswith(';') and final_sql.lower().startswith(tuple(sql_keywords)):
             final_sql += ";"


        return final_sql

    except Exception as e:
        st.error(f"Error communicating with Ollama or Qwen3:8B: {e}")
        st.info("Please ensure Ollama is running and the 'qwen3:8b' model is downloaded (`ollama run qwen3:8b`).")
        return ""

# --- 4. Streamlit User Interface Setup ---
st.title("🛍️ Natural Language to SQL Product Query (Local Qwen3)")
st.write("Ask questions about your `products.db` database in plain English!")

if not os.path.exists(DB_PATH):
    st.error(f"Database file '{DB_FILE}' not found at '{DB_PATH}'.")
    st.info("Please run the `db.py` script first to create and populate the database.")
    st.stop()

user_question = st.text_input(
    "Enter your question:",
    "What is the total stock quantity of all products?",
    key="user_question_input"
)

if user_question:
    with st.spinner("Thinking... Generating SQL and fetching data..."):
        try:
            generated_sql = generate_sql_qwen(user_question, DB_SCHEMA_PRODUCTS)

            if generated_sql:
                st.subheader("Generated SQL:")
                st.code(generated_sql, language="sql")

                conn = None
                try:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute(generated_sql)
                    results = cursor.fetchall()

                    st.subheader("Query Results:")
                    if results:
                        col_names = [description[0] for description in cursor.description]

                        # --- Clean Column Names for Display ---
                        cleaned_col_names = []
                        for col in col_names:
                            if col.lower().startswith('sum(') and col.endswith(')'):
                                field = col[len('sum('):-1]
                                cleaned_col_names.append(f"Total {field.replace('_', ' ').title()}")
                            elif col.lower().startswith('count(') and col.endswith(')'):
                                field = col[len('count('):-1]
                                cleaned_col_names.append(f"Number of {field.replace('_', ' ').title()}")
                            elif col.lower().startswith('avg(') and col.endswith(')'):
                                field = col[len('avg('):-1]
                                cleaned_col_names.append(f"Average {field.replace('_', ' ').title()}")
                            elif col.lower().startswith('max(') and col.endswith(')'):
                                field = col[len('max('):-1]
                                cleaned_col_names.append(f"Maximum {field.replace('_', ' ').title()}")
                            elif col.lower().startswith('min(') and col.endswith(')'):
                                field = col[len('min('):-1]
                                cleaned_col_names.append(f"Minimum {field.replace('_', ' ').title()}")
                            else:
                                cleaned_col_names.append(col.replace('_', ' ').title())

                        df = pd.DataFrame(results, columns=cleaned_col_names)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("No results found for this query or the query returned an empty set.")

                except sqlite3.Error as db_error:
                    st.error(f"Error executing SQL query against database: {db_error}")
                    st.warning("The generated SQL might be incorrect or incompatible with the database schema.")
                finally:
                    if conn:
                        conn.close()
            else:
                st.warning("SQL generation failed. Please try a different question or check Ollama server status.")

        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
            st.info("Please review your console for more details and ensure all prerequisites are met.")

st.markdown("---")
st.caption("Powered by Ollama (Qwen3:8B) and Streamlit. Ensure Ollama is running and `qwen3:8b` is downloaded.")