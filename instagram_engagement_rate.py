import instaloader

def calculate_engagement_rate(username: str) -> dict:
    try:
        # Initialize instaloader
        loader = instaloader.Instaloader()

        # Load the profile
        profile = instaloader.Profile.from_username(loader.context, username)

        # Variables to hold total likes and comments for calculating averages
        total_likes = 0
        total_comments = 0
        post_count = 0

        # Iterate over the latest 12 posts
        for post in profile.get_posts():
            if post_count >= 12:
                break
            total_likes += post.likes
            total_comments += post.comments
            post_count += 1

        # Calculate average likes and comments
        average_likes = round((total_likes / post_count), 2) if post_count > 0 else 0
        average_comments = round(total_comments / post_count, 2) if post_count > 0 else 0

        # Calculate engagement rate
        engagement_rate = round(((average_likes + average_comments) / profile.followers) * 100 if profile.followers > 0 else 0, 2)

        return {
            "average_likes": average_likes,
            "average_comments": average_comments,
            "engagement_rate": engagement_rate
        }

    except instaloader.exceptions.ProfileNotExistsException:
        print("Error: Profile not found")
        return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None
