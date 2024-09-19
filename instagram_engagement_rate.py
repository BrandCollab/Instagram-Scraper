import instaloader
from pymongo import MongoClient
from dotenv import load_dotenv
import os

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
        
        # Variables to hold total likes and comments for calculating averages
        total_likes = 0
        total_comments = 0

        # Iterate over the posts
        for post_id, post_info in profile_data['posts'].items():
            total_likes += post_info["likes"]
            total_comments += post_info["comments"]

        # Calculate average likes and comments
        average_likes = round((total_likes / 12), 2) 
        average_comments = round(total_comments / 12, 2) 

        # Calculate engagement rate
        engagement_rate = round(((average_likes + average_comments) / profile_data["followers"]) * 100 if profile_data["followers"] > 0 else 0, 2)

        profile_data["average_likes"] = average_likes
        profile_data["average_comments"] = average_comments
        profile_data["engagement_rate"] = engagement_rate
        
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