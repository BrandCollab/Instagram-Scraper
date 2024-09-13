import instaloader
import time
import random
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from instagram_engagement_rate import calculate_engagement_rate
from datetime import datetime
import numpy as np

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
        
        average_likes = engagement_data['average_likes']
        average_comments = engagement_data['average_comments']
        engagement_rate = engagement_data['engagement_rate']

        # influencer score calculation
        

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
            "average_likes": average_likes,
            "average_comments":average_comments,
            "engagement_rate": f"{engagement_rate} %",
            "recent_top_posts": {},
            "posts": {},
        }


        # Initialize variables to track min and max likes/comments
        min_likes = float('inf')
        max_likes = float('-inf')
        min_comments = float('inf')
        max_comments = float('-inf')
        min_engagement = float('inf')
        max_engagement = float('-inf')

        # Store all posts to find the top posts by likes later
        all_posts = []

        # Iterate over posts with a random delay, limit to 12 posts
        for idx, post in enumerate(profile.get_posts(), start=1):
            if idx > 12:  # Limit to 12 posts
                break
            time.sleep(random.uniform(1, 3))  # random delay between requests

            likes = post.likes
            comments = post.comments

            # Calculate engagement rate for each post
            if profile.followers > 0:
                post_engagement_rate = round(((likes + comments) / profile.followers) * 100, 2)
            else:
                post_engagement_rate = 0

            # Update min and max engagement rates
            min_engagement = min(min_engagement, post_engagement_rate)
            max_engagement = max(max_engagement, post_engagement_rate)

            post_data = {
                "post_url": f"https://www.instagram.com/p/{post.shortcode}/",
                "caption": post.caption,
                "likes": post.likes,
                "comments": post.comments,
                "caption_hashtags": post.caption_hashtags,
                "sponsored_post": post.is_sponsored,
                "media_type": post.typename,
                "date": post.date.strftime('%Y-%m-%d'),
                "media_urls": []
            }

            if post.typename == 'GraphImage':
                post_data["media_urls"].append(post.url)
            elif post.typename == 'GraphVideo':
                post_data["media_urls"].append(post.url)
            elif post.typename == 'GraphSidecar':
                for sidecar_node in post.get_sidecar_nodes():
                    post_data["media_urls"].append(sidecar_node.display_url)

            # Track min and max likes/comments
            min_likes = min(min_likes, post_data["likes"])
            max_likes = max(max_likes, post_data["likes"])
            min_comments = min(min_comments, post_data["comments"])
            max_comments = max(max_comments, post_data["comments"])

            # Convert integer index to string for MongoDB
            profile_data["posts"][str(idx)] = post_data
            all_posts.append(post_data)

         # Normalize average likes and comments
        def normalize(value, min_value, max_value):
            if max_value > min_value:
                return (value - min_value) / (max_value - min_value)
            else:
                return 0  # Avoid division by zero

        if min_engagement != float('inf') and max_engagement != float('-inf'):
            for post_data in profile_data["posts"].values():
                normalized_engagement_rate = round(normalize(engagement_rate, min_engagement, max_engagement), 2)
        else:
            # Set normalized engagement rate to 0 if no valid engagement rates are found
            for post_data in profile_data["posts"].values():
                normalized_engagement_rate = 0

        normalized_avg_likes = normalize(average_likes, min_likes, max_likes)
        normalized_avg_comments = normalize(average_comments, min_comments, max_comments)

        # Sort all posts by the number of likes in descending order
        all_posts.sort(key=lambda x: x['likes'], reverse=True)

        # Get the top 3 posts with highest likes
        for idx, post in enumerate(all_posts[:3], start=1):
            profile_data["recent_top_posts"][str(idx)] = post  # Convert index to string

        # Calculate time intervals between posts in days
        post_dates = [datetime.strptime(post["date"], '%Y-%m-%d') for post in profile_data["posts"].values()]
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

        influencer_score = (0.3 * normalized_engagement_rate) + (0.25 * normalized_avg_likes) + (0.2 * normalized_avg_comments) + (0.25 * consistency_score)
        profile_data["influencer_score"] = round(influencer_score, 2)

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
    profile_data = scrape_instagram_profile(username)
    if profile_data:
        save_to_mongodb(profile_data)
