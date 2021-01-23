import socketio
from datetime import datetime
from aiohttp import web
import aiohttp_jinja2
import jinja2
import asyncio

import itertools
import os
from os.path import join, dirname
import pickle
from io import StringIO, FileIO
import json
import nest_asyncio
import base64
import dropbox
import shutil
from dotenv import load_dotenv

load_dotenv(verbose=True)
dotenv_path = join(dirname(__file__), ".env")
load_dotenv(dotenv_path)
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")

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


async def download_pdf(dbx):
    global pdf_slide
    prev_files = []
    while True:
        files=[]
        res = dbx.files_list_folder('')
        for entry in res.entries:
            if entry.path_lower.endswith(".pdf"):
                files.append(entry.path_display)
        
        if len(files) == 0:
            prev_files = []
            shutil.rmtree("./tmp/")
            os.mkdir("./tmp/")
            with open(f"./default.pdf", "rb") as f:
                pdf_slide = [base64.b64encode(f.read())]
        else:
            remove_queue = set(prev_files) - set(files)
            download_queue = set(files) - set(prev_files)
            tmp_path = join(dirname(__file__), "tmp")
            for f in download_queue:
                dbx.files_download_to_file(tmp_path + f, f)

            for f in remove_queue:
                os.remove(tmp_path + f)  
            prev_files = files
            pdf_slide=[]
            for file_name in files:
                with open(f"./tmp/{file_name}", "rb") as f:
                    pdf_slide.append(base64.b64encode(f.read()))
        await asyncio.sleep(10)


@aiohttp_jinja2.template('index.html')
def index(request):
    return {'': ''}


def connect_dropbox():
    dbx = dropbox.Dropbox(ACCESS_TOKEN)
    return dbx


async def start_web():
    sio = socketio.AsyncServer(cors_allowed_origins='*', async_mode='aiohttp')
    sio.register_namespace(CustomNamespace('/'))
    app = web.Application()
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('./'))
    app.router.add_get('/', index)
    sio.attach(app)
    web.run_app(app, handle_signals=False)


async def start():
    dbx = connect_dropbox()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(await asyncio.gather(download_pdf(dbx), start_web()))

if __name__ == '__main__':
    asyncio.run(start())
