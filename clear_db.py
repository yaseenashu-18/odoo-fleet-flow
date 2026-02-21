from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

def clear_data():
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/fleetflow')
    client = MongoClient(MONGO_URI)
    db = client.get_database()

    print("--- ⚠️ WIPING DATABASE FOR FRESH START ⚠️ ---")
    
    # List of all collections to clear
    collections = ['users', 'vehicles', 'trips', 'maintenance', 'expenses', 'drivers']
    
    for collection in collections:
        db[collection].delete_many({})
        print(f"Cleared: {collection}")

    print("\n✅ Database is now EMPTY.")
    print("🚀 You can now go to /register and create your own Admin account.")

if __name__ == "__main__":
    clear_data()
