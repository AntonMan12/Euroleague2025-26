import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="EuroLeague Squad Draft Game", page_icon="🏀", layout="centered")

# 1. Fetch data directly from your public Google Sheet link
@st.cache_data
def load_data():
    sheet_url = (
        "https://docs.google.com/spreadsheets/d/"
        "1xPjvZ0vnRN_arbIWIJemXRzH9U9Krb3jZCcCfifILAw/"
        "export?format=csv"
    )
    df = pd.read_csv(sheet_url)
    
    # Clean up column headers
    df.columns = df.columns.str.strip()
    for col in df.columns:
        clow = col.lower()
        if clow == 'team': df.rename(columns={col: 'Team'}, inplace=True)
        elif clow == 'player': df.rename(columns={col: 'Player'}, inplace=True)
        elif clow in ['position', 'pos']: df.rename(columns={col: 'Position'}, inplace=True)
        elif clow == 'pts': df.rename(columns={col: 'PTS'}, inplace=True)
        elif clow == 'trb': df.rename(columns={col: 'TRB'}, inplace=True)
        elif clow == 'ast': df.rename(columns={col: 'AST'}, inplace=True)
        elif clow == 'stl': df.rename(columns={col: 'STL'}, inplace=True)
        elif clow == 'blk': df.rename(columns={col: 'BLK'}, inplace=True)
    return df

df = load_data()

# 2. Gather all individual teams, splitting any shared '/' paths
raw_teams = df['Team'].dropna().unique()
individual_teams = set()
for team_string in raw_teams:
    for individual_team in team_string.split('/'):
        individual_teams.add(individual_team.strip())
unique_teams = list(individual_teams)

def plays_for_team(player_team_str, target_team):
    if pd.isna(player_team_str): return False
    teams = [t.strip().lower() for t in str(player_team_str).split('/')]
    return target_team.lower() in teams

def get_squad_grade(score):
    if score >= 105.0: return "A", "🔥 ELITE / ALL-EUROLEAGUE SQUAD! You drafted absolute superstars."
    elif score >= 85.0: return "B", "💪 PLAYOFF CONTENDER! A highly competitive lineup of solid starters."
    elif score >= 65.0: return "C", "⚖️ MID-TABLE TEAM. An average draft with a mix of stars and role players."
    elif score >= 45.0: return "D", "📉 REBUILDING PHASE. Your squad has too many bench players."
    else: return "E", "🪑 GARBAGE TIME SQUAD. You drafted deep rotation players."

# 3. Streamlit Session State Initialization
if 'game_started' not in st.session_state:
    st.session_state.game_started = False
    st.session_state.round_num = 1
    st.session_state.grand_total_stats = 0.0
    st.session_state.selected_players_info = []
    st.session_state.available_teams = unique_teams.copy()
    st.session_state.current_team = random.choice(unique_teams)
    if st.session_state.current_team in st.session_state.available_teams:
        st.session_state.available_teams.remove(st.session_state.current_team)

# --- SCREEN 1: WELCOME SCREEN ---
if not st.session_state.game_started:
    st.title("🏀 EuroLeague Squad Draft Game")
    st.markdown("---")
    st.subheader("Can you build an elite roster?")
    st.write("• You will draft a team over 5 rounds.")
    st.write("• Each round reveals a completely random EuroLeague squad.")
    st.write("• Pick one player per round to construct your lineup.")
    st.write("")
    
    if st.button("🚀 Start Game", use_container_width=True, type="primary"):
        st.session_state.game_started = True
        st.rerun()

# --- SCREEN 2: GAME OVER REPORT ---
elif st.session_state.round_num > 5:
    st.title("🏆 Final Squad Report")
    st.markdown("---")
    
    for p in st.session_state.selected_players_info:
        pos_display = f" [{p['pos']}]" if p['pos'] else ""
        st.markdown(f"**• {p['name']}**{pos_display} ({p['team']})")
        st.caption(f"➔ {p['pts']:.1f} PTS | {p['trb']:.1f} TRB | {p['ast']:.1f} AST | {p['stl']:.1f} STL | {p['blk']:.1f} BLK")
        st.divider()
        
    grade, message = get_squad_grade(st.session_state.grand_total_stats)
    st.success(f"🏅 YOUR SQUAD GRADE: **[ GRADE {grade} ]** (Total Stats: {st.session_state.grand_total_stats:.1f})")
    st.info(f"📢 STATUS: {message}")
    
    if st.button("🔄 Play Again", use_container_width=True):
        st.session_state.game_started = False
        st.session_state.round_num = 1
        st.session_state.grand_total_stats = 0.0
        st.session_state.selected_players_info = []
        st.session_state.available_teams = unique_teams.copy()
        st.session_state.current_team = random.choice(unique_teams)
        if st.session_state.current_team in st.session_state.available_teams:
            st.session_state.available_teams.remove(st.session_state.current_team)
        st.rerun()

# --- SCREEN 3: ACTIVE GAME ROUNDS ---
else:
    st.title(f"Round {st.session_state.round_num} / 5")
    
    # Running Squad Selection Log
    if st.session_state.selected_players_info:
        with st.expander("🏀 View Your Squad So Far", expanded=True):
            for p in st.session_state.selected_players_info:
                pos_log = f" ({p['pos']})" if p['pos'] else ""
                st.write(f"• **{p['name']}**{pos_log} [{p['team']}] ➔ {p['pts']:.1f} PTS | {p['trb']:.1f} TRB")
    
    st.markdown("---")
    st.subheader(f"🎲 Random Team: :blue[{st.session_state.current_team}]")
    st.write("Tap a player's name below to draft them into your squad:")
    
    # Filter Roster
    team_mask = df['Team'].apply(lambda x: plays_for_team(x, st.session_state.current_team))
    current_roster = df[team_mask]
    players = current_roster['Player'].unique()
    
    # Display interactive buttons cleanly in a 2-column mobile responsive grid
    cols = st.columns(2)
    for i, name in enumerate(players):
        col = cols[i % 2]
        
        # Pull player specific row to extract position letter
        p_row = current_roster[current_roster['Player'] == name].iloc[0]
