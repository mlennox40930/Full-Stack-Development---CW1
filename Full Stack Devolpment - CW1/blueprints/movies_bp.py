from flask import Blueprint, request, jsonify, make_response
from pymongo import MongoClient
from bson import ObjectId

movies_bp = Blueprint('movies_bp', __name__)

client = MongoClient("mongodb://127.0.0.1:27017")
db = client.cinemapulse
movies = db.movies
# ---------------------------------------------------------
# GET ALL MOVIES
# ---------------------------------------------------------
@movies_bp.route("/api/v1.0/movies", methods=["GET"])
def show_all_movies():
    try:
        page_num = int(request.args.get('pn', 1))
        page_size = int(request.args.get('ps', 10))
    except ValueError:
        return make_response(jsonify({"error": "Invalid pagination parameters"}), 400)

    page_start = page_size * (page_num - 1)
    total_docs = movies.count_documents({})
    total_pages = (total_docs + page_size - 1) // page_size if total_docs > 0 else 0

    data_to_return = []
    for movie in movies.find().skip(page_start).limit(page_size):
        movie['_id'] = str(movie['_id'])
        for review in movie.get('reviews', []):
            if '_id' in review:
                review['_id'] = str(review['_id'])
        data_to_return.append(movie)

    response = {
        "page": page_num,
        "page_size": page_size,
        "total_results": total_docs,
        "total_pages": total_pages,
        "data": data_to_return
    }
    return make_response(jsonify(response), 200)
# ---------------------------------------------------------
# GET ALL INDIVIDUAL MOVIES
# ---------------------------------------------------------
@movies_bp.route("/api/v1.0/movies/<string:id>", methods=["GET"])
def show_one_movie(id):
    if len(id) != 24:
        return make_response(jsonify({"error": "Invalid movie ID format"}), 404)

    try:
        movie = movies.find_one({'_id': ObjectId(id)})
    except Exception:
        return make_response(jsonify({"error": "Invalid movie ID format"}), 404)

    if movie:
        movie['_id'] = str(movie['_id'])
        for review in movie.get('reviews', []):
            if '_id' in review:
                review['_id'] = str(review['_id'])
        return make_response(jsonify(movie), 200)

    return make_response(jsonify({"error": "Movie not found"}), 404)
# ---------------------------------------------------------
# GET INDIVIDUAL MOVIE STATS
# ---------------------------------------------------------
@movies_bp.route("/api/v1.0/movies/<string:id>/stats", methods=["GET"])
def get_movie_stats(id):
    if len(id) != 24:
        return make_response(jsonify({"error": "Invalid movie ID format"}), 404)

    pipeline = [
        {"$match": {"_id": ObjectId(id)}},
        {"$unwind": "$reviews"},
        {
            "$group": {
                "_id": "$_id",
                "title": {"$first": "$title"},
                "total_reviews": {"$sum": 1},
                "average_rating": {"$avg": "$reviews.rating"},
                "highest_rating": {"$max": "$reviews.rating"},
                "lowest_rating": {"$min": "$reviews.rating"}
            }
        }
    ]

    results = list(movies.aggregate(pipeline))
    if results:
        stats = results[0]
        stats["_id"] = str(stats["_id"])
        stats["average_rating"] = round(stats["average_rating"], 2)
        return make_response(jsonify(stats), 200)

    return make_response(jsonify({"error": "No reviews found for this movie or movie not found"}), 404)
# ---------------------------------------------------------
# GET ALL MOVIES NEARBY
# ---------------------------------------------------------
@movies_bp.route("/api/v1.0/movies/nearby", methods=["GET"])
def get_nearby_screenings():
    try:
        lng = float(request.args.get('lng', -5.9264))
        lat = float(request.args.get('lat', 54.5847))
        max_dist = float(request.args.get('max_dist', 10000))
    except ValueError:
        return make_response(jsonify({"error": "Invalid coordinate or distance parameters"}), 400)

    query = {
        "location": {
            "$nearSphere": {
                "$geometry": {
                    "type": "Point",
                    "coordinates": [lng, lat]
                },
                "$maxDistance": max_dist
            }
        }
    }

    nearby_movies = []
    for movie in movies.find(query).limit(10):
        movie['_id'] = str(movie['_id'])
        for review in movie.get('reviews', []):
            if '_id' in review:
                review['_id'] = str(review['_id'])
        nearby_movies.append(movie)

    return make_response(jsonify(nearby_movies), 200)
# ---------------------------------------------------------
# POST MOVIES
# ---------------------------------------------------------
@movies_bp.route("/api/v1.0/movies", methods=["POST"])
def add_movie():
    # request.values inspects both x-www-form-urlencoded body and query string parameters
    title = request.values.get("title")
    overview = request.values.get("overview")
    release_year = request.values.get("release_year", 2026)

    if not title or not overview:
        return make_response(jsonify({
            "error": "Missing title or overview form fields",
            "received_keys": list(request.values.keys())  # Helps debug exact key names sent
        }), 400)

    try:
        year = int(release_year)
    except (ValueError, TypeError):
        return make_response(jsonify({"error": "release_year must be an integer"}), 400)

    new_movie = {
        "title": title,
        "overview": overview,
        "release_year": year,
        "genres": ["Drama"],
        "runtime": 120,
        "location": {"type": "Point", "coordinates": [-5.9264, 54.5847]},
        "reviews": []
    }

    result = movies.insert_one(new_movie)
    new_id = str(result.inserted_id)

    return make_response(jsonify({
        "message": "Movie created successfully",
        "id": new_id,
        "url": f"http://127.0.0.1:5001/api/v1.0/movies/{new_id}"
    }), 201)
# ---------------------------------------------------------
# UPDATE MOVIES
# ---------------------------------------------------------
@movies_bp.route("/api/v1.0/movies/<string:id>", methods=["PATCH"])
def patch_movie(id):
    if len(id) != 24:
        return make_response(jsonify({"error": "Invalid movie ID format"}), 404)

    update_data = {}
    if "title" in request.form:
        update_data["title"] = request.form["title"]
    if "overview" in request.form:
        update_data["overview"] = request.form["overview"]
    if "release_year" in request.form:
        try:
            update_data["release_year"] = int(request.form["release_year"])
        except ValueError:
            return make_response(jsonify({"error": "release_year must be an integer"}), 400)

    if not update_data:
        return make_response(jsonify({"error": "No valid fields provided for update"}), 400)

    result = movies.update_one({"_id": ObjectId(id)}, {"$set": update_data})
    if result.matched_count == 1:
        return make_response(jsonify({"message": "Movie updated successfully", "updated_fields": update_data}), 200)
    return make_response(jsonify({"error": "Movie not found"}), 404)
# ---------------------------------------------------------
# DELETE MOVIES
# ---------------------------------------------------------
@movies_bp.route("/api/v1.0/movies/<string:id>", methods=["DELETE"])
def delete_movie(id):
    if len(id) != 24:
        return make_response(jsonify({"error": "Invalid movie ID format"}), 404)

    result = movies.delete_one({"_id": ObjectId(id)})
    if result.deleted_count == 1:
        return make_response(jsonify({}), 204)
    return make_response(jsonify({"error": "Movie not found"}), 404)