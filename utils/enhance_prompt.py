from utils.kwmatch import match_keywords
import pandas as pd
import re

# 辞書ファイルExcel(A列からC列のみを利用する)
df = pd.read_excel("utils/辞書データ.xlsx", usecols="A:C", converters={'Title': str, '概要': str, '詳細・経緯など': str})

def refine_query(query: str) -> str:
    """質問を辞書データを使って改善する"""
    if not query:
        return query
        
    # キーワードを抽出
    possible_kws = df['Title'].to_list()
    keywords = match_keywords(query, keyword_list=possible_kws, tokenizer_type="sudachi", mode="C")
    
    if not keywords:
        return query
        
    # 質問の後ろに補足として説明をつける
    replaced_query = query + "\n\n【以下用語の補足】\n"
    _df: pd.DataFrame = df.copy()
    _df.fillna("---", inplace=True)
    replacements = []
    
    for kw in keywords:
        definitions = _df.query("Title == @kw")['概要'].tolist()
        details = _df.query("Title == @kw")['詳細・経緯など'].tolist()
        
        update_definitions = []
        for i in range(len(definitions)):
            _def = definitions[i]
            _det = details[i]
            _def = re.sub(r"\s+", " ", _def)
            _det = re.sub(r"\s+", " ", _det)
            if _def != kw and _def != "---":
                update_definitions.append(_def)
            elif (_det != kw and _det != "---"):
                update_definitions.append(_det)
                
        if len(update_definitions) == 0:
            continue
            
        # 重複の除去
        unique_definitions = set(update_definitions)
        
        replacement_str = ", ".join(unique_definitions)
        replacement_str = f"{kw}: {replacement_str}\n"
        replacements.append((kw, replacement_str))
        
    for kw, replace in replacements:
        replaced_query = replaced_query + replace
        
    return replaced_query