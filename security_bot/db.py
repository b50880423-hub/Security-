from datetime import datetime, timezone
from pymongo import AsyncMongoClient, ASCENDING, DESCENDING

class Database:
    def __init__(self, url: str, db_name: str):
        self.url = url
        self.db_name = db_name
        self.client = None
        self.db = None

    async def connect(self):
        self.client = AsyncMongoClient(self.url, serverSelectionTimeoutMS=10000)
        await self.client.admin.command("ping")
        self.db = self.client[self.db_name]
        await self.db.group_settings.create_index([("chat_id", ASCENDING)], unique=True)
        await self.db.incidents.create_index([("chat_id", ASCENDING), ("created_at", DESCENDING)])
        await self.db.incidents.create_index([("chat_id", ASCENDING), ("user_id", ASCENDING)])
        await self.db.moderation_actions.create_index([("chat_id", ASCENDING), ("user_id", ASCENDING), ("created_at", DESCENDING)])
        await self.db.bot_registry.create_index([("chat_id", ASCENDING), ("bot_user_id", ASCENDING)], unique=True)
        await self.db.domain_rules.create_index([("chat_id", ASCENDING), ("domain", ASCENDING)], unique=True)

    async def close(self):
        if self.client:
            await self.client.close()

    async def ensure_group(self, chat_id: int):
        await self.db.group_settings.update_one(
            {"chat_id": chat_id},
            {"$setOnInsert": {
                "chat_id": chat_id,
                "lockdown": False,
                "anti_spam": True,
                "anti_links": True,
                "explicit_protection": True,
                "raid_protection": True,
                "default_mute_minutes": 60,
                "updated_at": datetime.now(timezone.utc),
            }},
            upsert=True,
        )

    async def settings(self, chat_id: int):
        await self.ensure_group(chat_id)
        return await self.db.group_settings.find_one({"chat_id": chat_id})

    async def set_lockdown(self, chat_id: int, value: bool):
        await self.ensure_group(chat_id)
        await self.db.group_settings.update_one(
            {"chat_id": chat_id},
            {"$set": {"lockdown": value, "updated_at": datetime.now(timezone.utc)}}
        )

    async def incident(self, chat_id, user_id, actor_id, kind, severity, reason, message_id=None, metadata=None):
        doc = {
            "chat_id": chat_id, "user_id": user_id, "actor_id": actor_id,
            "kind": kind, "severity": severity, "reason": reason,
            "message_id": message_id, "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc),
        }
        result = await self.db.incidents.insert_one(doc)
        return str(result.inserted_id)

    async def action(self, chat_id, user_id, actor_id, action, reason, duration_seconds=None, incident_id=None):
        await self.db.moderation_actions.insert_one({
            "chat_id": chat_id, "user_id": user_id, "actor_id": actor_id,
            "action": action, "reason": reason,
            "duration_seconds": duration_seconds, "incident_id": incident_id,
            "created_at": datetime.now(timezone.utc),
        })

    async def history(self, chat_id, user_id, limit=30):
        cursor = self.db.moderation_actions.find(
            {"chat_id": chat_id, "user_id": user_id}
        ).sort("created_at", DESCENDING).limit(limit)
        return await cursor.to_list(length=limit)

    async def bot_event(self, chat_id, bot_id, username, added_by, promoted):
        await self.db.bot_registry.update_one(
            {"chat_id": chat_id, "bot_user_id": bot_id},
            {"$set": {
                "username": username,
                "added_by": added_by,
                "promoted": promoted,
                "updated_at": datetime.now(timezone.utc),
            }, "$setOnInsert": {"approved": False}},
            upsert=True,
        )

    async def domain_action(self, chat_id, domain):
        row = await self.db.domain_rules.find_one({"chat_id": chat_id, "domain": domain})
        return row["action"] if row else None
