
# Anime Nexus: Intelligent Anime Recommendation System

Anime Nexus is a modern web application built with Python Flask that provides personalized anime recommendations. It intelligently suggests new anime titles by analyzing genres of a user's favorite anime and leveraging the Jikan API (an unofficial MyAnimeList API) for comprehensive data retrieval. The application features a sleek, responsive user interface designed with Tailwind CSS, enhancing user experience and showcasing full-stack development capabilities.

## Features

- Modern Web UI: Intuitive and visually appealing interface built with Flask and styled using Tailwind CSS for a responsive design.

- Intelligent Genre Matching: Fetches and maps official anime genre IDs from the Jikan API for highly accurate genre-based recommendations.

+ Advanced Recommendation Logic: Recommends anime by calculating genre overlap with the user's favorite title, prioritizing titles with more shared genres and higher scores.

+ Robust API Integration: Seamlessly interacts with the Jikan API to retrieve real-time anime details (title, synopsis, score, genres).

- Error Handling & Rate Limiting: Implements robust error handling for API requests and incorporates delays to respect API rate limits.

- Dynamic Content Display: Displays detailed information about the user's chosen anime and a curated list of recommendations.

## Tech Stack

**Backend:** 
- Python 3.x 
- Flask (Web Framework)
- requests library (HTTP requests to API)

- json library (JSON data handling)

**Frontend:** 
- HTML5

- Tailwind CSS 

- Jinja2 


## API Reference

Jikan API (Unofficial MyAnimeList API: https://jikan.moe/)
## Future Enhancements 
- User Authentication

- More Advanced Recommendation Models

- Dynamic Content Loading
- Search Autocomplete

- User Ratings
