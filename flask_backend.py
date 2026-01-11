from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import time
import os
import pandas as pd
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from playerstyles1 import normalize_text

app = Flask(__name__)
CORS(app)

# Configure API Keys
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'YOUR_API_KEY_HERE')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
XAI_API_KEY = os.environ.get('XAI_API_KEY', '')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')

# Disable OpenAI requirement for CrewAI
os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY or 'not-needed'

# Cache storage - will be loaded from JSON files
offensive_cache = {}
defensive_cache = {}
cache_timestamp = None

def load_cache_from_json():
    """Load cached data from JSON files (instant load!)"""
    global offensive_cache, defensive_cache, cache_timestamp
    
    print("📂 Loading data from JSON files...")
    
    try:
        # Load offensive stats
        with open('offensive_cache.json', 'r') as f:
            offensive_data = json.load(f)
            # Convert back to DataFrame format
            offensive_cache = {
                play_type: pd.DataFrame(records) 
                for play_type, records in offensive_data.items()
            }
        print(f"  ✅ Loaded {len(offensive_cache)} offensive play types")
        
        # Load defensive stats
        with open('defensive_cache.json', 'r') as f:
            defensive_data = json.load(f)
            # Convert back to DataFrame format
            defensive_cache = {
                play_type: pd.DataFrame(records) 
                for play_type, records in defensive_data.items()
            }
        print(f"  ✅ Loaded {len(defensive_cache)} defensive play types")
        
        # Load cache info
        with open('cache_info.json', 'r') as f:
            cache_info = json.load(f)
            cache_timestamp = cache_info['timestamp']
        
        print(f"✅ Cache loaded successfully! Data from: {time.ctime(cache_timestamp)}")
        return True
        
    except FileNotFoundError as e:
        print(f"❌ JSON files not found! Please run scraper_backend.py first.")
        print(f"   Missing file: {e.filename}")
        return False
    except Exception as e:
        print(f"❌ Error loading cache: {e}")
        return False

@app.route('/api/player/<player_name>', methods=['GET'])
def get_player(player_name):
    """Get player offensive stats"""
    if not offensive_cache:
        return jsonify({"error": "Data not loaded. Please run scraper_backend.py first."}), 503
    
    search_normalized = normalize_text(player_name)
    player_data = []
    
    for play_type, df in offensive_cache.items():
        if 'PLAYER' in df.columns and 'PTS' in df.columns and 'TEAM' in df.columns:
            def matches_player(name):
                return search_normalized in normalize_text(name)
            
            player_stats = df[df['PLAYER'].apply(matches_player)]
            if not player_stats.empty:
                for _, row in player_stats.iterrows():
                    player_data.append({
                        "playType": play_type,
                        "team": row['TEAM'],
                        "pts": float(row['PTS']) if row['PTS'] else 0,
                        "player": row['PLAYER']
                    })
    
    if not player_data:
        return jsonify({"error": "Player not found"}), 404
    
    return jsonify({
        "player": player_data[0]["player"] if player_data else player_name,
        "data": player_data
    })

@app.route('/api/defense/<team_name>', methods=['GET'])
def get_defense(team_name):
    """Get team defensive stats"""
    if not defensive_cache:
        return jsonify({"error": "Data not loaded. Please run scraper_backend.py first."}), 503
    
    defense_data = []
    
    for play_type, df in defensive_cache.items():
        team_stats = df[df['TEAM'].str.contains(team_name, case=False, na=False)]
        if not team_stats.empty:
            for _, row in team_stats.iterrows():
                defense_data.append({
                    "playType": play_type,
                    "team": row['TEAM'],
                    "rank": int(row['RANK']),
                    "ppp": float(row['PPP']) if row['PPP'] else 0
                })
    
    if not defense_data:
        return jsonify({"error": "Team not found"}), 404
    
    return jsonify({
        "team": defense_data[0]["team"] if defense_data else team_name,
        "data": defense_data
    })

@app.route('/api/matchup/<player_name>/<team_name>', methods=['GET'])
def get_matchup(player_name, team_name):
    """Get player vs team matchup"""
    # Get player data
    player_response = get_player(player_name)
    if player_response[1] == 404:
        return player_response
    
    # Get defense data
    defense_response = get_defense(team_name)
    if defense_response[1] == 404:
        return defense_response
    
    player_json = player_response[0].get_json()
    defense_json = defense_response[0].get_json()
    
    return jsonify({
        "player": player_json,
        "defense": defense_json
    })

# CrewAI Tools
@tool("Search Recent NBA Info")
def search_recent_nba_info(query: str) -> str:
    """Search for recent NBA information using Gemini's web search capabilities.
    Use this to find recent player performance, injuries, team strategies, etc."""
    try:
        # Using ChatGoogleGenerativeAI for web search (langchain integration)
        search_llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=GEMINI_API_KEY,
            temperature=0.3
        )
        
        prompt = f"""Search the web for recent NBA information about: {query}
        
Provide a concise summary (2-3 sentences) of the most relevant and recent findings.
Focus on:
- Recent game performance (last 5-10 games)
- Current injuries or lineup changes
- Head-to-head matchup history
- Recent trends or momentum"""
        
        response = search_llm.invoke(prompt)
        return response.content
    except Exception as e:
        return f"Search failed: {str(e)}"

@tool("Analyze Statistical Matchup")
def analyze_statistical_matchup(player_stats: str, defense_stats: str) -> str:
    """Analyze the statistical matchup between player offense and team defense.
    Returns key insights about favorable/unfavorable matchups."""
    # This tool helps agents reason about the raw stats
    return f"""Statistical Analysis:
Player Stats: {player_stats}
Defense Stats: {defense_stats}

Key points to consider:
- Compare player's strongest play types vs defense's weakest areas
- Look for rank discrepancies (player excels where defense struggles)
- Consider PPP efficiency vs defensive PPP allowed"""

@app.route('/api/ai-analysis', methods=['POST'])
def ai_analysis():
    """CrewAI multi-agent collaborative analysis"""
    try:
        data = request.json
        player_name = data.get('playerName')
        team_name = data.get('teamName')
        player_stats = data.get('playerStats', [])
        defense_stats = data.get('defenseStats', [])
        
        if not player_name or not team_name:
            return jsonify({"error": "Missing player or team name"}), 400
        
        # Format stats for agents
        player_stats_text = ', '.join([
            f"{s['playType']}: {s['pts']:.1f} PTS" 
            for s in sorted(player_stats, key=lambda x: x['pts'], reverse=True)
        ])
        
        defense_stats_text = ', '.join([
            f"{s['playType']}: Rank #{s['rank']} ({s['ppp']:.2f} PPP)" 
            for s in sorted(defense_stats, key=lambda x: x['rank'])
        ])
        
        print(f"🤖 Starting CrewAI analysis for {player_name} vs {team_name}...")
        print("⏳ This may take 30-60 seconds...")
        
        # Configure 4 different LLMs for maximum diversity
        from crewai import LLM
        
        # Track which LLMs we're using
        llm_lineup = []
        
        # Analyst 1: Gemini 2.5 Flash (FREE - 1,500 req/day)
        llm_gemini = LLM(
            model="gemini/gemini-2.5-flash",
            api_key=GEMINI_API_KEY
        )
        llm_lineup.append("Gemini 2.5 Flash")
        
        # Analyst 2: OpenAI GPT-4o-mini (affordable)
        if OPENAI_API_KEY and OPENAI_API_KEY != 'not-needed':
            llm_openai = LLM(
                model="openai/gpt-4o-mini",
                api_key=OPENAI_API_KEY
            )
            llm_lineup.append("GPT-4o-mini")
        else:
            llm_openai = llm_gemini
            llm_lineup.append("Gemini (no OpenAI key)")
        
        # Analyst 3: Grok (you have Premium+!)
        if XAI_API_KEY:
            llm_grok = LLM(
                model="xai/grok-beta",
                api_key=XAI_API_KEY
            )
            llm_lineup.append("Grok (xAI)")
        else:
            llm_grok = llm_gemini
            llm_lineup.append("Gemini (no Grok key)")
        
        # Analyst 4: DeepSeek V3 (super cheap)
        if DEEPSEEK_API_KEY:
            llm_deepseek = LLM(
                model="deepseek/deepseek-chat",
                api_key=DEEPSEEK_API_KEY
            )
            llm_lineup.append("DeepSeek V3")
        else:
            llm_deepseek = llm_gemini
            llm_lineup.append("Gemini (no DeepSeek key)")
        
        manager_llm = llm_gemini  # Gemini manages the debate
        
        print(f"🤖 AI Panel: {' | '.join(llm_lineup)}")
        if len(set(llm_lineup)) == 1:
            print(f"💡 Tip: Add OPENAI_API_KEY, XAI_API_KEY, or DEEPSEEK_API_KEY for diverse perspectives!")
        
        # Define 4 Agents - each using a different LLM
        gemini_analyst = Agent(
            role='gemini sports analyst',
            goal=f'Provide an objective analysis of {player_name} vs {team_name} matchup',
            backstory=f"""You are a sports analyst examining the {player_name} vs {team_name} matchup. 
            Analyze the statistics objectively and provide your honest assessment. Look at the data, 
            search for recent performance if needed, and share your genuine analysis.""",
            verbose=True,
            allow_delegation=False,
            tools=[search_recent_nba_info, analyze_statistical_matchup],
            llm=llm_gemini
        )
        
        gpt_analyst = Agent(
            role='gpt sports analyst',
            goal=f'Provide an independent analysis of {player_name} vs {team_name} matchup',
            backstory=f"""You are a sports analyst examining the {player_name} vs {team_name} matchup. 
            Analyze the statistics objectively and provide your honest assessment. Look at the data 
            and share what the evidence tells you.""",
            verbose=True,
            allow_delegation=False,
            tools=[search_recent_nba_info, analyze_statistical_matchup],
            llm=llm_openai
        )
        
        grok_analyst = Agent(
            role='grok sports analyst',
            goal=f'Provide a bold, unfiltered analysis of {player_name} vs {team_name} matchup',
            backstory=f"""You are a sports analyst examining the {player_name} vs {team_name} matchup. 
            Give your honest, straightforward take. Don't sugarcoat it. Look at the data and tell it 
            like it is.""",
            verbose=True,
            allow_delegation=False,
            tools=[search_recent_nba_info, analyze_statistical_matchup],
            llm=llm_grok
        )
        
        deepseek_analyst = Agent(
            role='deepseek sports analyst',
            goal=f'Provide a thorough technical analysis of {player_name} vs {team_name} matchup',
            backstory=f"""You are a sports analyst examining the {player_name} vs {team_name} matchup. 
            Focus on the technical details and statistical patterns. Provide a comprehensive, 
            data-driven assessment.""",
            verbose=True,
            allow_delegation=False,
            tools=[search_recent_nba_info, analyze_statistical_matchup],
            llm=llm_deepseek
        )
        
        betting_synthesizer = Agent(
            role='betting recommendation synthesizer',
            goal='Synthesize all four analyses into actionable betting recommendations',
            backstory="""You listen to analyses from Gemini, GPT, Grok, and DeepSeek. Synthesize their 
            insights into clear betting recommendations. Note where they agree/disagree. Make specific, 
            confident recommendations with reasoning.""",
            verbose=True,
            allow_delegation=False,
            tools=[search_recent_nba_info],
            llm=llm_gemini
        )
        
        # Single collaborative debate task
        matchup_context = f"""
MATCHUP: {player_name} vs {team_name}

PLAYER OFFENSIVE STATS:
{player_stats_text}

TEAM DEFENSIVE STATS:
{defense_stats_text}
"""
        
        debate_task = Task(
            description=f"""{matchup_context}

ANALYSIS INSTRUCTIONS:
Four independent AI analysts will each provide their honest analysis of this matchup.

Gemini Analyst:
- Analyze the matchup objectively
- Search for recent player/team performance data
- Share your genuine assessment

GPT Analyst:
- Provide your independent systematic analysis
- Look for statistical patterns and trends
- Give your honest data-driven take

Grok Analyst:
- Give your bold, unfiltered analysis
- Don't hold back - tell it like you see it
- Be direct about strengths and weaknesses

DeepSeek Analyst:
- Examine the matchup from a technical perspective
- Focus on deep statistical patterns
- Provide thorough, analytical insights

Betting Synthesizer:
- Review all four AI analyses
- Identify consensus and disagreements
- Provide 2-3 specific betting recommendations with confidence levels

Each analyst works independently. No predetermined biases.

FINAL OUTPUT REQUIREMENTS:
- Summary of each AI's key findings
- Areas of consensus vs. disagreement
- 2-3 specific betting recommendations  
- Confidence levels (HIGH/MEDIUM/LOW) with reasoning""",
            agent=betting_synthesizer,
            expected_output="""A comprehensive betting analysis that includes:
1. Gemini's analysis and key insights
2. GPT's analysis and key insights
3. Grok's analysis and key insights
4. DeepSeek's analysis and key insights
5. Points of agreement between the AIs
6. Points of disagreement between the AIs
7. 2-3 specific betting recommendations (player props, totals, spreads)
8. Confidence levels with clear reasoning for each recommendation
9. Final synthesis explaining how the four perspectives informed the decision"""
        )
        
        # Create the Crew with all 4 AI analysts + synthesizer
        analysis_crew = Crew(
            agents=[gemini_analyst, gpt_analyst, grok_analyst, deepseek_analyst, betting_synthesizer],
            tasks=[debate_task],
            process=Process.hierarchical,
            manager_llm=manager_llm,
            verbose=True
        )
        
        # Execute the crew
        print("🚀 Crew kickoff - agents are debating...")
        result = analysis_crew.kickoff()
        
        # Extract the final output
        if hasattr(debate_task, 'output') and debate_task.output:
            if hasattr(debate_task.output, 'raw_output'):
                complete_analysis = debate_task.output.raw_output
            else:
                complete_analysis = str(debate_task.output)
        else:
            complete_analysis = str(result)
        
        print("✅ CrewAI debate complete!")
        print(f"🎯 Ready for next analysis request...")
        
        return jsonify({
            "analysis": complete_analysis,
            "player": player_name,
            "team": team_name
        })
        
    except Exception as e:
        print(f"❌ CrewAI Analysis error: {e}")
        print("🔄 Server still running, ready for next request...")
        import traceback
        traceback.print_exc()
        
        error_message = str(e)
        if 'quota' in error_message.lower() or '429' in error_message:
            return jsonify({
                "error": "Rate limit exceeded. Please wait a minute and try again."
            }), 429
        return jsonify({"error": f"Analysis failed: {error_message}"}), 500

@app.route('/api/status', methods=['GET'])
def status():
    """Check cache status"""
    return jsonify({
        "cached": cache_timestamp is not None,
        "age_seconds": time.time() - cache_timestamp if cache_timestamp else None,
        "cache_date": time.ctime(cache_timestamp) if cache_timestamp else None,
        "offensive_types": len(offensive_cache),
        "defensive_types": len(defensive_cache)
    })

if __name__ == '__main__':
    # Load data from JSON files (INSTANT - no scraping!)
    if not load_cache_from_json():
        print("\n⚠️  WARNING: Could not load data!")
        print("Please run: python scraper_backend.py")
        print("Then run this Flask app again.\n")
        exit(1)
    
    print("\n" + "="*60)
    print("🏀 NBA MATCHUP ANALYSIS SERVER")
    print("="*60)
    print("✅ Server is running and ready for requests")
    print("🌐 Available at: http://localhost:5000")
    print("📊 Endpoints available:")
    print("   - /api/player/<name>")
    print("   - /api/defense/<team>")
    print("   - /api/matchup/<player>/<team>")
    print("   - /api/ai-analysis (POST)")
    print("   - /api/status")
    print("\n💡 Server will keep running until you press Ctrl+C")
    print("="*60 + "\n")
    
    # Run server (will stay running)
    app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)