from pymongo import MongoClient, GEOSPHERE

client = MongoClient("mongodb://127.0.0.1:27017")
db = client.cinemapulse

db.movies.create_index([("location", GEOSPHERE)])
print("2dsphere index created successfully on location field!")