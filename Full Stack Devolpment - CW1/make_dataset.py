import json
from pymongo import MongoClient
from bson import ObjectId

client = MongoClient("mongodb://127.0.0.1:27017")
db = client.cinemapulse
movies_collection = db.movies

with open("movies_clean.json", "r", encoding="utf-8") as f:
    movies_data = json.load(f)

def format_oids(doc):
    if isinstance(doc, dict):
        if "$oid" in doc:
            return ObjectId(doc["$oid"].strip())
        if "$ oid" in doc:
            return ObjectId(doc["$ oid"].strip())
        return {k: format_oids(v) for k, v in doc.items()}
    elif isinstance(doc, list):
        return [format_oids(item) for item in doc]
    return doc

clean_data = [format_oids(m) for m in movies_data]

movies_collection.delete_many({})
result = movies_collection.insert_many(clean_data)

print(f"Successfully inserted {len(result.inserted_ids)} movies into database 'cinemapulse'!")