import asyncio
import json
from prisma import Prisma

db = Prisma()

async def seed_skill_suggestions():
    print("Connecting to database...")
    await db.connect()
    print("Connected to database ✅")

    # Load data from JSON
    with open("scripts/skill_suggestions.json", "r") as f:
        skills_data = json.load(f)

    # Clear existing records
    await db.skillsuggestion.delete_many()
    print("Cleared old skill suggestions 🧹")

    # Insert new records
    for item in skills_data:
        await db.skillsuggestion.create(
            data={
                "department": item["department"],
                "suggestions": item["suggestions"],
            }
        )
        print(f"Inserted: {item['department']}")

    await db.disconnect()
    print("Seeding completed successfully 🌱")

if __name__ == "__main__":
    asyncio.run(seed_skill_suggestions())
