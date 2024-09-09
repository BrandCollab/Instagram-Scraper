import instaloader
import requests
from bs4 import BeautifulSoup
from instagram_engagement_rate import calculate_engagement_rate
from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Initialize instaloader
loader = instaloader.Instaloader()

# Get MongoDB connection details from environment variables
mongodb_uri = os.getenv("MONGODB_URI")

def get_top_50_instagram_accounts() -> list:
    try:
        url = "https://en.wikipedia.org/wiki/List_of_most-followed_Instagram_accounts"
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        accounts_table = soup.find('table', {'class': 'wikitable'})
        rows = accounts_table.find_all('tr')

        accounts = []
        for index, row in enumerate(rows[1:51], start=1):  # Skipping the header row and limiting to top 50
            cols = row.find_all('td')
            rank = index
            account_name = cols[1].text.strip()
            username = cols[0].text.strip().lstrip("@")

            accounts.append({
                "rank": rank,
                "username": username,
                "account_name": account_name
            })

        return accounts
    except Exception as e:
        print(f"Error fetching Instagram accounts: {e}")
        return []

def process_batch(batch):
    batch_results = []
    for account in batch:
        try:
            username = account["username"]
            engagement_data = calculate_engagement_rate(username)

            # Load the profile
            profile = instaloader.Profile.from_username(loader.context, username)
            followers = profile.followers
            following = profile.followees
            total_posts = profile.mediacount
            profile_link = f"https://www.instagram.com/{username}/"

            batch_results.append({
                "rank": account["rank"],
                "username": username,
                "account_name": account["account_name"],
                "profile_link": profile_link,
                "followers": followers,
                "following": following,
                "total_posts": total_posts,
                "engagement_rate": f"{engagement_data['engagement_rate']} %"
            })
        except Exception as e:
            print(f"Error processing account {username}: {e}")
            continue
    return batch_results


def save_to_mongodb(all_results: list):
    try:
        # Establish connection to MongoDB
        client = MongoClient(mongodb_uri)
        db = client["test"]
        collection = db["top_50_instagram_accounts"]

        # Debugging: Check connection
        print("Connected to MongoDB")

        # Insert multiple documents
        if all_results:
            result = collection.insert_many(all_results)  # Insert a batch of documents
            print(f"Inserted {len(result.inserted_ids)} documents into MongoDB")
        
    except Exception as e:
        print(f"An error occurred while saving to MongoDB: {e}")

def main():
    accounts = get_top_50_instagram_accounts()
    if not accounts:
        print("No accounts found.")
        return

    # Process accounts in batches of 5
    batches = [accounts[i:i + 5] for i in range(0, len(accounts), 5)]
    all_results = []

    for batch in batches:
        batch_results = process_batch(batch)
        all_results.extend(batch_results)

    # Save results to MongoDB
    save_to_mongodb(all_results)

    # Print the results
    print(all_results)  # Print all_results

if __name__ == "__main__":
    main()               