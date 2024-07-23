import instaloader
from fastapi import FastAPI, HTTPException

app = FastAPI()

def calculate_engagement_rate(username: str) -> dict:
    try:
        # Initialize instaloader
        loader = instaloader.Instaloader()

        # Load the profile
        profile = instaloader.Profile.from_username(loader.context, username)

        # Variables to hold total likes and comments for calculating averages
        total_likes = 0
        total_comments = 0

        # Iterate over posts
        for post in profile.get_posts():
            total_likes += post.likes
            total_comments += post.comments

        # Calculate average likes and comments
        average_likes = total_likes / profile.mediacount if profile.mediacount > 0 else 0
        average_comments = total_comments / profile.mediacount if profile.mediacount > 0 else 0

        # Calculate engagement rate
        engagement_rate = round(((average_likes + average_comments) / profile.followers) * 100 if profile.followers > 0 else 0,2)

        return engagement_rate
    
    except instaloader.exceptions.ProfileNotExistsException:
        raise HTTPException(status_code=404, detail="Profile not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/engagement_rate/{username}")
async def engagement_rate(username: str):
    engagement_rate = calculate_engagement_rate(username)
    return engagement_rate

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
