import socketio
from datetime import datetime
from aiohttp import web
import aiohttp_jinja2
import jinja2
import asyncio
import copy

import itertools
import os.path
import pickle
from io import StringIO, FileIO
import json
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload
import nest_asyncio
import base64
import shutil

nest_asyncio.apply()
routes = web.RouteTableDef()

pdf_slide = []

connected_client = 0
class CustomNamespace(socketio.AsyncNamespace):
    async def on_connect(self, sid, environ):
        global connected_client
        connected_client += 1
        print('[{}] connet sid : {}'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S') , sid))
        if connected_client == 1:
            self.task = asyncio.ensure_future(self.on_connecnting())
        else:
            self.index = self.index % len(pdf_slide)
            await self.emit('event', pdf_slide[self.index].decode(), room=sid)

    async def on_broadcast_message(self, msg):
        await self.emit('event', msg.decode())

    async def on_disconnect(self, sid):
        global connected_client
        connected_client -= 1
        if not connected_client:
          self.task.cancel()

    async def on_connecnting(self):
        self.index=0
        while True:
            self.index = self.index % len(pdf_slide)
            await self.on_broadcast_message(pdf_slide[self.index])
            self.index += 1
            await asyncio.sleep(30)


async def download_pdf(app_folder_info, service):
    """
    5分間隔でPDFをGoogle Driveからダウンロードし，base64エンコードしたものを配列に格納する

    Parameters
    ----------
    app_folder_info : dict
        対象のGoogle DriveのフォルダーのID/名前
    
    service : any

    """
    global pdf_slide
    files = []
    prev_files = []
    while True:
        folder_id = app_folder_info["id"]
        query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed = false"
        results = service.files().list(
            pageSize=100,
            fields='nextPageToken, files(id, name)',
            q=query
            ).execute()
        files = results.get('files', [])
        if not files:
            print("No file found")
            prev_files = []
            shutil.rmtree("./tmp/")
            os.mkdir("./tmp/")
        if files:
            print("Found new File")
            old_files = []
            new_files = []
            if prev_files:
                file_ids = set([i["id"] for i in files])
                prev_file_ids = set([i["id"] for i in prev_files])
                new_file_ids = file_ids - prev_file_ids
                old_file_ids = prev_file_ids - file_ids
                for nf in new_file_ids:
                    new_files.append(next((f for f in files if f["id"] == nf), None))
                for of in old_file_ids:
                    old_files.append(next((f for f in prev_files if f["id"] == of), None))
            else:
                new_files = copy.deepcopy(files) 
            for f in new_files:
                request = service.files().get_media(fileId=f['id'])
                fh = FileIO('./tmp/' + f['name'], mode='w')
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
                print("Download Copmlete")
            for f in old_files:
                fname = f["name"]
                os.remove(f"./tmp/{fname}")
            prev_files = files
            pdf_slide = []
            for f in files:
                file_name = f["name"]
                with open(f"./tmp/{file_name}", "rb") as f:
                    pdf_slide.append(base64.b64encode(f.read()))
            print("All Slide Updated")
        await asyncio.sleep(300)


@aiohttp_jinja2.template('index.html')
def index(request):
    return {'': ''}


def connect_drive():
    """
    認証した後に，Google Driveに接続，情報を取得。
    """
    creds = None
    SCOPES = ["https://www.googleapis.com/auth/drive.metadata", "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive.readonly"]
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
            creds = flow.run_local_server(port=8080)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)
    app_folder_info = None
    if not os.path.exists('folder.json'):
        file_metadata = {
            'name': 'Digital-Signage',
            'mimeType': 'application/vnd.google-apps.folder'
        }
        app_folder = service.files().create(body=file_metadata, fields='id').execute()
        app_folder_id = app_folder.get('id')
        app_folder_info = {"name": "Digital-Signage", "id": app_folder_id}
        with open('folder.json', 'w') as f:
            json.dump(app_folder_info, f, indent=4)
    else:
        with open('folder.json') as f:
            app_folder_info = json.load(f)
    print("Connected")
    return app_folder_info, service
        

async def start_web():
    sio = socketio.AsyncServer(cors_allowed_origins='*', async_mode='aiohttp')
    sio.register_namespace(CustomNamespace('/'))
    app = web.Application()
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('./'))
    app.router.add_get('/', index)
    sio.attach(app)
    web.run_app(app, handle_signals=False)

async def start():
    app_folder_info, service = connect_drive()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(await asyncio.gather(download_pdf(app_folder_info, service), start_web()))

if __name__ == '__main__':
    asyncio.run(start())
