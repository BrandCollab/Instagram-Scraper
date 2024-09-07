import instaloader
import time
import random
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from instagram_engagement_rate import calculate_engagement_rate

# Load environment variables from .env file
load_dotenv()

# Get MongoDB connection details from environment variables
mongodb_uri = os.getenv("MONGODB_URI")

def scrape_instagram_profile(username: str) -> dict:
    try:
        # Initialize instaloader
        loader = instaloader.Instaloader()

        # Introduce random delay to avoid rate limiting
        time.sleep(random.uniform(2, 5))

        # Load the profile
        profile = instaloader.Profile.from_username(loader.context, username)

        # Get engagement rate
        engagement_data = calculate_engagement_rate(username)
        if engagement_data is None:
            return None

        # Create a dictionary to hold profile information
        profile_data = {
            "username": profile.username,
            "full_name": profile.full_name,
            "biography": profile.biography,
            "profile_pic": profile.profile_pic_url,
            "is_verified": profile.is_verified,
            # "business_category_name": profile.business_category_name,
            "followers": profile.followers,
            "following": profile.followees,
            "number_of_posts": profile.mediacount,
            "average_likes": engagement_data['average_likes'],
            "average_comments": engagement_data['average_comments'],
            "engagement_rate": f"{engagement_data['engagement_rate']} %",
            "top_posts": {},
            "posts": {},
        }

        # Store all posts to find the top posts by likes later
        all_posts = []

        # Iterate over posts with a random delay, limit to 12 posts
        for idx, post in enumerate(profile.get_posts(), start=1):
            if idx > 12:  # Limit to 12 posts
                break
            time.sleep(random.uniform(1, 3))  # random delay between requests
            post_data = {
                "post_url": f"https://www.instagram.com/p/{post.shortcode}/",
                "caption": post.caption,
                "likes": post.likes,
                "comments": post.comments,
                "caption_hashtags": post.caption_hashtags,
                "sponsored_post": post.is_sponsored,
                "media_type": post.typename,
                "date": post.date.isoformat(),
                "media_urls": []
            }

            if post.typename == 'GraphImage':
                post_data["media_urls"].append(post.url)
            elif post.typename == 'GraphVideo':
                post_data["media_urls"].append(post.url)
            elif post.typename == 'GraphSidecar':
                for sidecar_node in post.get_sidecar_nodes():
                    post_data["media_urls"].append(sidecar_node.display_url)

            # Convert integer index to string for MongoDB
            profile_data["posts"][str(idx)] = post_data
            all_posts.append(post_data)

        # Sort all posts by the number of likes in descending order
        all_posts.sort(key=lambda x: x['likes'], reverse=True)

        # Get the top 3 posts with highest likes
        for idx, post in enumerate(all_posts[:3], start=1):
            profile_data["top_posts"][str(idx)] = post  # Convert index to string

        return profile_data
    except instaloader.exceptions.ProfileNotExistsException:
        print("Error: Profile not found")
        return None
    except instaloader.exceptions.ConnectionException as ce:
        print("Error: Instagram is blocking requests temporarily. Please try again later.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def save_to_mongodb(profile_data: dict):
    try:
        # Establish connection to MongoDB
        client = MongoClient(mongodb_uri)
        db = client["test"]
        collection = db["instagram_profiles"]

        # Debugging: Check connection
        print("Connected to MongoDB")

        # Insert the document
        result = collection.insert_one(profile_data)  # Insert a new document

        print(f"New document inserted with ID: {result.inserted_id}")
        
    except Exception as e:
        print(f"An error occurred while saving to MongoDB: {e}")

if __name__ == "__main__":
    username = input("Enter the Instagram username to scrape: ")
    profile_data = scrape_instagram_profile(username)
    if profile_data:
        save_to_mongodb(profile_data)
