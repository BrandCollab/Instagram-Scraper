import instaloader
from fastapi import FastAPI, HTTPException
import time
import random
import logging

app = FastAPI()

# Set up logging
logging.basicConfig(level=logging.INFO)

def scrape_instagram_profile(username: str) -> dict:
    try:
        logging.info(f"Starting to scrape profile: {username}")

        # Initialize instaloader
        loader = instaloader.Instaloader()

        # Introduce random delay to avoid rate limiting
        time.sleep(random.uniform(1, 3))

        # Load the profile
        profile = instaloader.Profile.from_username(loader.context, username)

        # Create a dictionary to hold profile information
        profile_data = {
            "username": profile.username,
            "full_name": profile.full_name,
            "biography": profile.biography,
            "profile_pic": profile.profile_pic_url,
            "is_verified": profile.is_verified,
            "business_category_name": profile.business_category_name,
            "followers": profile.followers,
            "following": profile.followees,
            "number_of_posts": profile.mediacount,
            "top_posts": {},
            "posts": {},
        }

        logging.info(f"Profile data retrieved for: {username}")

        # Store all posts to find the top posts by likes later
        all_posts = []

        # Iterate over posts with a random delay, limiting to 9 posts for quicker execution
        for idx, post in enumerate(profile.get_posts(), start=1):
            if idx > 5:  # Limit to 9 posts
                break
            time.sleep(random.uniform(0.5, 1.5))  # Reduced random delay between requests

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

            profile_data["posts"][idx] = post_data
            all_posts.append(post_data)

        # Sort all posts by the number of likes in descending order
        all_posts.sort(key=lambda x: x['likes'], reverse=True)

        # Get the top 3 posts with highest likes
        for idx, post in enumerate(all_posts[:3], start=1):
            profile_data["top_posts"][idx] = post

        logging.info(f"Finished scraping profile: {username}")

        return profile_data

    except instaloader.exceptions.ProfileNotExistsException:
        raise HTTPException(status_code=404, detail="Profile not found")
    except instaloader.exceptions.ConnectionException as ce:
        raise HTTPException(status_code=503, detail="Instagram is blocking requests temporarily. Please try again later.")
    except Exception as e:
        logging.error(f"Error scraping profile {username}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/scrape/{username}")
async def scrape_profile(username: str):
    profile_data = scrape_instagram_profile(username)
    return profile_data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
