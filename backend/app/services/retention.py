import asyncio
import os
import datetime
from sqlalchemy import select, delete
from app.core.database import async_session
from app.models.models import Defect, SystemLog

class RetentionWorker:
    def __init__(self, retention_days: int = 30, interval_hours: int = 24):
        self.retention_days = retention_days
        self.interval_hours = interval_hours
        self.running = False
        self._task = None

    async def start(self):
        self.running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self):
        print(f"[RETENTION WORKER] Started. Deleting records older than {self.retention_days} days.")
        
        while self.running:
            try:
                cutoff_date = datetime.datetime.now() - datetime.timedelta(days=self.retention_days)
                
                async with async_session() as session:
                    # Find old defects to delete files
                    result = await session.execute(
                        select(Defect).where(Defect.timestamp < cutoff_date)
                    )
                    old_defects = result.scalars().all()
                    
                    # Delete from DB
                    await session.execute(delete(Defect).where(Defect.timestamp < cutoff_date))
                    await session.execute(delete(SystemLog).where(SystemLog.timestamp < cutoff_date))
                    await session.commit()
                    
                    import logging
                    for defect in old_defects:
                        if defect.image_path:
                            filepath = os.path.join("/app/data/defects", defect.image_path)
                            try:
                                if os.path.exists(filepath) and os.path.isfile(filepath):
                                    os.remove(filepath)
                            except Exception as e:
                                logging.warning(f"[RETENTION] Failed to delete file {filepath}: {e}")
                    
                    if old_defects:
                        print(f"[RETENTION] Deleted {len(old_defects)} old defects.")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[RETENTION ERROR] {e}")
            
            # Wait for the next interval
            try:
                await asyncio.sleep(self.interval_hours * 3600)
            except asyncio.CancelledError:
                break
