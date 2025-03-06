import sqlite3
import json
import pandas as pd
from datetime import datetime
import streamlit as st

def get_db_connection():
    """データベース接続を取得し、コンテキストマネージャとして使用できるようにする"""
    return sqlite3.connect('config.db', detect_types=sqlite3.PARSE_DECLTYPES)

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

    # チャット設定プリセット用のテーブル
    c.execute('''
        CREATE TABLE IF NOT EXISTS chat_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            settings TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # チャットスレッド用のテーブル
    c.execute('''
        CREATE TABLE IF NOT EXISTS chat_threads (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # チャットメッセージ用のテーブル
    c.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            context TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (thread_id) REFERENCES chat_threads (id) ON DELETE CASCADE
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
            memo TEXT,
            prompt_template TEXT
        )
    ''')

    conn.commit()
    conn.close()

def initialize_session_state():
    """基本的なデータベース関連のセッション状態を初期化する"""
    if "db_initialized" not in st.session_state:
        st.session_state.db_initialized = True
        try:
            saved_urls = load_last_used_urls()
            st.session_state.target_url = saved_urls.get("target_url", "")
            st.session_state.proxy_url = saved_urls.get("proxy_url", "")
        except Exception as e:
            st.error(f"URL設定の読み込みに失敗しました: {str(e)}")
            st.session_state.target_url = ""
            st.session_state.proxy_url = ""

# 元の関数群を復元
def save_post_data(name, data):
    """POSTデータを保存する"""
    if not name or not isinstance(name, str):
        raise ValueError("名前は空にできません")
    if not isinstance(data, dict):
        raise ValueError("dataはdict型である必要があります")
    
    with get_db_connection() as conn:
        c = conn.cursor()
        try:
            c.execute('INSERT OR REPLACE INTO saved_post_data (name, data) VALUES (?, ?)',
                     (name, json.dumps(data)))
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise sqlite3.Error(f"データの保存に失敗しました: {str(e)}")

def load_post_data(name):
    """保存されたPOSTデータを読み込む"""
    if not name or not isinstance(name, str):
        raise ValueError("名前は空にできません")
        
    with get_db_connection() as conn:
        c = conn.cursor()
        try:
            c.execute('SELECT data FROM saved_post_data WHERE name = ?', (name,))
            result = c.fetchone()
            if result:
                return json.loads(result[0])
            return None
        except sqlite3.Error as e:
            raise sqlite3.Error(f"データの読み込みに失敗しました: {str(e)}")
        except json.JSONDecodeError as e:
            raise ValueError(f"保存されたデータの形式が不正です: {str(e)}")

def get_saved_post_data_names():
    """保存されているPOSTデータの名前リストを取得する"""
    with get_db_connection() as conn:
        c = conn.cursor()
        try:
            c.execute('SELECT name FROM saved_post_data')
            return [row[0] for row in c.fetchall()]
        except sqlite3.Error as e:
            raise sqlite3.Error(f"データ名の取得に失敗しました: {str(e)}")

def delete_post_data(name):
    """保存されたPOSTデータを削除する"""
    if not name or not isinstance(name, str):
        raise ValueError("名前は空にできません")

    with get_db_connection() as conn:
        c = conn.cursor()
        try:
            c.execute('DELETE FROM saved_post_data WHERE name = ?', (name,))
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise sqlite3.Error(f"データの削除に失敗しました: {str(e)}")

def save_urls(name, target_url, proxy_url=""):
    """URLの組み合わせを保存する"""
    if not name or not isinstance(name, str):
        raise ValueError("名前は空にできません")
    if not target_url or not isinstance(target_url, str):
        raise ValueError("target_urlは必須で、文字列である必要があります")
    if not isinstance(proxy_url, str):
        raise ValueError("proxy_urlは文字列である必要があります")

    with get_db_connection() as conn:
        c = conn.cursor()
        try:
            c.execute('INSERT OR REPLACE INTO saved_urls (name, target_url, proxy_url) VALUES (?, ?, ?)',
                     (name, target_url, proxy_url))
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise sqlite3.Error(f"URLの保存に失敗しました: {str(e)}")

def load_urls(name):
    """保存されたURLの組み合わせを読み込む"""
    if not name or not isinstance(name, str):
        raise ValueError("名前は空にできません")

    with get_db_connection() as conn:
        c = conn.cursor()
        try:
            c.execute('SELECT target_url, proxy_url FROM saved_urls WHERE name = ?', (name,))
            result = c.fetchone()
            return {"target_url": result[0], "proxy_url": result[1]} if result else None
        except sqlite3.Error as e:
            raise sqlite3.Error(f"URLの読み込みに失敗しました: {str(e)}")

def get_saved_url_names():
    """保存されているURLの名前リストを取得する"""
    with get_db_connection() as conn:
        c = conn.cursor()
        try:
            c.execute('SELECT name FROM saved_urls')
            return [row[0] for row in c.fetchall()]
        except sqlite3.Error as e:
            raise sqlite3.Error(f"URL名の取得に失敗しました: {str(e)}")

def delete_urls(name):
    """保存されたURLを削除する"""
    if not name or not isinstance(name, str):
        raise ValueError("名前は空にできません")

    with get_db_connection() as conn:
        c = conn.cursor()
        try:
            c.execute('DELETE FROM saved_urls WHERE name = ?', (name,))
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise sqlite3.Error(f"URLの削除に失敗しました: {str(e)}")

def save_last_used_urls(target_url, proxy_url=""):
    """最後に使用したURLを保存する"""
    if not target_url or not isinstance(target_url, str):
        raise ValueError("target_urlは必須で、文字列である必要があります")
    if not isinstance(proxy_url, str):
        raise ValueError("proxy_urlは文字列である必要があります")

    with get_db_connection() as conn:
        c = conn.cursor()
        try:
            c.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
                     ("last_target_url", target_url))
            c.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
                     ("last_proxy_url", proxy_url))
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise sqlite3.Error(f"最後に使用したURLの保存に失敗しました: {str(e)}")

def load_last_used_urls():
    """最後に使用したURLを読み込む"""
    with get_db_connection() as conn:
        c = conn.cursor()
        try:
            c.execute('SELECT key, value FROM settings WHERE key IN ("last_target_url", "last_proxy_url")')
            results = dict(c.fetchall())
            return {
                "target_url": results.get("last_target_url", ""),
                "proxy_url": results.get("last_proxy_url", "")
            }
        except sqlite3.Error as e:
            raise sqlite3.Error(f"最後に使用したURLの読み込みに失敗しました: {str(e)}")

def get_all_post_data():
    """すべての保存されたPOSTデータを取得する"""
    with get_db_connection() as conn:
        c = conn.cursor()
        try:
            c.execute('SELECT name, data FROM saved_post_data')
            results = c.fetchall()
            data_dict = {}
            for name, data_str in results:
                try:
                    data_dict[name] = json.loads(data_str)
                except json.JSONDecodeError as e:
                    raise json.JSONDecodeError(f"データ '{name}' のJSON形式が不正です: {str(e)}", e.doc, e.pos)
            return data_dict
        except sqlite3.Error as e:
            raise sqlite3.Error(f"データの取得に失敗しました: {str(e)}")

def import_post_data(import_data):
    """POSTデータをインポートする"""
    if not isinstance(import_data, dict):
        raise ValueError("import_dataはdict型である必要があります")

    success = 0
    errors = 0

    with get_db_connection() as conn:
        c = conn.cursor()
        try:
            for name, data in import_data.items():
                try:
                    if not isinstance(name, str) or not name:
                        errors += 1
                        continue

                    if not isinstance(data, dict):
                        errors += 1
                        continue

                    if "question" not in data or "overrides" not in data:
                        errors += 1
                        continue

                    try:
                        c.execute(
                            'INSERT OR REPLACE INTO saved_post_data (name, data) VALUES (?, ?)',
                            (name, json.dumps(data))
                        )
                        success += 1
                    except (sqlite3.Error, json.JSONEncodeError):
                        errors += 1

                except Exception:
                    errors += 1

            conn.commit()
            return success, errors

        except sqlite3.Error as e:
            conn.rollback()
            raise sqlite3.Error(f"データのインポートに失敗しました: {str(e)}")

def save_request(target_url, post_data, response, proxy_url=None, request_name=None):
    """リクエスト情報をデータベースに保存する"""
    if not target_url or not isinstance(target_url, str):
        raise ValueError("target_urlは必須で、文字列である必要があります")
    if not post_data or not isinstance(post_data, str):
        raise ValueError("post_dataは必須で、文字列である必要があります")

    request_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if not request_name:
        request_name = f"Request_{request_time}"

    try:
        if isinstance(response, str):
            response_dict = json.loads(response)
        elif isinstance(response, dict):
            response_dict = response
        else:
            raise ValueError("responseは文字列またはdict型である必要があります")
        
        status_code = response_dict.get('status_code', 0)
        response_str = json.dumps(response_dict)
    except json.JSONDecodeError as e:
        raise ValueError(f"responseのJSON形式が不正です: {str(e)}")
    except Exception as e:
        raise ValueError(f"responseの処理中にエラーが発生しました: {str(e)}")

    with get_db_connection() as conn:
        c = conn.cursor()
        try:
            prompt_template = ""
            try:
                post_data_dict = json.loads(post_data)
                if isinstance(post_data_dict, dict):
                    if ('prompts' in post_data_dict and
                        isinstance(post_data_dict['prompts'], dict) and
                        'prompt_template' in post_data_dict['prompts']):
                        prompt_template = str(post_data_dict['prompts']['prompt_template'])
                    elif 'prompt_template' in post_data_dict:
                        prompt_template = str(post_data_dict['prompt_template'])
                    elif ('overrides' in post_data_dict and
                          isinstance(post_data_dict['overrides'], dict) and
                          'prompt_template' in post_data_dict['overrides']):
                        prompt_template = str(post_data_dict['overrides']['prompt_template'])
            except (json.JSONDecodeError, AttributeError) as e:
                st.error(f"prompt_templateの抽出中にエラーが発生しました: {str(e)}")

            c.execute('''
                INSERT INTO requests
                (request_time, request_name, url, proxy_url, post_data, response, status_code, prompt_template)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (request_time, request_name, target_url, proxy_url, post_data, response_str, status_code, prompt_template))
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise sqlite3.Error(f"リクエスト情報の保存に失敗しました: {str(e)}")

# 新しい関数群

def save_chat_settings(name, settings):
    """チャット設定をプリセットとして保存"""
    if not name or not isinstance(name, str):
        raise ValueError("nameは空にできません")
    if not isinstance(settings, dict):
        raise ValueError("settingsはdict型である必要があります")

    with get_db_connection() as conn:
        c = conn.cursor()
        try:
            c.execute('''
                INSERT OR REPLACE INTO chat_settings (name, settings, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (name, json.dumps(settings)))
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise sqlite3.Error(f"チャット設定の保存に失敗しました: {str(e)}")

def load_chat_settings(name):
    """保存されたチャット設定を読み込む"""
    if not name or not isinstance(name, str):
        raise ValueError("nameは空にできません")

    with get_db_connection() as conn:
        c = conn.cursor()
        try:
            c.execute('SELECT settings FROM chat_settings WHERE name = ?', (name,))
            result = c.fetchone()
            return json.loads(result[0]) if result else None
        except sqlite3.Error as e:
            raise sqlite3.Error(f"チャット設定の読み込みに失敗しました: {str(e)}")

def get_chat_settings_list():
    """保存されているチャット設定プリセットの一覧を取得"""
    with get_db_connection() as conn:
        c = conn.cursor()
        try:
            c.execute('SELECT name, created_at, updated_at FROM chat_settings ORDER BY updated_at DESC')
            return [{"name": row[0], "created_at": row[1], "updated_at": row[2]} for row in c.fetchall()]
        except sqlite3.Error as e:
            raise sqlite3.Error(f"チャット設定一覧の取得に失敗しました: {str(e)}")

def save_chat_thread(thread_id, name):
    """チャットスレッドを保存または更新"""
    if not thread_id or not isinstance(thread_id, str):
        raise ValueError("thread_idは空にできません")
    if not name or not isinstance(name, str):
        raise ValueError("nameは空にできません")

    with get_db_connection() as conn:
        c = conn.cursor()
        try:
            c.execute('''
                INSERT OR REPLACE INTO chat_threads (id, name, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (thread_id, name))
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise sqlite3.Error(f"チャットスレッドの保存に失敗しました: {str(e)}")

def save_chat_message(thread_id, role, content, context=None):
    """チャットメッセージを保存"""
    if not thread_id or not isinstance(thread_id, str):
        raise ValueError("thread_idは空にできません")
    if not role or role not in ["user", "assistant"]:
        raise ValueError("roleは'user'または'assistant'である必要があります")
    if not content or not isinstance(content, str):
        raise ValueError("contentは空にできません")

    with get_db_connection() as conn:
        c = conn.cursor()
        try:
            context_json = json.dumps(context) if context else None
            c.execute('''
                INSERT INTO chat_messages (thread_id, role, content, context)
                VALUES (?, ?, ?, ?)
            ''', (thread_id, role, content, context_json))
            
            # スレッドの更新時刻を更新
            c.execute('''
                UPDATE chat_threads
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (thread_id,))
            
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise sqlite3.Error(f"チャットメッセージの保存に失敗しました: {str(e)}")

def load_chat_threads():
    """保存されているチャットスレッド一覧を取得"""
    with get_db_connection() as conn:
        c = conn.cursor()
        try:
            c.execute('''
                SELECT id, name, created_at, updated_at
                FROM chat_threads
                ORDER BY updated_at DESC
            ''')
            return [{
                "id": row[0],
                "name": row[1],
                "created_at": row[2].strftime('%Y-%m-%d %H:%M:%S') if row[2] else None,
                "updated_at": row[3].strftime('%Y-%m-%d %H:%M:%S') if row[3] else None
            } for row in c.fetchall()]
        except sqlite3.Error as e:
            raise sqlite3.Error(f"チャットスレッド一覧の取得に失敗しました: {str(e)}")

def load_chat_messages(thread_id):
    """指定されたスレッドのメッセージ履歴を取得"""
    if not thread_id or not isinstance(thread_id, str):
        raise ValueError("thread_idは空にできません")

    with get_db_connection() as conn:
        c = conn.cursor()
        try:
            c.execute('''
                SELECT role, content, context, created_at
                FROM chat_messages
                WHERE thread_id = ?
                ORDER BY created_at ASC
            ''', (thread_id,))
            return [{
                "role": row[0],
                "content": row[1],
                "context": json.loads(row[2]) if row[2] else None,
                "created_at": row[3].strftime('%Y-%m-%d %H:%M:%S') if row[3] else None
            } for row in c.fetchall()]
        except sqlite3.Error as e:
            raise sqlite3.Error(f"チャットメッセージの取得に失敗しました: {str(e)}")

def delete_chat_thread(thread_id):
    """チャットスレッドとそれに関連するメッセージを削除"""
    if not thread_id or not isinstance(thread_id, str):
        raise ValueError("thread_idは空にできません")

    with get_db_connection() as conn:
        c = conn.cursor()
        try:
            c.execute('DELETE FROM chat_threads WHERE id = ?', (thread_id,))
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise sqlite3.Error(f"チャットスレッドの削除に失敗しました: {str(e)}")

def load_requests_summary():
    """保存されたリクエスト情報の概要を取得する"""
    query = '''
        SELECT
            request_time,
            request_name,
            url,
            status_code,
            post_data,
            response,
            memo,
            prompt_template,
            COALESCE(
                prompt_template,
                json_extract(post_data, '$.prompts.prompt_template'),
                json_extract(post_data, '$.prompt_template'),
                json_extract(post_data, '$.overrides.prompt_template'),
                ''
            ) as effective_prompt_template
        FROM requests
        ORDER BY request_time DESC
    '''

    with get_db_connection() as conn:
        try:
            df = pd.read_sql_query(query, conn, parse_dates=['request_time'])
        except (sqlite3.Error, pd.io.sql.DatabaseError) as e:
            raise sqlite3.Error(f"リクエスト情報の読み込みに失敗しました: {str(e)}")

    if not df.empty:
        # レスポンスカラムの処理
        def extract_response_data(row):
            """レスポンスデータから必要な情報を抽出する"""
            try:
                # レスポンスデータの解析
                if isinstance(row['response'], str):
                    try:
                        response = json.loads(row['response'])
                    except json.JSONDecodeError:
                        return {
                            'error': 'JSONの解析に失敗しました',
                            'answer': '',
                            'thoughts': '',
                            'data_points': ''
                        }
                elif isinstance(row['response'], dict):
                    response = row['response']
                else:
                    return {
                        'error': '不正なレスポンス形式です',
                        'answer': '',
                        'thoughts': '',
                        'data_points': ''
                    }

                # データポイントの処理
                try:
                    data_points = response.get('data_points', [])
                    if not isinstance(data_points, list):
                        data_points = []
                    data_points_str = "\n=========================\n".join([f"{i+1}. {point}" for i, point in enumerate(data_points)])
                except Exception:
                    data_points_str = ""

                return {
                    'error': str(response.get('error', '')),
                    'answer': str(response.get('answer', '')),
                    'thoughts': str(response.get('thoughts', '')),
                    'data_points': data_points_str
                }
            except Exception as e:
                return {
                    'error': f"データの処理中にエラーが発生しました: {str(e)}",
                    'answer': '',
                    'thoughts': '',
                    'data_points': ''
                }

        # レスポンスデータの処理
        response_data = df.apply(extract_response_data, axis=1)
        for key in ['error', 'answer', 'thoughts', 'data_points']:
            df[key] = response_data.apply(lambda x: x.get(key, ''))

        # POSTデータからquestionとprompt_templateを抽出
        def extract_post_data(post_data, row):
            """POSTデータから必要な情報を抽出する"""
            try:
                if not isinstance(post_data, str):
                    return {"question": "不正なPOSTデータ", "prompt_template": ""}
                    
                data = json.loads(post_data)
                if not isinstance(data, dict):
                    return {"question": "不正なPOSTデータ形式", "prompt_template": ""}
                
                # 質問とプロンプトテンプレートを取得
                question = str(data.get('question', ''))
                prompt_template = str(row['effective_prompt_template'])
                
                return {"question": question, "prompt_template": prompt_template}
            except json.JSONDecodeError:
                return {"question": "JSONの解析に失敗", "prompt_template": ""}
            except Exception as e:
                return {"question": f"エラー: {str(e)}", "prompt_template": ""}

        post_data_info = df.apply(lambda row: extract_post_data(row['post_data'], row), axis=1)
        df['question'] = post_data_info.apply(lambda x: x['question'])
        df['prompt_template'] = post_data_info.apply(lambda x: x['prompt_template'])

    return df

def update_request_memo(request_name, memo):
    """リクエストのメモを更新する"""
    if not request_name or not isinstance(request_name, str):
        raise ValueError("request_nameは空にできません")
    if not isinstance(memo, str):
        raise ValueError("memoは文字列である必要があります")

    with get_db_connection() as conn:
        c = conn.cursor()
        try:
            c.execute('''
                UPDATE requests
                SET memo = ?
                WHERE request_name = ?
            ''', (memo, request_name))
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise sqlite3.Error(f"メモの更新に失敗しました: {str(e)}")

def delete_request(request_name):
    """リクエスト情報を削除する"""
    if not request_name or not isinstance(request_name, str):
        raise ValueError("request_nameは空にできません")

    with get_db_connection() as conn:
        c = conn.cursor()
        try:
            c.execute('DELETE FROM requests WHERE request_name = ?', (request_name,))
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise sqlite3.Error(f"リクエストの削除に失敗しました: {str(e)}")