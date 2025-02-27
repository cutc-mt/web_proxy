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
        CREATE TABLE IF NOT EXISTS saved_urls (
            name TEXT PRIMARY KEY,
            target_url TEXT,
            proxy_url TEXT
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
    try:
        json_data = json.dumps(data)
        print(f"Saving POST data: {name}, Data: {json_data}")  # デバッグログ
        c.execute('INSERT OR REPLACE INTO saved_post_data (name, data) VALUES (?, ?)',
                  (name, json_data))
        conn.commit()
    except Exception as e:
        print(f"Error saving POST data: {e}")  # エラーログ
        raise
    finally:
        conn.close()

def load_post_data(name):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('SELECT data FROM saved_post_data WHERE name = ?', (name,))
        result = c.fetchone()
        if result:
            data = json.loads(result[0])
            print(f"Loaded POST data for {name}: {data}")  # デバッグログ
            return data
        print(f"No data found for {name}")  # デバッグログ
        return None
    except Exception as e:
        print(f"Error loading POST data: {e}")  # エラーログ
        return None
    finally:
        conn.close()

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

def save_request(target_url, post_data, response, proxy_url=None, request_name=None):
    conn = get_db_connection()
    c = conn.cursor()

    request_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if not request_name:
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
                # 文字列として保存されているJSONデータを適切にデコード
                if isinstance(row['response'], str):
                    response = json.loads(row['response'])
                else:
                    response = row['response']

                # データポイントを文字列として結合
                data_points = response.get('data_points', [])
                if data_points:
                    data_points_str = "\n".join([f"{i+1}. {point}" for i, point in enumerate(data_points)])
                else:
                    data_points_str = ""

                return {
                    'error': response.get('error', ''),
                    'answer': response.get('answer', ''),
                    'thoughts': response.get('thoughts', ''),
                    'data_points': data_points_str
                }
            except Exception as e:
                return {
                    'error': str(row['response'])[:100] if row['response'] else '',
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

# Add new functions for URL management
def save_urls(name, target_url, proxy_url=""):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO saved_urls (name, target_url, proxy_url) VALUES (?, ?, ?)',
              (name, target_url, proxy_url))
    conn.commit()
    conn.close()

def load_urls(name):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT target_url, proxy_url FROM saved_urls WHERE name = ?', (name,))
    result = c.fetchone()
    conn.close()

    if result:
        return {"target_url": result[0], "proxy_url": result[1]}
    return None

def get_saved_url_names():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT name FROM saved_urls')
    names = [row[0] for row in c.fetchall()]
    conn.close()
    return names

def delete_urls(name):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM saved_urls WHERE name = ?', (name,))
    conn.commit()
    conn.close()

def save_last_used_urls(target_url, proxy_url=""):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
              ("last_target_url", target_url))
    c.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
              ("last_proxy_url", proxy_url))
    conn.commit()
    conn.close()

def load_last_used_urls():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT key, value FROM settings WHERE key IN ("last_target_url", "last_proxy_url")')
    results = dict(c.fetchall())
    conn.close()
    return {
        "target_url": results.get("last_target_url", ""),
        "proxy_url": results.get("last_proxy_url", "")
    }

def get_all_post_data():
    """Get all saved POST data"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT name, data FROM saved_post_data')
    results = c.fetchall()
    conn.close()

    return {row[0]: json.loads(row[1]) for row in results}

def import_post_data(import_data):
    """
    Import POST data from dictionary
    Returns tuple: (success_count, error_count)
    """
    success = 0
    errors = 0

    conn = get_db_connection()
    c = conn.cursor()

    for name, data in import_data.items():
        try:
            # Validate data structure
            if not isinstance(data, dict):
                errors += 1
                continue

            if "question" not in data or "overrides" not in data:
                errors += 1
                continue

            # Save to database
            c.execute(
                'INSERT OR REPLACE INTO saved_post_data (name, data) VALUES (?, ?)',
                (name, json.dumps(data))
            )
            success += 1

        except Exception:
            errors += 1

    conn.commit()
    conn.close()

    return success, errors

def update_request_memo(request_name, memo):
    """Update memo for a specific request"""
    conn = get_db_connection()
    c = conn.cursor()

    c.execute('''
        UPDATE requests 
        SET memo = ? 
        WHERE request_name = ?
    ''', (memo, request_name))

    conn.commit()
    conn.close()