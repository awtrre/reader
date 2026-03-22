import docker
import zipfile 
import shutil
import asyncio
from pathlib import Path
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
# 🛠️ 炼金工坊核心工具：EPUB 爆破术
# -----------------------------------------------------------------
def _sync_extract_epub(source_path: str, target_dir: str, remove_source: bool = True):
    """
    同步解压逻辑：将 EPUB 文件解压为网页文件夹。
    如果解压失败会自动清理残留文件。
    """
    os.makedirs(target_dir, exist_ok=True)
    try:
        with zipfile.ZipFile(source_path, 'r') as zip_ref:
            zip_ref.extractall(target_dir)
        
        if remove_source and os.path.exists(source_path):
            os.remove(source_path) # 阅后即焚
            
    except Exception as e:
        print(f"💥 爆破解压失败: {e}")
        # 如果解压到一半报错，为了防止产生脏数据，把生成的残缺文件夹直接抹除
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        raise Exception(f"魔法书结构损坏: {str(e)}")

async def extract_epub_to_folder(source_path: str, book_id: str, remove_source: bool = True) -> str:
    """
    异步包装器：防止树莓派 CPU 解压时阻塞其他用户的网络请求
    返回解压后的最终文件夹路径
    """
    target_dir = f"/app/data/books/{book_id}"
    
    # 将同步的解压 I/O 任务推入后台线程池执行
    await asyncio.to_thread(_sync_extract_epub, source_path, target_dir, remove_source)
    
    return target_dir
async def convert_to_epub_task(source_file_path: str, book_id: str):
    """
    后台炼金炉：指挥 Calibre 容器将 TXT/MOBI/AZW3 转为 EPUB，随后自动爆破。
    """
    print(f"🔥 正在召唤 Calibre 炼金炉处理: {source_file_path}")
    
    # 转换后生成的临时 EPUB 路径
    calibre_output_epub = f"/app/data/raw_books/converted_{book_id}.epub"
    
    def run_calibre():
        # 通过宿主机的 docker.sock 连接容器引擎
        client = docker.from_env()
        try:
            # 找到我们在 docker-compose 里命名的 calibre 容器
            calibre_container = client.containers.get('library_calibre')
            
            # 组装转换命令：ebook-convert <输入路径> <输出路径>
            cmd = ["ebook-convert", source_file_path, calibre_output_epub]
            
            # 在 Calibre 容器内部执行转换
            exit_code, output = calibre_container.exec_run(cmd)
            
            if exit_code != 0:
                raise Exception(f"Calibre 转换失败: {output.decode('utf-8', errors='ignore')}")
            return True
        except Exception as e:
            raise Exception(f"跨容器调用失败: {str(e)}")

    try:
        # 1. 执行耗时的转换操作（放入线程池，不阻塞其他用户）
        await asyncio.to_thread(run_calibre)
        
        # 2. 转换成功后，立即调用“爆破术”将其变为静态文件夹 [cite: 5]
        # remove_source=True 会在解压后删除转换出的那个临时 .epub 文件
        final_dir = await extract_epub_to_folder(calibre_output_epub, book_id, remove_source=True)
        
        # 3. 炼金完成，更新记忆水晶（数据库）中的路径和格式 [cite: 5]
        from database import DB_PATH
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE books SET format = 'epub', file_path = ? WHERE id = ?",
                (final_dir, book_id)
            )
            await db.commit()
            
        # 4. 扫尾工作：删除最原始的上传文件（如 .txt 或 .mobi）以节省空间 [cite: 5]
        if os.path.exists(source_file_path):
            os.remove(source_file_path)
            
        print(f"✨ 炼金成功！书籍 {book_id} 已解压完毕，可供秒开。")

    except Exception as e:
        print(f"💥 炼金炉故障: {e}")
        # 如果彻底失败，建议从数据库中抹除该书，防止书架出现永远无法打开的“死书” [cite: 5]
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM user_books WHERE book_id = ?", (book_id,))
            await db.execute("DELETE FROM books WHERE id = ?", (book_id,))
            await db.commit()
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
    from database import DB_PATH
    
    async with aiosqlite.connect(DB_PATH) as db:
        # 1. 识别当前发来请求的究竟是谁（此时可能是被别的标签页修改后的新账号）
        user_id = await get_current_user_id(db, user_token, guest_uuid)
        
        # 🛡️ 2. 核心修复：灵魂绑定锁！检查当前用户是否真的拥有这本书！
        cursor = await db.execute(
            "SELECT 1 FROM user_books WHERE user_id = ? AND book_id = ?", 
            (user_id, book_id)
        )
        is_owner = await cursor.fetchone()
        
        if not is_owner:
            # 🚨 如果当前账号没有这本书（说明发生了串号），绝对不能静默转移书籍！直接拒绝！
            # 这样就不会把【账号1】的书强行塞给【账号2】了
            raise HTTPException(status_code=403, detail="账号状态已变更，拒绝越权保存进度！")

        # 3. 如果校验通过，提取进度
        cfi = payload.get("cfi")
        percent = payload.get("percent", 0)
        
        # 🔒 4. 绝对安全的更新逻辑：严格限定只更新当前 user_id 和 book_id 的记录
        await db.execute(
            """
            UPDATE user_books 
            SET current_cfi = ?, progress_percentage = ?
            WHERE user_id = ? AND book_id = ?
            """,
            (cfi, percent, user_id, book_id)
        )
        await db.commit()
        
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
    """获取当前用户的专属书架"""
    db_path = "/app/data/library.db"
    books = []
    
    try:
        async with aiosqlite.connect(db_path) as db:
            user_id = await get_current_user_id(db, user_token, guest_uuid)
            
            # ✨ 核心修复：把 uploader_id 和 is_public 一起从数据库里查出来
            cursor = await db.execute("""
                SELECT b.id, b.title, b.author, b.format, ub.progress_percentage, b.uploader_id, b.is_public 
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
                    "is_uploader": row[5] == user_id,  # ✨ 告诉前端：这本书是不是我传的
                    "is_public": bool(row[6]),         # ✨ 告诉前端：这本书现在的状态
                    "is_owned": True
                })
        
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
    """重构版：支持直接爆破 EPUB 或后台异步转换其他格式"""
    file_ext = Path(file.filename).suffix.lower()
    book_id = str(uuid.uuid4())
    save_filename = f"{book_id}{file_ext}"
    title = Path(file.filename).stem

    # 1. 统一先存入 raw_books 缓冲区
    raw_dir = "/app/data/raw_books"
    os.makedirs(raw_dir, exist_ok=True)
    temp_path = f"{raw_dir}/{save_filename}"
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 2. 准备路径和格式
    format_type = file_ext.replace('.', '')
    db_save_path = temp_path # 默认先存原始路径
    
    # 3. 数据库预登记
    db_path = "/app/data/library.db"
    async with aiosqlite.connect(db_path) as db:
        user_id = await get_current_user_id(db, user_token, guest_uuid)
        cursor = await db.execute("SELECT is_guest FROM users WHERE id = ?", (user_id,))
        user_info = await cursor.fetchone()
        is_public = 1 if (user_info and user_info[0]) else 0

        await db.execute(
            "INSERT INTO books (id, title, file_path, format, uploader_id, is_public) VALUES (?, ?, ?, ?, ?, ?)",
            (book_id, title, db_save_path, format_type, user_id, is_public)
        )
        await db.execute(
            "INSERT INTO user_books (user_id, book_id) VALUES (?, ?)",
            (user_id, book_id)
        )
        await db.commit()

    # 4. 根据格式决定处理策略
    if file_ext == '.epub':
        # 如果是 EPUB，直接在主进程/线程爆破，用户可以立即读
        final_path = await extract_epub_to_folder(temp_path, book_id, remove_source=True)
        # 更新数据库为解压后的路径
        async with aiosqlite.connect(db_path) as db:
            await db.execute("UPDATE books SET file_path = ? WHERE id = ?", (final_path, book_id))
            await db.commit()
        return {"status": "success", "message": "EPUB 已就绪，秒开已激活！"}
    
    elif file_ext in ['.mobi', '.azw3', '.txt', '.pdf']:
        # 如果需要转换，丢进后台，让 Calibre 慢慢炼制
        background_tasks.add_task(convert_to_epub_task, temp_path, book_id)
        return {"status": "processing", "message": "非 EPUB 格式，后台炼金炉正在努力转换中..."}

    return {"status": "success", "message": "上传成功"}
@app.delete("/api/books/{book_id}")
async def delete_book(
    book_id: str,
    user_token: Optional[str] = Header(None),
    guest_uuid: Optional[str] = Header(None)
):
    """彻底抹除书籍存在的痕迹（包含数据库记录和物理文件）"""
    db_path = "/app/data/library.db"
    
    try:
        # ✨ 关键修复：必须先把 db 连接建立好，包裹在 async with 里面！
        async with aiosqlite.connect(db_path) as db:
            # 现在 db 已经存在了，调用身份识别就不会报错了
            user_id = await get_current_user_id(db, user_token, guest_uuid)

            # 查出文件的物理路径和上传者 ID
            cursor = await db.execute("SELECT file_path, uploader_id FROM books WHERE id = ?", (book_id,))
            book_record = await cursor.fetchone()

            if not book_record:
                raise HTTPException(status_code=404, detail="书籍似乎已经不存在了")

            file_path, uploader_id = book_record

            # 判断权限：是彻底删除，还是仅仅移出书架
            if user_id == uploader_id:
                # 是上传者，彻底物理销毁
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                await db.execute("DELETE FROM user_books WHERE book_id = ?", (book_id,))
                await db.execute("DELETE FROM books WHERE id = ?", (book_id,))
                msg = "该书籍已从宇宙中彻底抹除！"
            else:
                # 只是白嫖的看客，仅从自己书架移除
                await db.execute("DELETE FROM user_books WHERE user_id = ? AND book_id = ?", (user_id, book_id))
                msg = "书籍已从您的书架移除，但源文件仍保留在城堡中。"

            # 统一提交魔法契约
            await db.commit()

        return {"status": "success", "message": msg}
        
    except Exception as e:
        print(f"💥 删除魔法失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
# 🔍 搜索全库（你的书 + 别人的公开书）
@app.get("/api/books/search")
async def search_books(
    q: str,
    user_token: Optional[str] = Header(None),
    guest_uuid: Optional[str] = Header(None)
):
    from database import DB_PATH
    async with aiosqlite.connect(DB_PATH) as db:
        user_id = await get_current_user_id(db, user_token, guest_uuid)
        search_term = f"%{q}%"
        
        # 魔法 SQL：选出书名/作者匹配的，并且（是你自己的 OR 它是公开的）
        query = """
            SELECT b.id, b.title, b.author, b.format, ub.progress_percentage, b.is_public, b.uploader_id,
                   CASE WHEN ub.user_id IS NOT NULL THEN 1 ELSE 0 END as is_owned
            FROM books b
            LEFT JOIN user_books ub ON b.id = ub.book_id AND ub.user_id = ?
            WHERE (b.title LIKE ? OR b.author LIKE ?)
            AND (ub.user_id IS NOT NULL OR b.is_public = 1)
        """
        cursor = await db.execute(query, (user_id, search_term, search_term))
        rows = await cursor.fetchall()
        
        books = []
        for row in rows:
            books.append({
                "id": row[0], "title": row[1], "author": row[2] or "佚名",
                "format": row[3], "progress": row[4] or 0,
                "is_public": bool(row[5]),
                "is_uploader": row[6] == user_id,
                "is_owned": bool(row[7])
            })
        return {"status": "success", "books": books}

# ➕ 白嫖公开书籍（加入自己书架）
@app.post("/api/books/{book_id}/add_to_shelf")
async def add_public_book(
    book_id: str,
    user_token: Optional[str] = Header(None),
    guest_uuid: Optional[str] = Header(None)
):
    from database import DB_PATH
    async with aiosqlite.connect(DB_PATH) as db:
        user_id = await get_current_user_id(db, user_token, guest_uuid)
        await db.execute("INSERT OR IGNORE INTO user_books (user_id, book_id) VALUES (?, ?)", (user_id, book_id))
        await db.commit()
    return {"status": "success", "message": "已成功偷取...啊不，借阅到您的书架！"}

# 👁️ 切换公开/私有状态
@app.put("/api/books/{book_id}/toggle_visibility")
async def toggle_visibility(
    book_id: str,
    user_token: Optional[str] = Header(None),
    guest_uuid: Optional[str] = Header(None)
):
    from database import DB_PATH
    async with aiosqlite.connect(DB_PATH) as db:
        user_id = await get_current_user_id(db, user_token, guest_uuid)
        
        # 先确认是不是上传者
        cursor = await db.execute("SELECT is_public FROM books WHERE id = ? AND uploader_id = ?", (book_id, user_id))
        record = await cursor.fetchone()
        if not record:
            raise HTTPException(status_code=403, detail="只有书籍的初始上传者才能修改可见性哦！")
        
        new_status = 0 if record[0] else 1
        await db.execute("UPDATE books SET is_public = ? WHERE id = ?", (new_status, book_id))
        
        # ✨ 核心修复：如果变成私有 (0)，直接抹除其他所有人的书架关联记录！
        if new_status == 0:
            await db.execute(
                "DELETE FROM user_books WHERE book_id = ? AND user_id != ?", 
                (book_id, user_id)
            )

        await db.commit()
        return {"status": "success", "is_public": new_status}


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
