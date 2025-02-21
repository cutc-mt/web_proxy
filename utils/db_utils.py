import sqlite3
import json
import pandas as pd
from datetime import datetime
import streamlit as st

def get_db_connection():
    return sqlite3.connect('config.db')

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Create tables
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS saved_post_data (
            name TEXT PRIMARY KEY,
            data TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_time TIMESTAMP,
            request_name TEXT,
            url TEXT,
            proxy_url TEXT,
            post_data TEXT,
            response TEXT,
            status_code INTEGER,
            memo TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def initialize_session_state():
    defaults = {
        "proxy_url": "",
        "target_url": "",
        "question": "",
        "retrieval_mode": "hybrid",
        "semantic_ranker": False,
        "semantic_captions": False,
        "top": 3,
        "temperature": 0.3,
        "prompt_template": "",
        "exclude_category": "",
        "selected_data": "",
        "save_name": ""
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def save_post_data(name, data):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO saved_post_data (name, data) VALUES (?, ?)',
              (name, json.dumps(data)))
    conn.commit()
    conn.close()

def load_post_data(name):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT data FROM saved_post_data WHERE name = ?', (name,))
    result = c.fetchone()
    conn.close()
    
    if result:
        return json.loads(result[0])
    return None

def get_saved_post_data_names():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT name FROM saved_post_data')
    names = [row[0] for row in c.fetchall()]
    conn.close()
    return names

def delete_post_data(name):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM saved_post_data WHERE name = ?', (name,))
    conn.commit()
    conn.close()

def save_request(target_url, post_data, response, proxy_url=None):
    conn = get_db_connection()
    c = conn.cursor()
    
    request_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    request_name = f"Request_{request_time}"
    
    try:
        response_dict = json.loads(response) if isinstance(response, str) else response
        status_code = response_dict.get('status_code', 0)
    except:
        status_code = 0
    
    c.execute('''
        INSERT INTO requests 
        (request_time, request_name, url, proxy_url, post_data, response, status_code)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (request_time, request_name, target_url, proxy_url, post_data, response, status_code))
    
    conn.commit()
    conn.close()

def load_requests_summary():
    conn = get_db_connection()
    
    query = '''
        SELECT 
            request_time,
            request_name,
            url,
            status_code,
            post_data,
            response,
            memo
        FROM requests
        ORDER BY request_time DESC
    '''
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if not df.empty:
        # Process response column
        def extract_response_data(row):
            try:
                response = json.loads(row['response'])
                return {
                    'error': response.get('error', ''),
                    'answer': response.get('answer', ''),
                    'thoughts': response.get('thoughts', ''),
                    'data_points': json.dumps(response.get('data_points', []))
                }
            except:
                return {
                    'error': str(row['response'])[:100],
                    'answer': '',
                    'thoughts': '',
                    'data_points': ''
                }
        
        response_data = df.apply(extract_response_data, axis=1)
        for key in ['error', 'answer', 'thoughts', 'data_points']:
            df[key] = response_data.apply(lambda x: x[key])
        
        # Create post_data preview
        df['post_data_preview'] = df['post_data'].apply(
            lambda x: json.loads(x)['question'][:50] + '...' if len(json.loads(x)['question']) > 50 else json.loads(x)['question']
        )
    
    return df

def delete_request(request_name):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM requests WHERE request_name = ?', (request_name,))
    conn.commit()
    conn.close()
