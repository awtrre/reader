import subprocess
import zipfile
import shutil
import asyncio
import uuid
import hashlib
import os
import re
import httpx
import aiosqlite
from pathlib import Path
from contextlib import asynccontextmanager
from bs4 import BeautifulSoup, NavigableString

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException, Header, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional

from database import init_db

# 🪄 城堡启动与关闭的生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🪄 正在唤醒记忆水晶，构建数字城堡的藏书阁...")
    await init_db()
    yield
    print("🏰 数字城堡进入休眠状态...")

# 🏰 实例化我们的城堡大管家
app = FastAPI(
    title="极简黑白数字图书馆 API",
    description="专为极客殿下树莓派打造的专属阅读后端",
    version="1.0.0",
    lifespan=lifespan
)

# 🛡️ 魔法护盾：CORS 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载 data 目录，让前端可以直接访问
app.mount("/api/static", StaticFiles(directory="/app/data"), name="static")

# -----------------------------------------------------------------
# 🗂️ 数据模型定义
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
         # ✨ 新增：解压完立刻进行附魔仪式，计算单元总数！
        print(f"🪄 开始为书籍附魔，注入绝对坐标...")
        total_units = _inject_sync_anchors(target_dir)
        print(f"✅ 附魔完成！共生成 {total_units} 个记忆单元。")
        return total_units # 返回单元总数
    except Exception as e:
        print(f"💥 爆破解压失败: {e}")
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        raise Exception(f"魔法书结构损坏: {str(e)}")

async def extract_epub_to_folder(source_path: str, book_id: str, remove_source: bool = True) -> tuple[str, int]:
    """
    修改返回值，现在返回 (文件夹路径, 总单元数)
    """
    target_dir = f"/app/data/books/{book_id}"
    total_units = await asyncio.to_thread(_sync_extract_epub, source_path, target_dir, remove_source)
    return target_dir, total_units

async def convert_to_epub_task(source_file_path: str, book_id: str):
    """
    原生炼金炉：直接在后端本地调用 ebook-convert！稳如老狗！
    """
    from database import DB_PATH
    print(f"🔥 本地炼金炉启动，目标文件: {source_file_path}")
    
    calibre_output_epub = f"/app/data/raw_books/converted_{book_id}.epub"
    cmd = ["ebook-convert", source_file_path, calibre_output_epub]

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='ignore').strip()
            raise Exception(f"本地转换引擎报错: {error_msg}")

        print(f"✅ 转换成功，生成临时文件: {calibre_output_epub}")

        # 调用爆破术 (注意这里接收了两个返回值)
        final_dir, total_units = await extract_epub_to_folder(calibre_output_epub, book_id, remove_source=True)
        
        # 更新记忆水晶 (加上 total_units)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE books SET format = 'epub', file_path = ?, total_units = ? WHERE id = ?",
                (final_dir, total_units, book_id)
            )
            await db.commit()
            
        # 清理原始非 EPUB 文件
        if os.path.exists(source_file_path):
            os.remove(source_file_path)
            
        print(f"✨ 炼金圆满完成！书籍 {book_id} 已入库。")

    except Exception as e:
        print(f"💥 炼金炉炸膛: {e}")
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM user_books WHERE book_id = ?", (book_id,))
            await db.execute("DELETE FROM books WHERE id = ?", (book_id,))
            await db.commit()

def _inject_sync_anchors(target_dir: str) -> int:
    import json # 确保引入 json
    total_units = 0
    unit_map = [] # 🗺️ 藏宝图：记录每个章节对应的 unit 范围
    
    # 1. 🔍 寻找核心 OPF 文件，确定真正的书籍阅读顺序！(修复 os.walk 的乱序隐患)
    opf_path = None
    for root, _, files in os.walk(target_dir):
        for file in files:
            if file.endswith('.opf'):
                opf_path = os.path.join(root, file)
                break
        if opf_path: break
        
    html_files = []
    if opf_path:
        opf_dir = os.path.dirname(opf_path)
        with open(opf_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'lxml-xml')
            
        # 解析 EPUB 的骨架 (manifest 和 spine)
        manifest = {item.get('id'): item.get('href') for item in soup.find_all('item')}
        for itemref in soup.find_all('itemref'):
            href = manifest.get(itemref.get('idref'))
            if href:
                clean_href = href.split('#')[0] # 滤除自带锚点
                full_path = os.path.join(opf_dir, clean_href)
                if full_path not in [f[1] for f in html_files] and full_path.endswith(('.html', '.htm', '.xhtml')):
                    # clean_href 就是 Epub.js 认得的那个相对路径
                    html_files.append((clean_href, full_path))
    else:
        # 极端兜底：如果没有 OPF，勉强按文件名排序
        for root, _, files in os.walk(target_dir):
            for file in sorted(files):
                if file.endswith(('.html', '.htm', '.xhtml')):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, target_dir).replace('\\', '/')
                    html_files.append((rel_path, full_path))

    # 2. 🪄 开始按正确的顺序附魔
    for href, filepath in html_files:
        if not os.path.exists(filepath): continue
        
        with open(filepath, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'lxml-xml' if filepath.endswith('.xhtml') else 'lxml')

        start_unit = total_units

        # --- 这里是修改的核心部分：按页面从上到下的真实顺序统一打标 ---
        elements = soup.find_all(['img', 'svg', 'image', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        for el in elements:
            if el.name in ['img', 'svg', 'image']:
                # 处理图片
                el['id'] = f"unit-{total_units}"
                classes = el.get('class', [])
                if isinstance(classes, str): classes = [classes]
                el['class'] = classes + ['sync-anchor']
                total_units += 1
            else:
                # 文本切碎
                if el.find(['img', 'svg', 'image']): continue
                for text_node in el.find_all(string=True):
                    text = text_node.text
                    if not text.strip(): continue
                    parent = text_node.parent
                    if parent and parent.name in ['ruby', 'rt', 'rp', 'pre', 'code']:
                        if not parent.has_attr('id'):
                            parent['id'] = f"unit-{total_units}"
                            parent_classes = parent.get('class', [])
                            if isinstance(parent_classes, str): parent_classes = [parent_classes]
                            parent['class'] = parent_classes + ['sync-anchor']
                            total_units += 1
                        continue
                    sentences = re.findall(r'[^。！？!?\.\…]+[。！？!?\.\…]+[”’"\'\)\]）】》]*|.+', text)
                    if not sentences: continue
                    fragment = soup.new_tag("span")
                    for s in sentences:
                        if not s.strip(): continue
                        new_span = soup.new_tag("span", id=f"unit-{total_units}", **{'class': 'sync-anchor'})
                        new_span.string = s
                        fragment.append(new_span)
                        total_units += 1
                    text_node.replace_with(fragment)
                    fragment.unwrap()
        # --- 修改核心部分结束 ---

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(str(soup))
            
        # ✨ 核心新增：记录该章节“承包”了哪些 unit！
        if total_units > start_unit:
            unit_map.append({
                "href": href,
                "start": start_unit,
                "end": total_units - 1
            })

    # 3. 💾 将藏宝图存入这本电子书的专属目录
    map_path = os.path.join(target_dir, 'unit_map.json')
    with open(map_path, 'w', encoding='utf-8') as f:
        json.dump(unit_map, f, ensure_ascii=False)
        
    return total_units
# -----------------------------------------------------------------
# 🕵️‍♂️ 极客身份验证模块
# -----------------------------------------------------------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

@app.post("/api/auth/login")
async def library_login(request: AuthRequest):
    db_path = "/app/data/library.db"
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("SELECT id, password_hash FROM users WHERE username = ?", (request.username,))
        user = await cursor.fetchone()
        
        input_hash = hash_password(request.password)
        
        if not user:
            print(f"🪄 捕捉到新魔法师 {request.username}，正在为您缔结契约...")
            await db.execute(
                "INSERT INTO users (username, password_hash, is_guest) VALUES (?, ?, 0)", 
                (request.username, input_hash)
            )
            await db.commit()
            return {"status": "success", "token": request.username, "message": "注册并登录成功！"}
            
        else:
            db_password_hash = user[1]
            if input_hash == db_password_hash:
                print(f"👑 欢迎回来，尊贵的 {request.username}！")
                return {"status": "success", "token": request.username, "message": "身份验证成功！"}
            else:
                raise HTTPException(status_code=401, detail="密码错误，试图潜入城堡的麻瓜？")

@app.post("/api/auth/logout")
async def geek_logout():
    return {"status": "success", "message": "已断开神经连接，期待您再次降临！"}

# -----------------------------------------------------------------
# 🔖 书籍进度管理
# -----------------------------------------------------------------
@app.get("/api/books/{book_id}/progress")
async def get_progress(book_id: str, user_token: Optional[str] = Header(None), guest_uuid: Optional[str] = Header(None)):
    from database import DB_PATH
    async with aiosqlite.connect(DB_PATH) as db:
        user_id = await get_current_user_id(db, user_token, guest_uuid)
        
        # ✨ 逻辑重构：认定“获取进度 = 刚才打开了这本书”，立刻刷新最后阅读时间！
        await db.execute(
            "UPDATE user_books SET last_read_at = CURRENT_TIMESTAMP WHERE user_id = ? AND book_id = ?",
            (user_id, book_id)
        )
        await db.commit()

        # 原本的查询逻辑保持不变
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT current_cfi FROM user_books WHERE user_id = ? AND book_id = ?",
            (user_id, book_id)
        )
        res = await cursor.fetchone()
        return {"cfi": res["current_cfi"] if res else None}

@app.post("/api/books/{book_id}/progress")
async def save_progress(book_id: str, payload: dict, user_token: Optional[str] = Header(None), guest_uuid: Optional[str] = Header(None)):
    from database import DB_PATH, update_reading_progress  # ✨ 衔接点：把完美的工具函数导进来
    
    async with aiosqlite.connect(DB_PATH) as db:
        user_id = await get_current_user_id(db, user_token, guest_uuid)
        cursor = await db.execute(
            "SELECT 1 FROM user_books WHERE user_id = ? AND book_id = ?",
            (user_id, book_id)
        )
        is_owner = await cursor.fetchone()
        if not is_owner:
            raise HTTPException(status_code=403, detail="账号状态已变更，拒绝越权保存进度！")

    cfi = payload.get("cfi")
    percent = payload.get("percent", 0)

    # ✨ 完美衔接：直接调用 database.py 里写好的护城河逻辑！
    await update_reading_progress(user_id, book_id, cfi, percent)
    
    return {"status": "success"}
# -----------------------------------------------------------------
# 📚 书架与图书管理模块
# -----------------------------------------------------------------
async def get_current_user_id(db, user_token: str, guest_uuid: str) -> int:
    token_to_use = user_token if user_token else guest_uuid
    if not token_to_use:
        token_to_use = "anonymous_stranger"

    is_guest = 0 if user_token else 1
    cursor = await db.execute("SELECT id FROM users WHERE username = ?", (token_to_use,))
    user = await cursor.fetchone()
    
    if user:
        return user[0]
    else:
        cursor = await db.execute(
            "INSERT OR IGNORE INTO users (username, is_guest) VALUES (?, ?)", 
            (token_to_use, is_guest)
        )
        await db.commit()
        if cursor.lastrowid:
            return cursor.lastrowid
        cursor = await db.execute("SELECT id FROM users WHERE username = ?", (token_to_use,))
        user = await cursor.fetchone()
        return user[0] if user else 1

@app.get("/api/books")
async def get_bookshelf(user_token: Optional[str] = Header(None), guest_uuid: Optional[str] = Header(None)):
    db_path = "/app/data/library.db"
    books = []
    try:
        async with aiosqlite.connect(db_path) as db:
            user_id = await get_current_user_id(db, user_token, guest_uuid)
            cursor = await db.execute("""
                SELECT b.id, b.title, b.author, b.format, ub.progress_percentage, b.uploader_id, b.is_public , b.total_units
                FROM books b 
                INNER JOIN user_books ub ON b.id = ub.book_id 
                WHERE ub.user_id = ? 
                ORDER BY ub.last_read_at DESC
            """, (user_id,))
            rows = await cursor.fetchall()
            for row in rows:
                books.append({
                    "id": row[0], "title": row[1], "author": row[2] or "佚名",
                    "format": row[3], "progress": row[4],
                    "is_uploader": row[5] == user_id,
                    "is_public": bool(row[6]), "is_owned": True, "total_units": row[7] or 0
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
    file_ext = Path(file.filename).suffix.lower()
    book_id = str(uuid.uuid4())
    save_filename = f"{book_id}{file_ext}"
    title = Path(file.filename).stem

    raw_dir = "/app/data/raw_books"
    os.makedirs(raw_dir, exist_ok=True)
    temp_path = f"{raw_dir}/{save_filename}"
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    format_type = file_ext.replace('.', '')
    db_save_path = temp_path
    
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
        await db.execute("INSERT INTO user_books (user_id, book_id) VALUES (?, ?)", (user_id, book_id))
        await db.commit()

    if file_ext == '.epub':
        # 接收两个返回值
        final_path, total_units = await extract_epub_to_folder(temp_path, book_id, remove_source=True)
        async with aiosqlite.connect(db_path) as db:
            # 更新 total_units
            await db.execute("UPDATE books SET file_path = ?, total_units = ? WHERE id = ?", (final_path, total_units, book_id))
            await db.commit()
        return {"status": "success", "message": "EPUB 已就绪，秒开已激活！"}
    
    elif file_ext in ['.mobi', '.azw3', '.txt', '.pdf']:
        background_tasks.add_task(convert_to_epub_task, temp_path, book_id)
        return {"status": "processing", "message": "非 EPUB 格式，后台炼金炉正在努力转换中..."}

    return {"status": "success", "message": "上传成功"}

@app.delete("/api/books/{book_id}")
async def delete_book(book_id: str, user_token: Optional[str] = Header(None), guest_uuid: Optional[str] = Header(None)):
    db_path = "/app/data/library.db"
    try:
        async with aiosqlite.connect(db_path) as db:
            user_id = await get_current_user_id(db, user_token, guest_uuid)
            cursor = await db.execute("SELECT file_path, uploader_id FROM books WHERE id = ?", (book_id,))
            book_record = await cursor.fetchone()

            if not book_record:
                raise HTTPException(status_code=404, detail="书籍似乎已经不存在了")

            file_path, uploader_id = book_record

            if user_id == uploader_id:
                if file_path and os.path.exists(file_path):
                    if os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                    else:
                        os.remove(file_path)
                await db.execute("DELETE FROM user_books WHERE book_id = ?", (book_id,))
                await db.execute("DELETE FROM books WHERE id = ?", (book_id,))
                msg = "该书籍已从宇宙中彻底抹除！"
            else:
                await db.execute("DELETE FROM user_books WHERE user_id = ? AND book_id = ?", (user_id, book_id))
                msg = "书籍已从您的书架移除，但源文件仍保留在城堡中。"

            await db.commit()
        return {"status": "success", "message": msg}
    except Exception as e:
        print(f"💥 删除魔法失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/books/search")
async def search_books(q: str, user_token: Optional[str] = Header(None), guest_uuid: Optional[str] = Header(None)):
    from database import DB_PATH
    async with aiosqlite.connect(DB_PATH) as db:
        user_id = await get_current_user_id(db, user_token, guest_uuid)
        search_term = f"%{q}%"
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
                "is_public": bool(row[5]), "is_uploader": row[6] == user_id,
                "is_owned": bool(row[7])
            })
        return {"status": "success", "books": books}

@app.post("/api/books/{book_id}/add_to_shelf")
async def add_public_book(book_id: str, user_token: Optional[str] = Header(None), guest_uuid: Optional[str] = Header(None)):
    from database import DB_PATH
    async with aiosqlite.connect(DB_PATH) as db:
        user_id = await get_current_user_id(db, user_token, guest_uuid)
        await db.execute("INSERT OR IGNORE INTO user_books (user_id, book_id) VALUES (?, ?)", (user_id, book_id))
        await db.commit()
    return {"status": "success", "message": "已成功偷取...啊不，借阅到您的书架！"}

@app.put("/api/books/{book_id}/toggle_visibility")
async def toggle_visibility(book_id: str, user_token: Optional[str] = Header(None), guest_uuid: Optional[str] = Header(None)):
    from database import DB_PATH
    async with aiosqlite.connect(DB_PATH) as db:
        user_id = await get_current_user_id(db, user_token, guest_uuid)
        cursor = await db.execute("SELECT is_public FROM books WHERE id = ? AND uploader_id = ?", (book_id, user_id))
        record = await cursor.fetchone()
        if not record:
            raise HTTPException(status_code=403, detail="只有书籍的初始上传者才能修改可见性哦！")
        new_status = 0 if record[0] else 1
        await db.execute("UPDATE books SET is_public = ? WHERE id = ?", (new_status, book_id))
        if new_status == 0:
            await db.execute("DELETE FROM user_books WHERE book_id = ? AND user_id != ?", (book_id, user_id))
        await db.commit()
        return {"status": "success", "is_public": new_status}

# -----------------------------------------------------------------
# 📖 沉浸式阅读小工具 (字典 & 维基反代)
# -----------------------------------------------------------------
@app.get("/api/dict/search")
async def search_dictionary(word: str):
    return {"word": word, "translation": "这里是来自大辞海的硬核解释！"}

PROXY_URL = os.getenv("SOCKS5_PROXY", "socks5://172.17.0.1:1080")

@app.get("/api/proxy/wiki")
async def proxy_wikipedia(query: str):
    wiki_url = f"https://zh.wikipedia.org/api/rest_v1/page/html/{query}"
    async with httpx.AsyncClient(proxy=PROXY_URL) as client:
        try:
            response = await client.get(
                wiki_url, 
                headers={"User-Agent": "MyGeekLibrary/1.0", "Accept-Language": "zh-CN,zh;q=0.9"},
                timeout=10.0
            )
            if response.status_code == 200:
                return HTMLResponse(content=response.text)
            else:
                raise HTTPException(status_code=404, detail="维基的知识库里似乎没有找到这个词条呢...")
        except Exception as e:
            print(f"代理请求失败: {e}") 
            raise HTTPException(status_code=500, detail="魔法网络波动，穿墙失败啦！请检查 SOCKS5 端口哦！")

# -----------------------------------------------------------------
# 🗣️ 赛博伴读 (Piper TTS 调用)
# -----------------------------------------------------------------
@app.post("/api/tts/synthesize")
async def synthesize_speech(request: TTSRequest):
    tts_url = "http://tts:10200" 
    async def fetch_audio_stream():
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", f"{tts_url}/process", params={"text": request.text}) as response:
                if response.status_code != 200:
                    yield b"TTS Engine Error"
                    return
                async for chunk in response.aiter_bytes():
                    yield chunk

    return StreamingResponse(fetch_audio_stream(), media_type="audio/wav")