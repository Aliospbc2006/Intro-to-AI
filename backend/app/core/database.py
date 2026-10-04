from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

# Motor là driver MongoDB bất đồng bộ. client/db được tạo một lần khi import và dùng chung
# cho các module crud/ và services/ (db.nodes, db.edges là hai collection).
client = AsyncIOMotorClient(settings.MONGO_URL)
db = client[settings.MONGO_DB_NAME]