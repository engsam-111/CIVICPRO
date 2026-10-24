import os, sys, requests, asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
SK = os.environ["CLERK_SECRET_KEY"]
H = {"Authorization": f"Bearer {SK}", "Content-Type": "application/json"}


def token(user_id):
    s = requests.post("https://api.clerk.com/v1/sessions", headers=H, json={"user_id": user_id}).json()
    return requests.post(f"https://api.clerk.com/v1/sessions/{s['id']}/tokens", headers=H, json={"expires_in_seconds": 3600}).json()["jwt"]


async def set_manager(uid):
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    await db.users.update_one({"user_id": uid}, {"$set": {"role": "manager"}})


if __name__ == "__main__":
    uid = sys.argv[1]
    if len(sys.argv) > 2 and sys.argv[2] == "manager":
        asyncio.run(set_manager(uid))
    print(token(uid))
