import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="EuroLeague Squad Draft Game", page_icon="🏀", layout="centered")

# 1. Fetch data directly from your public Google Sheet link
def load_data():
    sheet_url = (
        "https://docs.google.com/spreadsheets/d/"
        "1xPjvZ0vnRN_arbIWIJemXRzH9U9Krb3jZCcCfifILAw/"
        "export?format=csv"
    )
    try:
        df = pd.read_csv(sheet_url)
    except Exception as e:
        st.error(f"Could not read Google Sheet. Make sure it is public! Error: {e}")
        return pd.DataFrame()
    
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

if df.empty:
    st.warning("The spreadsheet appears to be empty or could not be loaded.")
else:
    # Diagnostic Check
    required = ['Team', 'Player', 'PTS', 'TRB', 'AST', 'STL', 'BLK']
    missing = [r for r in required if r not in df.columns]
    if missing:
        st.error(f"🕵️‍♂️ Missing columns in spreadsheet: {missing}")
        st.stop()

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

    # 3. Stream

