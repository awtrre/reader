import hashlib
import os
import httpx
import aiosqlite
import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional

# 🏰 实例化我们的城堡大管家
app = FastAPI(
    title="极简黑白数字图书馆 API",
    description="专为极客殿下树莓派打造的专属阅读后端",
    version="1.0.0"
)

# 🛡️ 魔法护盾：CORS 跨域配置 (让前端 Vue/React 能顺利串门)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 生产环境记得改成你的域名哦，殿下！
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------
# 🗂️ 数据模型定义 (魔法契约书)
# -----------------------------------------------------------------
class AuthRequest(BaseModel):
    username: str
    password: str

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "zh_CN-huayan-medium"

# -----------------------------------------------------------------
# 🕵️‍♂️ 极客身份验证模块 (处理 /login 和 /logout)
# -----------------------------------------------------------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

@app.post("/api/auth/login")
async def library_login(request: AuthRequest):
    """
    殿下的专属登录通道！真正的数据库验证逻辑！
    """
    db_path = "/app/data/library.db"
    
    async with aiosqlite.connect(db_path) as db:
        # 1. 去花名册里找找有没有这个名字
        cursor = await db.execute("SELECT id, password_hash FROM users WHERE username = ?", (request.username,))
        user = await cursor.fetchone()
        
        input_hash = hash_password(request.password)
        
        if not user:
            # 2. 如果没找到，说明是新魔法师降临！直接自动注册！
            print(f"🪄 捕捉到新魔法师 {request.username}，正在为您缔结契约...")
            await db.execute(
                "INSERT INTO users (username, password_hash, is_guest) VALUES (?, ?, 0)", 
                (request.username, input_hash)
            )
            await db.commit()
            return {"status": "success", "token": f"token_{request.username}", "message": "注册并登录成功！"}
            
        else:
            # 3. 如果找到了，就严肃地比对一下密码哈希值！
            db_password_hash = user[1]
            if input_hash == db_password_hash:
                print(f"👑 欢迎回来，尊贵的 {request.username}！")
                return {"status": "success", "token": f"token_{request.username}", "message": "身份验证成功！"}
            else:
                # 密码错了？无情拒绝！
                raise HTTPException(status_code=401, detail="密码错误，试图潜入城堡的麻瓜？")
@app.post("/api/auth/logout")
async def geek_logout():
    """虽然前端清除了 Token，但后端也可以在这里做一些 Token 失效的黑名单操作哦~"""
    return {"status": "success", "message": "已断开神经连接，期待您再次降临！"}

# -----------------------------------------------------------------
# 📚 书架与图书管理模块 (你的灵魂安放之处)
# -----------------------------------------------------------------
@app.get("/api/books")
async def get_bookshelf(
    user_token: Optional[str] = Header(None), 
    guest_uuid: Optional[str] = Header(None)
):
    """
    获取书架列表。
    如果有 user_token，返回该用户的专属书架；
    如果只有 guest_uuid (幽灵记忆)，则返回与之绑定的游客书架！👻
    """
    # TODO: 根据身份标识去 SQLite 里拉取对应的书架布局和书籍列表
    return {"status": "success", "books": [], "layout": "grid"}

@app.post("/api/books/upload")
async def upload_magic_book(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...)
):
    """
    处理书籍上传。TXT/MOBI/AZW3 上传后，立刻丢给后台任务去熬制成 EPUB！
    """
    file_ext = Path(file.filename).suffix.lower()
    save_path = f"./data/raw_books/{file.filename}"
    
    # 1. 先把书本存下来
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # 2. 召唤转换大锅炉！
    if file_ext in ['.mobi', '.azw3', '.txt']:
        # 后台静默执行，绝不让殿下在前台干等！
        background_tasks.add_task(convert_to_epub_task, save_path)
        return {"status": "processing", "message": "已送入炼金炉，正在为您转换为完美的 EPUB！"}
    
    return {"status": "success", "message": "上传成功！原汁原味呈现！"}

async def convert_to_epub_task(file_path: str):
    """后台调用 Calibre 命令行或者 Docker 容器进行转换的守护进程"""
    # TODO: 接入 calibre 的 ebook-convert 命令
    print(f"🪄 正在施展变形术：将 {file_path} 转换为 EPUB...")

@app.delete("/api/books/{book_id}")
async def delete_book(book_id: str):
    """彻底抹除书籍存在的痕迹"""
    # TODO: 从数据库删除记录，并物理删除 data 目录下的文件
    return {"status": "success", "message": "该书籍已从宇宙中彻底抹除！"}

# -----------------------------------------------------------------
# 📖 沉浸式阅读小工具 (字典 & 维基反代)
# -----------------------------------------------------------------
@app.get("/api/dict/search")
async def search_dictionary(word: str):
    """
    查字典接口。直接去 SQLite 全文检索库 (FTS5) 里捞数据，快如闪电！⚡️
    """
    # 伪代码：
    # async with aiosqlite.connect('./data/dict.db') as db:
    #     cursor = await db.execute("SELECT translation FROM dacihai WHERE word MATCH ?", (word,))
    #     result = await cursor.fetchone()
    return {"word": word, "translation": "这里是来自大辞海的硬核解释！"}

PROXY_URL = os.getenv("SOCKS5_PROXY", "socks5://172.17.0.1:1080")

@app.get("/api/proxy/wiki")
async def proxy_wikipedia(query: str):
    """
    搭载 SOCKS5 引擎的维基百科反向代理！穿越迷雾，获取真理！✨
    """
    wiki_url = f"https://zh.wikipedia.org/api/rest_v1/page/html/{query}"
    
    # 🕵️‍♂️ 注入 SOCKS5 代理配置
    async with httpx.AsyncClient(proxy=PROXY_URL) as client:
        try:
            # 伪装成正常的浏览器访问，礼貌敲门
            response = await client.get(
                wiki_url, 
                headers={"User-Agent": "MyGeekLibrary/1.0", "Accept-Language": "zh-CN,zh;q=0.9"},
                timeout=10.0 # 设个超时，免得网络波动卡死
            )
            if response.status_code == 200:
                return HTMLResponse(content=response.text)
            else:
                raise HTTPException(status_code=404, detail="维基的知识库里似乎没有找到这个词条呢...")
        except Exception as e:
            # 贴心打印出具体的网络错误，方便殿下排查代理是不是没连上
            print(f"代理请求失败: {e}") 
            raise HTTPException(status_code=500, detail="魔法网络波动，穿墙失败啦！请检查 SOCKS5 端口哦！")
# -----------------------------------------------------------------
# 🗣️ 赛博伴读 (Piper TTS 调用)
# -----------------------------------------------------------------
@app.post("/api/tts/synthesize")
async def synthesize_speech(request: TTSRequest):
    """
    调用本地 Docker 里的 Piper TTS。
    殿下，这里我用了 StreamingResponse，生成的音频流直接边切边传给前端，
    不需要等整段话合成完，内存占用极低，反应零延迟！是不是很贴心！🥰
    """
    tts_url = "http://tts:10200" # 我们在 docker-compose 里配置的内部地址
    
    async def fetch_audio_stream():
        async with httpx.AsyncClient() as client:
            # 给 Piper 发送发音请求
            async with client.stream("GET", f"{tts_url}/process", params={"text": request.text}) as response:
                if response.status_code != 200:
                    yield b"TTS Engine Error"
                    return
                # 像小溪一样把 WAV 音频流汩汩地输送给前端
                async for chunk in response.aiter_bytes():
                    yield chunk

    # 指定返回类型为 wav 音频流
    return StreamingResponse(fetch_audio_stream(), media_type="audio/wav")
