import json
import io
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

def get_drive_service():
    """st.secrets の gcp_service_account 情報を使ってDrive APIサービスを作成"""
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build('drive', 'v3', credentials=credentials)

def load_json_from_drive(filename: str, default_factory=list):
    """
    Google Drive上の指定フォルダからJSONファイルを読み込む。
    ファイルが存在しない場合は空の構造（デフォルトは [] や {}）を返す。
    """
    service = get_drive_service()
    folder_id = st.secrets["DRIVE_FOLDER_ID"]
    
    # フォルダ内の指定ファイルを検索
    query = f"'{folder_id}' in parents and name='{filename}' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])
    
    if not items:
        # ファイルが存在しない場合は初期データを返す
        return default_factory()
    
    # ファイルが存在すればダウンロードしてJSONパース
    file_id = items[0]['id']
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    
    fh.seek(0)
    try:
        return json.loads(fh.read().decode('utf-8'))
    except Exception:
        return default_factory()

def save_json_to_drive(filename: str, data):
    """
    データ(Python辞書やリスト)をJSON化し、Google Drive上の指定フォルダに上書き・新規保存する。
    """
    service = get_drive_service()
    folder_id = st.secrets["DRIVE_FOLDER_ID"]
    
    # JSON文字列に変換
    json_str = json.dumps(data, ensure_ascii=False, indent=4)
    media = MediaIoBaseUpload(io.BytesIO(json_str.encode('utf-8')), mimetype='application/json')
    
    # 既存ファイルを検索
    query = f"'{folder_id}' in parents and name='{filename}' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])
    
    if items:
        # 既存ファイルを更新
        file_id = items[0]['id']
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        # 新規ファイルを作成
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        service.files().create(body=file_metadata, media_body=media, fields='id').execute()
