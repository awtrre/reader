import aiosqlite
import logging

# 告诉树莓派咱们的记忆水晶存在哪里
DB_PATH = "/app/data/library.db"

async def init_db():
    """
    🔮 唤醒记忆水晶！在系统启动时自动建表。
    如果没有表就建，有的话就乖乖跳过~
    """
    logging.info("🪄 正在连接数字城堡的记忆中枢...")
    async with aiosqlite.connect(DB_PATH) as db:
        
        # 1. 🧙‍♂️ 魔法师花名册 (包含幽灵游客和正式用户)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,       -- 极客登录名 (如果是幽灵游客，这里存 UUID)
                password_hash TEXT,         -- 密码哈希 (游客为空)
                is_guest BOOLEAN DEFAULT 0, -- 标记是不是没有注册的幽灵游客 👻
                layout_prefs TEXT           -- JSON格式：保存黑白灰书架的布局设置
            )
        """)

        # 2. 📖 皇家藏书阁 (保存书籍元数据)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                author TEXT,
                cover_path TEXT,
                file_path TEXT NOT NULL,
                format TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                uploader_id INTEGER,         -- ✨ 新增：记录书籍的源头主人
                is_public BOOLEAN DEFAULT 0,  -- ✨ 新增：是否对所有人可见
                total_units INTEGER DEFAULT 0         
            )
        """)

        # 3. 🔖 灵魂羁绊表 (用户和书的关联，包含阅读进度和朗读记忆！)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_books (
                user_id INTEGER,
                book_id TEXT,
                progress_percentage REAL DEFAULT 0.0, -- 阅读进度百分比 (用于书架底部的小进度条)
                current_cfi TEXT,                     -- 🌟 极其重要！记住你读到了哪个字的坐标！
                tts_cfi TEXT,                         -- 🗣️ 赛博伴读专属记忆！上次朗读停在的坐标
                font_size INTEGER DEFAULT 100,
                last_read_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, book_id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
            )
        """)
        try:
            await db.execute("ALTER TABLE user_books ADD COLUMN font_size INTEGER DEFAULT 100")
        except Exception:
            pass
        # 4. ✍️ 岁月痕迹表 (你的划线、批注全在这里)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS annotations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                book_id TEXT,
                cfi_range TEXT NOT NULL,    -- 划线的起止坐标范围 (Epub.js 原生支持)
                selected_text TEXT,         -- 你勾画出的那段原话
                note TEXT,                  -- 你写的批注内容
                color TEXT DEFAULT 'gray',  -- 极简风嘛，默认灰色高亮 🕶️
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
            )
        """)

        await db.commit()
        logging.info("✨ 记忆中枢构建完毕！所有的表都已经乖乖就位啦！")

# --- 下面是一些提供给 main.py 调用的便捷魔法小工具 ---


async def save_tts_position(user_id: int, book_id: str, tts_cfi: str):
    """悄悄记住赛博播音员读到了哪里~ 🎙️"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE user_books SET tts_cfi = ? WHERE user_id = ? AND book_id = ?
        """, (tts_cfi, user_id, book_id))
        await db.commit()
        
async def update_reading_progress(user_id: int, book_id: str, cfi: str, percentage: float):
    """
    🌟 进度保存中枢（完美版）：安全更新阅读进度，绝不误伤 TTS 进度！
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # 使用 UPSERT 语法：插入新数据，如果主键冲突则只更新指定的字段
        await db.execute("""
            INSERT INTO user_books (user_id, book_id, current_cfi, progress_percentage, last_read_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, book_id) DO UPDATE SET 
                current_cfi = excluded.current_cfi,
                progress_percentage = excluded.progress_percentage,
                last_read_at = CURRENT_TIMESTAMP
        """, (user_id, book_id, cfi, percentage))
        await db.commit()
