# app.py
from flask import Flask, render_template, request, jsonify
import requests
import json
import os
import time # For adding a small delay to respect API rate limits

app = Flask(__name__)

# Base URL for the Jikan API
JIKAN_API_URL = "https://api.jikan.moe/v4"

# Global variable to store genre map (initialized once)
# This avoids fetching the genre list repeatedly
GENRE_NAME_TO_ID_MAP = {}

def get_genre_map():
    """
    Fetches all anime genres from Jikan API and creates a name-to-ID map.
    This helps in accurate genre-based filtering.
    """
    global GENRE_NAME_TO_ID_MAP
    if GENRE_NAME_TO_ID_MAP: # If already populated, return it
        return GENRE_NAME_TO_ID_MAP

    print("Fetching anime genre list...")
    genre_api_url = f"{JIKAN_API_URL}/genres/anime"
    try:
        response = requests.get(genre_api_url)
        response.raise_for_status()
        data = response.json()

        if data and data.get('data'):
            for genre in data['data']:
                GENRE_NAME_TO_ID_MAP[genre['name'].lower()] = genre['mal_id']
            print(f"Successfully fetched {len(GENRE_NAME_TO_ID_MAP)} genres.")
            return GENRE_NAME_TO_ID_MAP
        else:
            print("No genre data found from API.")
            return {}
    except requests.exceptions.RequestException as e:
        print(f"Error fetching genre list from Jikan API: {e}")
        return {}
    except json.JSONDecodeError:
        print("Error decoding JSON response for genres from API.")
        return {}
    except Exception as e:
        print(f"An unexpected error occurred while fetching genres: {e}")
        return {}

def get_anime_data(search_query):
    """
    Fetches anime data from the Jikan API (MyAnimeList unofficial API).

    Args:
        search_query (str): The name of the anime to search for.

    Returns:
        dict: A dictionary containing anime data if found, otherwise None.
    """
    api_url = f"{JIKAN_API_URL}/anime?q={search_query}&limit=10"
    print(f"Searching for anime: '{search_query}'...")

    try:
        response = requests.get(api_url)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        data = response.json()

        if data and data.get('data'):
            return data['data'][0] # Return the first result's data
        else:
            print(f"No anime found for '{search_query}'.")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Jikan API: {e}")
        return None
    except json.JSONDecodeError:
        print("Error decoding JSON response from API.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def recommend_anime_by_genre(favorite_anime_genre_names, num_recommendations=10):
    """
    Recommends anime based on shared genres using genre IDs for better accuracy.

    Args:
        favorite_anime_genre_names (list): A list of genre names from the user's favorite anime.
        num_recommendations (int): The number of recommendations to provide.

    Returns:
        list: A list of recommended anime titles, sorted by genre overlap.
    """
    if not favorite_anime_genre_names:
        return []

    genre_map = get_genre_map()
    if not genre_map:
        print("Cannot recommend: Genre map not available.")
        return []

    # Convert favorite anime genre names to their corresponding IDs
    favorite_anime_genre_ids = [
        genre_map[g.lower()] for g in favorite_anime_genre_names if g.lower() in genre_map
    ]

    if not favorite_anime_genre_ids:
        print("No valid genre IDs found for your favorite anime.")
        return []

    print(f"\nLooking for anime similar to genres (IDs): {favorite_anime_genre_ids}")
    
    # Use a dictionary to store potential recommendations with their genre overlap count
    # {anime_id: {'title': 'Anime Title', 'overlap_count': X}}
    potential_recommendations = {}
    
    # To avoid hitting rate limits, we'll fetch a broad list and then filter/score
    # We can query by multiple genre IDs (comma-separated) for a more targeted search
    # However, Jikan's /anime endpoint only takes one genre ID at a time in the 'genres' parameter.
    # So, we'll iterate through the top genres and combine results.

    # Prioritize searching by the most relevant genres first (e.g., first 3-5)
    genres_to_query = favorite_anime_genre_ids[:7] # Limit to top few genres for API calls

    for genre_id in genres_to_query:
        # Search for anime by specific genre ID, ordered by score
        search_url = f"{JIKAN_API_URL}/anime?genres={genre_id}&order_by=score&sort=desc&limit=25"
        
        try:
            response = requests.get(search_url)
            response.raise_for_status()
            data = response.json()

            if data and data.get('data'):
                for anime in data['data']:
                    anime_id = anime['mal_id']
                    if anime_id in potential_recommendations:
                        continue # Already processed this anime

                    # Get genres of the current anime being considered
                    current_anime_genres = [g['mal_id'] for g in anime.get('genres', [])]
                    
                    # Calculate genre overlap with the user's favorite anime's genres
                    overlap_count = len(set(favorite_anime_genre_ids).intersection(current_anime_genres))

                    if overlap_count > 0: # Only consider if there's at least one shared genre
                        potential_recommendations[anime_id] = {
                            'title': anime['title'],
                            'overlap_count': overlap_count,
                            'score': anime.get('score', 0) # Include score for secondary sorting
                        }
            time.sleep(0.5) # Be kind to the API, add a small delay between requests
        except requests.exceptions.RequestException as e:
            print(f"Error fetching genre-based recommendations for genre ID {genre_id}: {e}")
        except json.JSONDecodeError:
            print(f"Error decoding JSON for genre ID {genre_id} recommendations.")
        except Exception as e:
            print(f"An unexpected error occurred during genre recommendation for genre ID {genre_id}: {e}")

    # Sort potential recommendations:
    # 1. By overlap count (descending)
    # 2. By score (descending)
    sorted_recommendations = sorted(
        potential_recommendations.values(),
        key=lambda x: (x['overlap_count'], x['score']),
        reverse=True
    )

    # Extract titles up to the requested number of recommendations
    recommended_titles = [rec['title'] for rec in sorted_recommendations[:num_recommendations]]
    return recommended_titles

@app.route('/', methods=['GET'])
def index():
    """
    Renders the main page of the application.
    """
    # Ensure genre map is loaded when the app starts or index page is accessed
    get_genre_map()
    return render_template('index.html',
                           favorite_anime=None,
                           recommendations=None,
                           message="Enter an anime you enjoy to get recommendations!")

@app.route('/recommend', methods=['POST'])
def recommend():
    """
    Handles the anime recommendation request from the UI.
    """
    user_anime_name = request.form.get('anime_name')
    message = ""
    favorite_anime_data = None
    recommendations = None

    if not user_anime_name:
        message = "Please enter an anime name."
    else:
        favorite_anime_data = get_anime_data(user_anime_name)

        if favorite_anime_data:
            # Extract genre names (strings) from the favorite anime data
            genres = [genre['name'] for genre in favorite_anime_data.get('genres', [])]
            
            if genres:
                # Pass genre names to the recommendation function
                recommendations = recommend_anime_by_genre(genres, num_recommendations=5)
                if not recommendations:
                    message = "Could not find suitable recommendations based on your anime's genres."
            else:
                message = "Could not find genres for your chosen anime, so no recommendations can be made."
        else:
            message = f"Could not find details for '{user_anime_name}'. Please try another name."

    return render_template('index.html',
                           favorite_anime=favorite_anime_data,
                           recommendations=recommendations,
                           message=message)

if __name__ == '__main__':
    # Create the 'templates' directory if it doesn't exist
    templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    os.makedirs(templates_dir, exist_ok=True)

    # Define the content for index.html
    index_html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Anime Recommender</title>
        <!-- Tailwind CSS CDN for easy styling -->
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            /* Custom styles for Inter font and background */
            body {
                font-family: 'Inter', sans-serif;
                background-color: #0d1117; /* Darker background, GitHub-like */
                color: #c9d1d9; /* Lighter text for contrast */
                background-image: radial-gradient(at 0% 0%, hsla(215, 80%, 20%, 0.3) 0, transparent 50%),
                                  radial-gradient(at 100% 100%, hsla(280, 80%, 20%, 0.3) 0, transparent 50%);
            }
            /* Custom scrollbar for better aesthetics */
            ::-webkit-scrollbar {
                width: 8px;
            }
            ::-webkit-scrollbar-track {
                background: #2d3748; /* Darker track */
                border-radius: 10px;
            }
            ::-webkit-scrollbar-thumb {
                background: #4a5568; /* Lighter thumb */
                border-radius: 10px;
            }
            ::-webkit-scrollbar-thumb:hover {
                background: #6b7280; /* Even lighter on hover */
            }
            /* Keyframe for subtle pulse animation on button */
            @keyframes pulse-once {
                0% { transform: scale(1); }
                50% { transform: scale(1.02); }
                100% { transform: scale(1); }
            }
            .animate-pulse-once {
                animation: pulse-once 0.5s ease-in-out;
            }
        </style>
    </head>
    <body class="flex items-center justify-center min-h-screen p-4">
        <div class="bg-gray-900 bg-opacity-80 backdrop-blur-sm p-8 rounded-xl shadow-2xl w-full max-w-2xl border border-gray-700">
            <h1 class="text-5xl font-extrabold text-center text-purple-400 mb-4 animate-fade-in-down">
                <span class="inline-block transform rotate-6 mr-3 text-yellow-300">✨</span> Anime Nexus <span class="inline-block transform -rotate-6 ml-3 text-pink-300">🌌</span>
            </h1>
            <p class="text-center text-gray-400 text-lg mb-8">
                Your gateway to discovering new anime. 
            </p>

            <form action="/recommend" method="post" class="mb-10 flex flex-col sm:flex-row gap-4">
                <input type="text" name="anime_name" placeholder="Enter an anime you love (e.g.One Piece)"
                       class="flex-grow p-4 rounded-lg bg-gray-700 border border-gray-600 focus:outline-none focus:ring-3 focus:ring-purple-500 text-white placeholder-gray-400 text-lg transition duration-300 ease-in-out">
                <button type="submit"
                        class="px-8 py-4 bg-gradient-to-r from-purple-600 to-indigo-600 text-white font-bold rounded-lg shadow-lg hover:shadow-xl focus:outline-none focus:ring-3 focus:ring-purple-500 focus:ring-offset-2 focus:ring-offset-gray-900 transition duration-300 ease-in-out transform hover:scale-105 active:scale-95 animate-pulse-once">
                    Find My Next Anime!
                </button>
            </form>

            {% if message %}
                <p class="text-center text-yellow-300 mb-8 text-xl font-semibold bg-gray-800 p-3 rounded-md border border-yellow-500">{{ message }}</p>
            {% endif %}

            {% if favorite_anime %}
                <div class="mb-8 bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-700 transform transition duration-300 hover:scale-[1.01]">
                    <h2 class="text-3xl font-bold text-purple-300 mb-4 flex items-center">
                        <span class="mr-3 text-pink-400">💖</span> Your Anime: {{ favorite_anime.title }}
                    </h2>
                    <p class="text-gray-300 text-lg mb-2">
                        <span class="font-semibold text-gray-200">Score:</span>
                        <span class="text-yellow-400">{{ favorite_anime.score if favorite_anime.score else 'N/A' }}</span>
                    </p>
                    <div class="mb-4 flex flex-wrap gap-2">
                        <span class="font-semibold text-gray-200 text-lg">Genres:</span>
                        {% for genre in favorite_anime.genres %}
                            <span class="inline-block bg-purple-700 text-purple-100 text-sm px-3 py-1 rounded-full shadow-md">{{ genre.name }}</span>
                        {% endfor %}
                    </div>
                    <p class="text-gray-400 text-base leading-relaxed">
                        <span class="font-semibold text-gray-200">Synopsis:</span> {{ favorite_anime.synopsis[:250] }}...
                        <a href="{{ favorite_anime.url }}" target="_blank" class="text-purple-400 hover:underline font-medium">Read more on MyAnimeList</a>
                    </p>
                </div>
            {% endif %}

            {% if recommendations %}
                <div class="bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-700 transform transition duration-300 hover:scale-[1.01]">
                    <h2 class="text-3xl font-bold text-green-300 mb-4 flex items-center">
                        <span class="mr-3 text-cyan-400">✨</span> Recommended for You:
                    </h2>
                    <ul class="list-none text-gray-300 space-y-3">
                        {% for rec_title in recommendations %}
                            <li class="flex items-center bg-gray-700 p-3 rounded-md shadow-sm border border-gray-600">
                                <span class="text-green-400 mr-3 text-xl font-bold">»</span> {{ rec_title }}
                            </li>
                        {% endfor %}
                    </ul>
                </div>
            {% endif %}
        </div>
    </body>
    </html>
    """

    # Write the HTML content to index.html inside the templates directory
    with open(os.path.join(templates_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(index_html_content)

    # Initialize the genre map when the app starts
    get_genre_map()

    # Run the Flask application
    app.run(debug=True)
