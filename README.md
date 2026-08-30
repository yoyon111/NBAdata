# NBA Data & Player Analysis

An NBA data project that collects basketball statistics, processes player and team data, and provides an interface for exploring player-versus-team performance.

## Overview

NBAdata combines web scraping, data processing, a Flask backend, AI-assisted analysis, and a web interface to explore NBA statistics.

The project collects NBA data and transforms it into information that can be used for player and team comparisons.

## Features

- NBA data scraping
- Player statistics
- Player-versus-team analysis
- AI-assisted analysis
- JSON-based data storage
- Flask backend
- Web interface
- Automated data collection

## Architecture

NBA Data Sources
↓
Web Scrapers
↓
Raw NBA Data
↓
JSON Data
↓
Flask Backend
↓
AI Analysis
↓
Web Interface

## Project Structure

### playerstyles1.py

Handles the collection of NBA data.

### scraper_backend.py

Runs the scraping workflow and stores collected NBA data in JSON format.

### flask_backend.py

Provides backend functionality for accessing the collected data and running analysis.

### playervsteams.html

Provides the frontend interface for exploring player-versus-team information.

## Example Use Cases

The application can be used to explore questions such as:

- How does a player perform against a particular team?
- What are a player's historical statistics?
- How do different players compare?
- What patterns can be found in NBA data?
- How does a player's performance change against different opponents?

## Tech Stack

- Python
- Flask
- Web Scraping
- JSON
- HTML
- JavaScript
- AI Agents

## Setup

### Clone the repository

    git clone https://github.com/yoyon111/NBAdata.git
    cd NBAdata

### Install dependencies

    pip install -r requirements.txt

### Run the backend

    python flask_backend.py

Then open the web interface in your browser.

## Future Improvements

Potential improvements include:

- Additional NBA statistics
- More player comparisons
- Interactive charts
- Advanced AI analysis
- Automated data updates
- Player dashboards
- Team dashboards
- Historical trend analysis

## Status

This project is a work in progress exploring sports data collection, web scraping, backend development, and AI-assisted analytics.
