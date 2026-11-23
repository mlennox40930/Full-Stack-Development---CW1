from flask import Blueprint, request, jsonify, make_response
from pymongo import MongoClient
from bson import ObjectId
from bson.errors import InvalidId

reviews_bp = Blueprint('reviews_bp', __name__)

client = MongoClient("mongodb://127.0.0.1:27017")
db = client.cinemapulse
movies = db.movies


# ---------------------------------------------------------
# GET ALL REVIEWS FOR A MOVIE
# ---------------------------------------------------------
@reviews_bp.route("/api/v1.0/movies/<string:id>/reviews", methods=["GET"])
def get_all_reviews(id):
    try:
        movie_oid = ObjectId(id)
    except InvalidId:
        return make_response(jsonify({"error": "Invalid movie ID format"}), 400)

    movie = movies.find_one({"_id": movie_oid}, {"reviews": 1})
    if movie and "reviews" in movie:
        for review in movie["reviews"]:
            if "_id" in review:
                review["_id"] = str(review["_id"])
        return make_response(jsonify(movie["reviews"]), 200)

    return make_response(jsonify({"error": "Movie not found"}), 404)


# ---------------------------------------------------------
# GET A SINGLE REVIEW
# ---------------------------------------------------------
@reviews_bp.route("/api/v1.0/movies/<string:id>/reviews/<string:review_id>", methods=["GET"])
def get_one_review(id, review_id):
    try:
        movie_oid = ObjectId(id)
    except InvalidId:
        return make_response(jsonify({"error": "Invalid movie ID format"}), 400)

    # Search for the specific movie document
    movie = movies.find_one({"_id": movie_oid}, {"reviews": 1})
    if not movie or "reviews" not in movie:
        return make_response(jsonify({"error": "Movie not found"}), 404)

    # Locate the target review in the embedded array
    for review in movie.get("reviews", []):
        if str(review.get("_id")) == review_id:
            review["_id"] = str(review["_id"])
            return make_response(jsonify(review), 200)

    return make_response(jsonify({"error": "Review not found"}), 404)


# ---------------------------------------------------------
# POST A REVIEW
# ---------------------------------------------------------
@reviews_bp.route("/api/v1.0/movies/<string:id>/reviews", methods=["POST"])
def add_review(id):
    try:
        movie_oid = ObjectId(id)
    except InvalidId:
        return make_response(jsonify({"error": "Invalid movie ID format"}), 400)

    user_id = request.form.get("user_id")
    rating = request.form.get("rating")
    comment = request.form.get("comment")

    if not user_id or not rating or not comment:
        return make_response(jsonify({"error": "Missing user_id, rating, or comment form fields"}), 400)

    try:
        rating_val = float(rating)
        user_id_val = int(user_id)
    except ValueError:
        return make_response(jsonify({"error": "Invalid rating or user_id format"}), 400)

    new_review = {
        "_id": ObjectId(),
        "user_id": user_id_val,
        "rating": rating_val,
        "comment": comment
    }

    result = movies.update_one(
        {"_id": movie_oid},
        {"$push": {"reviews": new_review}}
    )

    if result.matched_count == 1:
        new_review_link = f"http://127.0.0.1:5000/api/v1.0/movies/{id}/reviews/{str(new_review['_id'])}"
        return make_response(jsonify({"message": "Review added successfully", "url": new_review_link}), 201)

    return make_response(jsonify({"error": "Movie not found"}), 404)


# ---------------------------------------------------------
# DELETE A REVIEW
# ---------------------------------------------------------
@reviews_bp.route("/api/v1.0/movies/<string:id>/reviews/<string:review_id>", methods=["DELETE"])
def delete_review(id, review_id):
    try:
        movie_oid = ObjectId(id)
    except InvalidId:
        return make_response(jsonify({"error": "Invalid ID format"}), 400)

    # 1. Try deleting matching ObjectId
    try:
        review_target = ObjectId(review_id)
    except InvalidId:
        review_target = review_id

    result = movies.update_one(
        {"_id": movie_oid},
        {"$pull": {"reviews": {"_id": review_target}}}
    )

    # 2. Fallback: If 0 modified, attempt matching string review_id
    if result.modified_count == 0 and isinstance(review_target, ObjectId):
        result = movies.update_one(
            {"_id": movie_oid},
            {"$pull": {"reviews": {"_id": review_id}}}
        )

    if result.modified_count == 1:
        return make_response(jsonify({}), 204)

    return make_response(jsonify({"error": "Movie or review not found"}), 404)
# ---------------------------------------------------------
# UPDATE A REVIEW
# ---------------------------------------------------------
@reviews_bp.route("/api/v1.0/movies/<string:id>/reviews/<string:review_id>", methods=["PUT"])
def update_review(id, review_id):
    try:
        movie_oid = ObjectId(id)
        review_oid = ObjectId(review_id)
    except InvalidId:
        return make_response(jsonify({"error": "Invalid ID format"}), 400)

    # Read update data from form or JSON payload
    rating = request.form.get("rating") or (request.json.get("rating") if request.is_json else None)
    comment = request.form.get("comment") or (request.json.get("comment") if request.is_json else None)

    if not rating and not comment:
        return make_response(jsonify({"error": "At least one field (rating or comment) is required to update"}), 400)

    # Build positional update payload
    update_fields = {}
    if rating is not None:
        try:
            update_fields["reviews.$.rating"] = float(rating)
        except ValueError:
            return make_response(jsonify({"error": "Invalid rating format"}), 400)

    if comment is not None:
        update_fields["reviews.$.comment"] = comment

    # Update matching review inside the array using positional operator ($)
    result = movies.update_one(
        {"_id": movie_oid, "reviews._id": review_oid},
        {"$set": update_fields}
    )

    if result.matched_count == 0:
        return make_response(jsonify({"error": "Movie or review not found"}), 404)

    return make_response(jsonify({"message": "Review updated successfully"}), 200)