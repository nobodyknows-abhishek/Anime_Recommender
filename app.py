from flask import Flask, render_template, request, jsonify
import requests
import json
import os

app = Flask(__name__)

# Base URL for the Jikan API
JIKAN_API_URL = "https://api.jikan.moe/v4"

def get_anime_data(search_query):
    """
    Fetches anime data from the Jikan API (MyAnimeList unofficial API).

    Args:
        search_query (str): The name of the anime to search for.

    Returns:
        dict: A dictionary containing anime data if found, otherwise None.
    """
    api_url = f"{JIKAN_API_URL}/anime?q={search_query}&limit=5"
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

def recommend_anime_by_genre(anime_genres, num_recommendations=5):
    """
    Recommends anime based on shared genres.
    This is a very basic content-based recommendation system.

    Args:
        anime_genres (list): A list of genres from the user's favorite anime.
        num_recommendations (int): The number of recommendations to provide.

    Returns:
        list: A list of recommended anime titles.
    """
    if not anime_genres:
        return []

    print(f"\nLooking for anime similar to genres: {', '.join(anime_genres)}")
    recommended_titles = []
    seen_anime_ids = set() # To avoid recommending the same anime multiple times

    # Iterate through each genre to find related anime
    for genre in anime_genres:
        # Fetch anime by genre name (simplified approach for beginner project)
        # In a real application, you'd get genre IDs and use the /anime?genres={id} endpoint
        search_url = f"{JIKAN_API_URL}/anime?q={genre}&order_by=score&sort=desc&limit=20"

        try:
            response = requests.get(search_url)
            response.raise_for_status()
            data = response.json()

            if data and data.get('data'):
                for anime in data['data']:
                    anime_genres_list = [g['name'] for g in anime.get('genres', [])]
                    if any(g in anime_genres_list for g in anime_genres):
                        if anime['mal_id'] not in seen_anime_ids:
                            recommended_titles.append(anime['title'])
                            seen_anime_ids.add(anime['mal_id'])
                            if len(recommended_titles) >= num_recommendations:
                                return recommended_titles # Return once enough recommendations are found

        except requests.exceptions.RequestException as e:
            print(f"Error fetching genre-based recommendations: {e}")
        except json.JSONDecodeError:
            print("Error decoding JSON for genre recommendations.")
        except Exception as e:
            print(f"An unexpected error occurred during genre recommendation: {e}")

    return recommended_titles[:num_recommendations] # Ensure we don't return more than requested

@app.route('/', methods=['GET'])
def index():
    """
    Renders the main page of the application.
    """
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
            genres = [genre['name'] for genre in favorite_anime_data.get('genres', [])]
            if genres:
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
    # This ensures the Flask app can find the HTML template.
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
                background-color: #1a202c; /* Dark background */
                color: #e2e8f0; /* Light text */
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
        </style>
    </head>
    <body class="flex items-center justify-center min-h-screen p-4">
        <div class="bg-gray-800 p-8 rounded-lg shadow-xl w-full max-w-2xl">
            <h1 class="text-4xl font-bold text-center text-indigo-400 mb-6">
                <span class="inline-block transform rotate-3 mr-2">🌟</span> Anime Recommender <span class="inline-block transform -rotate-3 ml-2">🎬</span>
            </h1>
            <p class="text-center text-gray-400 mb-8">
                Discover new anime based on your favorites! Powered by Jikan API.
            </p>

            <form action="/recommend" method="post" class="mb-8 flex flex-col sm:flex-row gap-4">
                <input type="text" name="anime_name" placeholder="Enter an anime you enjoy (e.g., Naruto)"
                       class="flex-grow p-3 rounded-md bg-gray-700 border border-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-white placeholder-gray-400">
                <button type="submit"
                        class="px-6 py-3 bg-indigo-600 text-white font-semibold rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-gray-800 transition duration-300 ease-in-out transform hover:scale-105">
                    Get Recommendations
                </button>
            </form>

            {% if message %}
                <p class="text-center text-yellow-400 mb-6 font-medium">{{ message }}</p>
            {% endif %}

            {% if favorite_anime %}
                <div class="mb-8 bg-gray-700 p-6 rounded-lg shadow-md">
                    <h2 class="text-2xl font-semibold text-indigo-300 mb-4 flex items-center">
                        <span class="mr-2">💖</span> Your Anime: {{ favorite_anime.title }}
                    </h2>
                    <p class="text-gray-300 mb-2">
                        <span class="font-semibold text-gray-200">Score:</span> {{ favorite_anime.score if favorite_anime.score else 'N/A' }}
                    </p>
                    <p class="text-gray-300 mb-4">
                        <span class="font-semibold text-gray-200">Genres:</span>
                        {% for genre in favorite_anime.genres %}
                            <span class="inline-block bg-indigo-700 text-indigo-100 text-xs px-2 py-1 rounded-full mr-1 mb-1">{{ genre.name }}</span>
                        {% endfor %}
                    </p>
                    <p class="text-gray-400 text-sm leading-relaxed">
                        <span class="font-semibold text-gray-200">Synopsis:</span> {{ favorite_anime.synopsis[:250] }}...
                        <a href="{{ favorite_anime.url }}" target="_blank" class="text-indigo-400 hover:underline">Read more</a>
                    </p>
                </div>
            {% endif %}

            {% if recommendations %}
                <div class="bg-gray-700 p-6 rounded-lg shadow-md">
                    <h2 class="text-2xl font-semibold text-green-300 mb-4 flex items-center">
                        <span class="mr-2">✨</span> Recommended Anime:
                    </h2>
                    <ul class="list-disc list-inside text-gray-300 space-y-2">
                        {% for rec_title in recommendations %}
                            <li class="flex items-center">
                                <span class="text-green-400 mr-2">•</span> {{ rec_title }}
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

    # Run the Flask application
    # debug=True allows for automatic reloading on code changes and provides a debugger.
    app.run(debug=True)
