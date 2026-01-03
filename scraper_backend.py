"""
Data scraper - Run this once to scrape and cache NBA stats data
The scraped data is saved to JSON files that the Flask backend can load instantly
"""
import json
import time
from playerstyles1 import get_offensive_stats, get_defensive_stats

offensive_play_types = {
    "Pick-and-Roll": "https://www.nba.com/stats/players/ball-handler?dir=D&sort=PTS",
    "Isolation": "https://www.nba.com/stats/players/isolation",
    "Transition": "https://www.nba.com/stats/players/transition",
    "Roll Man": "https://www.nba.com/stats/players/roll-man",
    "Post-Up": "https://www.nba.com/stats/players/playtype-post-up",
    "Spot-Up": "https://www.nba.com/stats/players/spot-up",
    "Cut": "https://www.nba.com/stats/players/cut",
    "Off Screen": "https://www.nba.com/stats/players/off-screen",
    "Putbacks": "https://www.nba.com/stats/players/putbacks",
    "Hand-Off": "https://www.nba.com/stats/players/hand-off"
}

defensive_play_types = {
    "Isolation": "https://www.nba.com/stats/teams/isolation?TypeGrouping=defensive&dir=A&sort=PPP",
    "Transition": "https://www.nba.com/stats/teams/transition?TypeGrouping=defensive&dir=A&sort=PPP",
    "Pick-and-Roll": "https://www.nba.com/stats/teams/ball-handler?TypeGrouping=defensive&dir=A&sort=PPP",
    "Roll Man": "https://www.nba.com/stats/teams/roll-man?TypeGrouping=defensive&dir=A&sort=PPP",
    "Post-Up": "https://www.nba.com/stats/teams/playtype-post-up?TypeGrouping=defensive&dir=A&sort=PPP",
    "Spot-Up": "https://www.nba.com/stats/teams/spot-up?TypeGrouping=defensive&dir=A&sort=PPP",
    "Hand-Off": "https://www.nba.com/stats/teams/hand-off?TypeGrouping=defensive&dir=A&sort=PPP",
    "Off Screen": "https://www.nba.com/stats/teams/off-screen?TypeGrouping=defensive&dir=A&sort=PPP",
    "Putbacks": "https://www.nba.com/stats/teams/putbacks?TypeGrouping=defensive&dir=A&sort=PPP"
}

def scrape_all_data():
    """Scrape all offensive and defensive stats and save to JSON files"""
    print("🏀 Starting data scraping...")
    start_time = time.time()
    
    # Scrape offensive stats
    print("\n📊 Scraping offensive stats...")
    offensive_cache = {}
    for play_type, url in offensive_play_types.items():
        print(f"  Scraping {play_type}...")
        stats = get_offensive_stats(url, play_type)
        if stats is not None:
            # Convert DataFrame to dict for JSON serialization
            offensive_cache[play_type] = stats.to_dict('records')
            print(f"    ✅ {len(stats)} players found")
        else:
            print(f"    ❌ Failed to scrape {play_type}")
    
    # Scrape defensive stats
    print("\n🛡️  Scraping defensive stats...")
    defensive_cache = {}
    for play_type, url in defensive_play_types.items():
        print(f"  Scraping {play_type} defense...")
        stats = get_defensive_stats(url, play_type)
        if stats is not None:
            # Convert DataFrame to dict for JSON serialization
            defensive_cache[play_type] = stats.to_dict('records')
            print(f"    ✅ {len(stats)} teams found")
        else:
            print(f"    ❌ Failed to scrape {play_type}")
    
    # Save to JSON files
    print("\n💾 Saving data to JSON files...")
    
    with open('offensive_cache.json', 'w') as f:
        json.dump(offensive_cache, f, indent=2)
    print("  ✅ Saved offensive_cache.json")
    
    with open('defensive_cache.json', 'w') as f:
        json.dump(defensive_cache, f, indent=2)
    print("  ✅ Saved defensive_cache.json")
    
    # Save timestamp
    cache_info = {
        "timestamp": time.time(),
        "offensive_types": len(offensive_cache),
        "defensive_types": len(defensive_cache),
        "total_time_seconds": time.time() - start_time
    }
    
    with open('cache_info.json', 'w') as f:
        json.dump(cache_info, f, indent=2)
    print("  ✅ Saved cache_info.json")
    
    elapsed = time.time() - start_time
    print(f"\n✅ Scraping complete! Took {elapsed:.1f} seconds")
    print(f"📦 Offensive play types: {len(offensive_cache)}")
    print(f"📦 Defensive play types: {len(defensive_cache)}")
    print("\nYou can now run flask_backend.py and it will load this data instantly!")

if __name__ == '__main__':
    scrape_all_data()