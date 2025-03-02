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
    """基本的なデータベース関連のセッション状態を初期化する
    
    注意:
        この関数はアプリケーション起動時に一度だけ呼び出されるべきです。
        UIに関連する状態の初期化は行いません。
    """
    if "db_initialized" not in st.session_state:
        st.session_state.db_initialized = True
        st.session_state.proxy_url = ""
        st.session_state.target_url = ""

def save_post_data(name, data):
    """POSTデータを保存する
    
    Args:
        name (str): 保存するデータの名前
        data (dict): 保存するデータ
    
    Raises:
        ValueError: nameが空の場合、またはdataが不正な形式の場合
        sqlite3.Error: データベース操作に失敗した場合
    """
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
    """保存されたPOSTデータを読み込む
    
    Args:
        name (str): 読み込むデータの名前
    
    Returns:
        dict or None: 保存されたデータ。存在しない場合はNone
    
    Raises:
        ValueError: nameが空の場合
        sqlite3.Error: データベース操作に失敗した場合
    """
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
    """保存されているPOSTデータの名前リストを取得する

    Returns:
        list[str]: 保存されているデータの名前リスト

    Raises:
        sqlite3.Error: データベース操作に失敗した場合
    """
    with get_db_connection() as conn:
        c = conn.cursor()
        try:
            c.execute('SELECT name FROM saved_post_data')
            return [row[0] for row in c.fetchall()]
        except sqlite3.Error as e:
            raise sqlite3.Error(f"データ名の取得に失敗しました: {str(e)}")

def delete_post_data(name):
    """保存されたPOSTデータを削除する

    Args:
        name (str): 削除するデータの名前

    Raises:
        ValueError: nameが空または不正な形式の場合
        sqlite3.Error: データベース操作に失敗した場合
    """
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

def save_request(target_url, post_data, response, proxy_url=None, request_name=None):
    """リクエスト情報をデータベースに保存する

    Args:
        target_url (str): リクエスト先URL
        post_data (str): POSTデータ
        response (str or dict): レスポンスデータ
        proxy_url (str, optional): プロキシURL
        request_name (str, optional): リクエスト名

    Raises:
        ValueError: 必須パラメータが不正な場合
        sqlite3.Error: データベース操作に失敗した場合
    """
    if not target_url or not isinstance(target_url, str):
        raise ValueError("target_urlは必須で、文字列である必要があります")
    if not post_data or not isinstance(post_data, str):
        raise ValueError("post_dataは必須で、文字列である必要があります")

    request_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if not request_name:
        request_name = f"Request_{request_time}"

    # レスポンスの処理
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
            # POSTデータからprompt_templateを抽出
            prompt_template = ""
            try:
                post_data_dict = json.loads(post_data)
                if isinstance(post_data_dict, dict):
                    # 1. promptsキーの中のprompt_template
                    if ('prompts' in post_data_dict and
                        isinstance(post_data_dict['prompts'], dict) and
                        'prompt_template' in post_data_dict['prompts']):
                        prompt_template = str(post_data_dict['prompts']['prompt_template'])
                    # 2. トップレベルのprompt_template
                    elif 'prompt_template' in post_data_dict:
                        prompt_template = str(post_data_dict['prompt_template'])
                    # 3. overridesの中のprompt_template
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

def load_requests_summary():
    """保存されたリクエスト情報の概要を取得する

    Returns:
        pd.DataFrame: リクエスト情報を含むDataFrame

    Raises:
        sqlite3.Error: データベース操作に失敗した場合
        pd.io.sql.DatabaseError: SQLクエリの実行に失敗した場合
    """
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
            df = pd.read_sql_query(query, conn)
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
                
                question = str(data.get('question', ''))
                # SQLで抽出したprompt_templateを使用
                prompt_template = str(row['effective_prompt_template'])
                
                if question:
                    question = f"{question[:50]}..." if len(question) > 50 else question
                
                return {"question": question, "prompt_template": prompt_template}
            except json.JSONDecodeError:
                return {"question": "JSONの解析に失敗", "prompt_template": ""}
            except Exception as e:
                return {"question": f"エラー: {str(e)}", "prompt_template": ""}

        post_data_info = df.apply(lambda row: extract_post_data(row['post_data'], row), axis=1)
        df['question'] = post_data_info.apply(lambda x: x['question'])
        df['prompt_template'] = post_data_info.apply(lambda x: x['prompt_template'])

    return df

def delete_request(request_name):
    """リクエスト情報を削除する

    Args:
        request_name (str): 削除するリクエストの名前

    Raises:
        ValueError: request_nameが空または不正な形式の場合
        sqlite3.Error: データベース操作に失敗した場合
    """
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

def save_urls(name, target_url, proxy_url=""):
    """URLの組み合わせを保存する

    Args:
        name (str): 保存する名前
        target_url (str): ターゲットURL
        proxy_url (str, optional): プロキシURL

    Raises:
        ValueError: パラメータが不正な場合
        sqlite3.Error: データベース操作に失敗した場合
    """
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
    """保存されたURLの組み合わせを読み込む

    Args:
        name (str): 読み込むデータの名前

    Returns:
        dict or None: {"target_url": str, "proxy_url": str} の形式。データが存在しない場合はNone

    Raises:
        ValueError: nameが不正な場合
        sqlite3.Error: データベース操作に失敗した場合
    """
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
    """保存されているURLの名前リストを取得する

    Returns:
        list[str]: 保存されているURLの名前リスト

    Raises:
        sqlite3.Error: データベース操作に失敗した場合
    """
    with get_db_connection() as conn:
        c = conn.cursor()
        try:
            c.execute('SELECT name FROM saved_urls')
            return [row[0] for row in c.fetchall()]
        except sqlite3.Error as e:
            raise sqlite3.Error(f"URL名の取得に失敗しました: {str(e)}")

def delete_urls(name):
    """保存されたURLを削除する

    Args:
        name (str): 削除するURLの名前

    Raises:
        ValueError: nameが空または不正な形式の場合
        sqlite3.Error: データベース操作に失敗した場合
    """
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
    """最後に使用したURLを保存する

    Args:
        target_url (str): ターゲットURL
        proxy_url (str, optional): プロキシURL

    Raises:
        ValueError: パラメータが不正な場合
        sqlite3.Error: データベース操作に失敗した場合
    """
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
    """最後に使用したURLを読み込む

    Returns:
        dict: {"target_url": str, "proxy_url": str} の形式

    Raises:
        sqlite3.Error: データベース操作に失敗した場合
    """
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
    """すべての保存されたPOSTデータを取得する

    Returns:
        dict: {name: data} の形式で保存されているすべてのPOSTデータ

    Raises:
        sqlite3.Error: データベース操作に失敗した場合
        json.JSONDecodeError: 保存されているデータの形式が不正な場合
    """
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
    """POSTデータをインポートする

    Args:
        import_data (dict): インポートするデータ。{name: data} の形式。
            各dataは "question" と "overrides" キーを含むdict型である必要があります。

    Returns:
        tuple: (成功件数, 失敗件数)

    Raises:
        ValueError: import_dataが不正な形式の場合
        sqlite3.Error: データベース操作に失敗した場合
    """
    if not isinstance(import_data, dict):
        raise ValueError("import_dataはdict型である必要があります")

    success = 0
    errors = 0

    with get_db_connection() as conn:
        c = conn.cursor()
        try:
            for name, data in import_data.items():
                try:
                    # データ構造の検証
                    if not isinstance(name, str) or not name:
                        errors += 1
                        continue

                    if not isinstance(data, dict):
                        errors += 1
                        continue

                    if "question" not in data or "overrides" not in data:
                        errors += 1
                        continue

                    # データベースに保存
                    try:
                        c.execute(
                            'INSERT OR REPLACE INTO saved_post_data (name, data) VALUES (?, ?)',
                            (name, json.dumps(data))
                        )
                        success += 1
                    except (sqlite3.Error, json.JSONEncodeError):
                        errors += 1

                except Exception as e:
                    errors += 1

            conn.commit()
            return success, errors

        except sqlite3.Error as e:
            conn.rollback()
            raise sqlite3.Error(f"データのインポートに失敗しました: {str(e)}")

def update_request_memo(request_name, memo):
    """リクエストのメモを更新する

    Args:
        request_name (str): 更新するリクエストの名前
        memo (str): 設定するメモ内容

    Raises:
        ValueError: パラメータが不正な場合
        sqlite3.Error: データベース操作に失敗した場合
    """
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