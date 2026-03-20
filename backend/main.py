from contextlib import asynccontextmanager
from database import init_db 
import uuid
import hashlib
import os
import httpx
import aiosqlite
import shutil
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional
# 🪄 城堡启动与关闭的生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🪄 正在唤醒记忆水晶，构建数字城堡的藏书阁...")
    # 启动时执行建表逻辑
    await init_db()
    yield
    # 关闭时的清理逻辑（暂时留空即可）
    print("🏰 数字城堡进入休眠状态...")

# 🏰 实例化我们的城堡大管家 (修改这里，把 lifespan 挂载上去)
app = FastAPI(
    title="极简黑白数字图书馆 API",
    description="专为极客殿下树莓派打造的专属阅读后端",
    version="1.0.0",
    lifespan=lifespan  # <-- 重点加这一行！
)
# 🛡️ 魔法护盾：CORS 跨域配置 (让前端 Vue/React 能顺利串门)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 生产环境记得改成你的域名哦，殿下！
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 挂载 data 目录，让前端可以直接通过 /api/static/xxx 访问封面和书籍
app.mount("/api/static", StaticFiles(directory="/app/data"), name="static")

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
            # 🌟 核心修改：直接返回 username 作为 token
            return {"status": "success", "token": request.username, "message": "注册并登录成功！"}
            
        else:
            # 3. 如果找到了，就严肃地比对一下密码哈希值！
            db_password_hash = user[1]
            if input_hash == db_password_hash:
                print(f"👑 欢迎回来，尊贵的 {request.username}！")
                # 🌟 核心修改：同样直接返回 username
                return {"status": "success", "token": request.username, "message": "身份验证成功！"}
            else:
                # 密码错了？无情拒绝！
                raise HTTPException(status_code=401, detail="密码错误，试图潜入城堡的麻瓜？")
@app.post("/api/auth/logout")
async def geek_logout():
    """虽然前端清除了 Token，但后端也可以在这里做一些 Token 失效的黑名单操作哦~"""
    return {"status": "success", "message": "已断开神经连接，期待您再次降临！"}
# -----------------------------------------------------------------
# 🔖 书籍进度管理 (解决问题 1 & 2)
# -----------------------------------------------------------------
# 获取进度接口
@app.get("/api/books/{book_id}/progress")
async def get_progress(
    book_id: str, 
    user_token: Optional[str] = Header(None), 
    guest_uuid: Optional[str] = Header(None)
):
    from database import DB_PATH
    async with aiosqlite.connect(DB_PATH) as db:
        # 🕵️‍♂️ 第一步：识别此人是谁（游客还是正式用户）
        user_id = await get_current_user_id(db, user_token, guest_uuid)
        
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT current_cfi FROM user_books WHERE user_id = ? AND book_id = ?", 
            (user_id, book_id)
        )
        res = await cursor.fetchone()
        return {"cfi": res["current_cfi"] if res else None}

# 保存进度接口
@app.post("/api/books/{book_id}/progress")
async def save_progress(
    book_id: str, 
    payload: dict, 
    user_token: Optional[str] = Header(None), 
    guest_uuid: Optional[str] = Header(None)
):
    from database import update_reading_progress, DB_PATH
    
    # 🕵️‍♂️ 识别身份
    async with aiosqlite.connect(DB_PATH) as db:
        user_id = await get_current_user_id(db, user_token, guest_uuid)
    
    cfi = payload.get("cfi")
    percent = payload.get("percent", 0)
    
    # 将识别出的真实 user_id 传给数据库操作函数
    await update_reading_progress(user_id, book_id, cfi, percent)
    return {"status": "success"}
# -----------------------------------------------------------------
# 📚 书架与图书管理模块 (你的灵魂安放之处)
# -----------------------------------------------------------------
# --- 请将此函数添加到 @app.get("/api/books") 上方 ---
async def get_current_user_id(db, user_token: str, guest_uuid: str) -> int:
    """🕵️‍♂️ 身份识别：根据 Token 或访客 UUID 获取/创建内部 user_id"""
    # 1. 确定当前使用的身份标识
    token_to_use = user_token if user_token else guest_uuid
    
    # 🛡️ 安全检查：如果前端两个头都没传，给一个兜底标识，防止程序崩溃
    if not token_to_use:
        token_to_use = "anonymous_stranger"

    is_guest = 0 if user_token else 1
    
    # 2. 尝试寻找老面孔
    cursor = await db.execute("SELECT id FROM users WHERE username = ?", (token_to_use,))
    user = await cursor.fetchone()
    
    if user:
        return user[0]
    else:
        # 3. 既然是新面孔，直接缔结契约
        # 使用 INSERT OR IGNORE 防止并发冲突
        cursor = await db.execute(
            "INSERT OR IGNORE INTO users (username, is_guest) VALUES (?, ?)", 
            (token_to_use, is_guest)
        )
        await db.commit()
        
        # 4. 🌟 关键修复：直接获取最后一次插入行的 ID
        if cursor.lastrowid:
            return cursor.lastrowid
        
        # 5. 万一 INSERT 被 IGNORE 了（说明正好有人同时创建），再最后捞一次
        cursor = await db.execute("SELECT id FROM users WHERE username = ?", (token_to_use,))
        user = await cursor.fetchone()
        return user[0] if user else 1 # 实在不行回滚到 1 号用户

@app.get("/api/books")
async def get_bookshelf(
    user_token: Optional[str] = Header(None),
    guest_uuid: Optional[str] = Header(None)
):
    """获取当前用户的专属书架 [cite: 4]"""
    db_path = "/app/data/library.db"
    books = []
    
    try:
        async with aiosqlite.connect(db_path) as db:
            # 1. 获取用户 ID
            user_id = await get_current_user_id(db, user_token, guest_uuid)
            
            # 2. 联合查询用户关联的书籍
            cursor = await db.execute("""
                SELECT b.id, b.title, b.author, b.format, ub.progress_percentage 
                FROM books b 
                INNER JOIN user_books ub ON b.id = ub.book_id 
                WHERE ub.user_id = ? 
                ORDER BY ub.last_read_at DESC
            """, (user_id,))
            rows = await cursor.fetchall()
            
            for row in rows:
                books.append({
                    "id": row[0],
                    "title": row[1],
                    "author": row[2] or "佚名",
                    "format": row[3],
                    "progress": row[4],
                    "is_owned": True
                })
        
        # 🌟 这里的 return 必须和上方的 async with 垂直对齐（8个空格）
        return {"status": "success", "books": books, "layout": "grid"}
        
    except Exception as e:
        print(f"💥 数据库读取异常: {e}")
        return {"status": "error", "books": []}
@app.post("/api/books/upload")
async def upload_magic_book(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_token: Optional[str] = Header(None),
    guest_uuid: Optional[str] = Header(None)
):
    """处理书籍上传，并真正将其写入记忆中枢！"""
    file_ext = Path(file.filename).suffix.lower()
    book_id = str(uuid.uuid4()) # 生成唯一的魔法编号
    
    # 为了防止同名文件冲突，保存时加上 ID
    save_filename = f"{book_id}{file_ext}"
    title = Path(file.filename).stem

    # 💡 核心修复：智能分流传送阵
    if file_ext == '.epub':
        # 已经是完美的 epub，直接送入藏书阁
        target_dir = "/app/data/books"
        format_type = "epub"
    else:
        # 其他格式，先扔进原料库准备炼金转换
        target_dir = "/app/data/raw_books"
        format_type = file_ext.replace('.', '')

    # 🛡️ 加一层护盾：确保目录存在，防止 500 报错
    os.makedirs(target_dir, exist_ok=True)
    
    save_path = f"{target_dir}/{save_filename}"

    # 1. 物理保存文件
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 2. 写入数据库！
    db_path = "/app/data/library.db"
    async with aiosqlite.connect(db_path) as db:
        # 第一步：先往藏书阁（books）存入书籍基本信息 [cite: 5]
        await db.execute(
            "INSERT INTO books (id, title, file_path, format) VALUES (?, ?, ?, ?)",
            (book_id, title, save_path, format_type)
        )
        
        # 第二步：获取当前用户的 ID (无论是正式用户还是幽灵游客) 
        user_id = await get_current_user_id(db, user_token, guest_uuid)
        
        # 第三步：在灵魂羁绊表（user_books）中建立关联 [cite: 5]
        await db.execute(
            "INSERT INTO user_books (user_id, book_id) VALUES (?, ?)",
            (user_id, book_id)
        )
        
        # 统一提交，确保两步操作要么都成功，要么都失败（原子性） 
        await db.commit()
    # 3. 召唤转换大锅炉 (如果需要转换)
    if file_ext in ['.mobi', '.azw3', '.txt', '.pdf']:
        # TODO: 这里需要确保 convert_to_epub_task 转换完成后，
        # 把新生成的 epub 移动到 /app/data/books/，并更新数据库的 file_path！
        background_tasks.add_task(convert_to_epub_task, save_path, book_id)
        return {"status": "processing", "message": "已入库！正在后台转为 EPUB..."}

    return {"status": "success", "message": "上传成功！原汁原味呈现！"}

@app.delete("/api/books/{book_id}")
async def delete_book(
    book_id: str,
    user_token: Optional[str] = Header(None),
    guest_uuid: Optional[str] = Header(None)
):
    """彻底抹除书籍存在的痕迹（包含数据库记录和物理文件）"""
    db_path = "/app/data/library.db"
    
    try:
        async with aiosqlite.connect(db_path) as db:
            # 1. 验证身份，获取对应的 user_id
            user_id = await get_current_user_id(db, user_token, guest_uuid)

            # 2. 在删除记录前，先查出文件的物理路径
            cursor = await db.execute("SELECT file_path FROM books WHERE id = ?", (book_id,))
            book_record = await cursor.fetchone()

            if book_record:
                file_path = book_record[0]
                # 3. 物理删除文件 (使用 os.path.exists 增加安全判定，防止文件不存在导致报错)
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"🗑️ 物理文件已粉碎: {file_path}")

            # 4. 解除灵魂羁绊：从 user_books 表中删除用户的阅读记录和关联
            await db.execute("DELETE FROM user_books WHERE user_id = ? AND book_id = ?", (user_id, book_id))
            
            # 5. 摧毁本体：从 books 表中彻底删除书籍信息
            await db.execute("DELETE FROM books WHERE id = ?", (book_id,))

            # 统一提交魔法契约
            await db.commit()

        return {"status": "success", "message": "该书籍已从宇宙中彻底抹除！"}
        
    except Exception as e:
        print(f"💥 删除魔法失败: {e}")
        raise HTTPException(status_code=500, detail="删除失败，残余魔法能量干扰！")
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
