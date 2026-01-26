"""
数据库迁移管理器 - 自动执行SQL迁移脚本
"""
import os
import sqlite3
from pathlib import Path
from typing import List, Tuple
from .database import engine
from sqlalchemy import text


class MigrationManager:
    """数据库迁移管理器"""
    
    def __init__(self):
        self.migrations_dir = Path(__file__).parent.parent / "migrations"
        self.db_path = self._get_db_path()
        
    def _get_db_path(self) -> str:
        """获取SQLite数据库路径"""
        db_url = str(engine.url)
        if "sqlite:///" in db_url:
            return db_url.replace("sqlite:///", "")
        return "./data/video.db"
    
    def _get_applied_migrations(self) -> List[str]:
        """获取已应用的迁移列表"""
        try:
            with engine.connect() as conn:
                # 创建迁移记录表（如果不存在）
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version VARCHAR(255) PRIMARY KEY,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                conn.commit()
                
                # 查询已应用的迁移
                result = conn.execute(text("SELECT version FROM schema_migrations"))
                return [row[0] for row in result]
        except Exception as e:
            print(f"获取迁移记录失败: {e}")
            return []
    
    def _mark_migration_applied(self, version: str):
        """标记迁移已应用"""
        try:
            with engine.connect() as conn:
                conn.execute(
                    text("INSERT INTO schema_migrations (version) VALUES (:version)"),
                    {"version": version}
                )
                conn.commit()
        except Exception as e:
            print(f"标记迁移失败: {e}")
    
    def _get_pending_migrations(self) -> List[Tuple[str, Path]]:
        """获取待执行的迁移文件"""
        if not self.migrations_dir.exists():
            return []
        
        applied = self._get_applied_migrations()
        pending = []
        
        for sql_file in sorted(self.migrations_dir.glob("*.sql")):
            version = sql_file.stem  # 文件名（不含扩展名）
            if version not in applied:
                pending.append((version, sql_file))
        
        return pending
    
    def _execute_sql_file(self, sql_file: Path) -> bool:
        """执行SQL文件"""
        try:
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # 分割SQL语句（按分号分割，忽略注释）
            statements = []
            current_statement = []
            
            for line in sql_content.split('\n'):
                # 跳过注释行
                stripped = line.strip()
                if stripped.startswith('--') or not stripped:
                    continue
                
                current_statement.append(line)
                
                # 如果行以分号结尾，表示一条语句结束
                if stripped.endswith(';'):
                    statements.append('\n'.join(current_statement))
                    current_statement = []
            
            # 执行每条SQL语句
            with engine.connect() as conn:
                for statement in statements:
                    if statement.strip():
                        try:
                            conn.execute(text(statement))
                        except Exception as e:
                            # 忽略"列已存在"等错误
                            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                                print(f"  ⚠️  跳过已存在的修改: {str(e)[:100]}")
                            else:
                                raise
                conn.commit()
            
            return True
            
        except Exception as e:
            print(f"执行SQL文件失败 {sql_file.name}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_migrations(self):
        """运行所有待执行的迁移"""
        pending = self._get_pending_migrations()
        
        if not pending:
            print("✓ 数据库迁移：无待执行的迁移")
            return
        
        print(f"\n📦 发现 {len(pending)} 个待执行的迁移:")
        for version, sql_file in pending:
            print(f"  - {version}")
        
        print("\n开始执行迁移...")
        
        for version, sql_file in pending:
            print(f"\n执行迁移: {version}")
            if self._execute_sql_file(sql_file):
                self._mark_migration_applied(version)
                print(f"✓ 迁移完成: {version}")
            else:
                print(f"✗ 迁移失败: {version}")
                break
        
        print("\n✓ 数据库迁移完成!\n")


def run_migrations():
    """运行数据库迁移（供外部调用）"""
    manager = MigrationManager()
    manager.run_migrations()


if __name__ == "__main__":
    run_migrations()

