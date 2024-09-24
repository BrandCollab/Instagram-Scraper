import instaloader
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from datetime import datetime
import numpy as np

# Load environment variables from .env file
load_dotenv()

# Get MongoDB connection details from environment variables
mongodb_uri = os.getenv("MONGODB_URI")


def fetch_from_mongodb(username: str) -> dict:
    try:
        # Establish connection to MongoDB
        client = MongoClient(mongodb_uri)
        db = client["test"]
        collection = db["instagram_profiles"]

        # Query for the document with the specified username
        profile_data = collection.find_one({"username": username})

        if profile_data:
            print(f"Fetched data for username '{username}'")
            return profile_data
        else:
            print(f"No data found for username '{username}'.")
            return None

    except Exception as e:
        print(f"An error occurred while fetching from MongoDB: {e}")
        return None

def calculate_engagement_rate(username: str) -> dict:
    try:

        profile_data = fetch_from_mongodb(username)

        # Calculate average likes and comments
        average_likes = profile_data["average_likes"]
        average_comments = profile_data["average_comments"]
        engagement_rate = profile_data["engagement_rate"]
        
        # Initialize variables to track min and max likes/comments
        min_likes = float('inf')
        max_likes = float('-inf')
        min_comments = float('inf')
        max_comments = float('-inf')
        min_engagement = float('inf')
        max_engagement = float('-inf')

        # Iterate over the posts
        for post_id, post_info in profile_data['posts'].items():
            likes = post_info["likes"]
            comments = post_info["comments"]

            # Calculate engagement rate for each post
            if profile_data["followers"] > 0:
                post_engagement_rate = round((likes + comments) / profile_data["followers"] * 100, 2)
            else:
                post_engagement_rate = 0

            # Update min and max engagement rates
            min_engagement = min(min_engagement, post_engagement_rate)
            max_engagement = max(max_engagement, post_engagement_rate)

            # Track min and max likes/comments
            min_likes = min(min_likes, post_info["likes"])
            max_likes = max(max_likes, post_info["likes"])
            min_comments = min(min_comments, post_info["comments"])
            max_comments = max(max_comments, post_info["comments"])


        # Normalize average likes and comments
        def normalize(value, min_value, max_value):
            if max_value > min_value:
                return (value - min_value) / (max_value - min_value)
            else:
                return 0  # Avoid division by zero

        if min_engagement != float('inf') and max_engagement != float('-inf'):
            for post_id, post_info in profile_data['posts'].items():
                normalized_engagement_rate = round(normalize(engagement_rate, min_engagement, max_engagement), 2)
        else:
            # Set normalized engagement rate to 0 if no valid engagement rates are found
            for post_id, post_info in profile_data['posts'].items():
                normalized_engagement_rate = 0

        normalized_avg_likes = normalize(average_likes, min_likes, max_likes)
        normalized_avg_comments = normalize(average_comments, min_comments, max_comments)

        # Calculate time intervals between posts in days

        post_dates = [datetime.fromisoformat(post["date"]).date() for post in profile_data["posts"].values()]
        post_dates.sort()

        intervals = []
        for i in range(1, len(post_dates)):
            interval = (post_dates[i] - post_dates[i - 1]).days  # Interval in days
            intervals.append(interval)

        if intervals:
            average_interval = np.mean(intervals)
            std_dev_interval = np.std(intervals)

            # Calculate consistency score
            if average_interval > 0:
                normalized_sd = std_dev_interval / average_interval
                consistency_score = max(0, 1 - normalized_sd)  # Ensure score is between 0 and 1
        
        influencer_score = ((0.9 * normalized_engagement_rate) + (0.75 * normalized_avg_likes) + (0.6 * normalized_avg_comments) + (0.75 * consistency_score)) * 100
        profile_data["influencer_score"] = round(influencer_score, 2)

        return profile_data

    except instaloader.exceptions.ProfileNotExistsException:
        print("Error: Profile not found")
        return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None
    
def save_to_mongodb(profile_data: dict):
    try:
        # Establish connection to MongoDB
        client = MongoClient(mongodb_uri)
        db = client["test"]
        collection = db["instagram_profiles"]

        # Debugging: Check connection
        print("Connected to MongoDB")

        # Create filter and update data
        filter_query = {"username": profile_data["username"]}
        update_data = {"$set": profile_data}

        # Update the document if it exists, otherwise insert a new one
        result = collection.update_one(filter_query, update_data, upsert=True)

        if result.matched_count > 0:
            print(f"Document with username '{profile_data['username']}' updated.")
        else:
            print(f"New document inserted with username '{profile_data['username']}'.")

    except Exception as e:
        print(f"An error occurred while saving to MongoDB: {e}")

if __name__ == "__main__":
    username = input("Enter the Instagram username to scrape: ")
    profile_data = calculate_engagement_rate(username)
    if profile_data:
        save_to_mongodb(profile_data)