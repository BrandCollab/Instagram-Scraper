import instaloader
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
import asyncio

app = FastAPI()

# Initialize instaloader
loader = instaloader.Instaloader()

def calculate_engagement_rate(username: str) -> dict:
    try:
        # Load the profile
        profile = instaloader.Profile.from_username(loader.context, username)

        # Variables to hold total likes and comments for calculating averages
        total_likes = 0
        total_comments = 0
        post_count = 0

        # Iterate over the latest 18 posts
        for post in profile.get_posts():
            if post_count >= 18:
                break
            total_likes += post.likes
            total_comments += post.comments
            post_count += 1

        # Calculate average likes and comments
        average_likes = total_likes / 18
        average_comments = total_comments / 18

        # Calculate engagement rate
        engagement_rate = round(((average_likes + average_comments) / profile.followers) * 100 if profile.followers > 0 else 0, 2)

        return engagement_rate
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
        raise HTTPException(status_code=500, detail=str(e))

async def process_batch(batch):
    batch_results = []
    for account in batch:
        try:
            username = account["username"]
            engagement_rate = calculate_engagement_rate(username)

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
                "engagement_rate": engagement_rate
            })
        except Exception as e:
            continue
    return batch_results

@app.get("/top_50_instagram_accounts")
async def top_50_instagram_accounts():
    accounts = get_top_50_instagram_accounts()
    batches = [accounts[i:i + 5] for i in range(0, len(accounts), 5)]

    results = []
    for batch in batches:
        batch_results = await process_batch(batch)
        results.extend(batch_results)

    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
