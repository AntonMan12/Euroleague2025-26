import streamlit as st
import pandas as pd
import random
import requests
import re

st.set_page_config(page_title="EuroLeague Squad Draft Game", page_icon="🏀", layout="centered")

SPREADSHEET_ID = "1xPjvZ0vnRN_arbIWIJemXRzH9U9Krb3jZCcCfifILAw"

# ─────────────────────────────────────────────
# 1. Fetch all sheet names + gids from the public spreadsheet
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_all_seasons():
    """
    Returns a dict of { season_name: gid } by scraping the public HTML export.
    Works for any public Google Sheet without an API key.
    """
    html_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"
    try:
        r = requests.get(html_url, timeout=10)
        r.raise_for_status()
        # Sheet metadata is embedded in the HTML as JSON-like fragments
        # Pattern: ["sheet_name",null,gid, ...]
        # We look for the gid anchors in the HTML instead — more stable
        # Google embeds sheet tabs as: data-name="2025-26" ... data-id="0"
        names = re.findall(r'data-name="([^"]+)"', r.text)
        gids  = re.findall(r'data-id="(\d+)"',    r.text)
        if names and gids and len(names) == len(gids):
            return {name: gid for name, gid in zip(names, gids)}
    except Exception:
        pass

    # Fallback: try the sheets feed (works for publicly shared sheets)
    try:
        feed_url = f"https://spreadsheets.google.com/feeds/worksheets/{SPREADSHEET_ID}/public/full?alt=json"
        r = requests.get(feed_url, timeout=10)
        r.raise_for_status()
        data = r.json()
        entries = data.get("feed", {}).get("entry", [])
        seasons = {}
        for entry in entries:
            title = entry["title"]["$t"]
            link  = next(l["href"] for l in entry["link"] if "gid" in l.get("href", ""))
            gid   = re.search(r"gid=(\d+)", link).group(1)
            seasons[title] = gid
        if seasons:
            return seasons
    except Exception:
        pass

    return {}


# ─────────────────────────────────────────────
# 2. Load one season's data by gid
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_season(gid: str):
    url = (
        f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/"
        f"export?format=csv&gid={gid}"
    )
    try:
        df = pd.read_csv(url)
    except Exception as e:
        st.error(f"Could not load the season sheet. Error: {e}")
        return pd.DataFrame()

    df.columns = df.columns.str.strip()
    rename_dict = {}
    for col in df.columns:
        clow = col.lower()
        if clow == 'team':                                      rename_dict[col] = 'Team'
        elif clow == 'player':                                  rename_dict[col] = 'Player'
        elif clow in ['position','pos','pos.','role','p'] or 'position' in clow:
                                                                rename_dict[col] = 'Position'
        elif clow == 'pts':                                     rename_dict[col] = 'PTS'
        elif clow == 'trb':                                     rename_dict[col] = 'TRB'
        elif clow == 'ast':                                     rename_dict[col] = 'AST'
        elif clow == 'stl':                                     rename_dict[col] = 'STL'
        elif clow == 'blk':                                     rename_dict[col] = 'BLK'
    df.rename(columns=rename_dict, inplace=True)
    return df


# ─────────────────────────────────────────────
# 3. Helpers
# ─────────────────────────────────────────────
def plays_for_team(player_team_str, target_team):
    if pd.isna(player_team_str): return False
    teams = [t.strip().lower() for t in str(player_team_str).split('/')]
    return target_team.lower() in teams

def get_squad_grade(score):
    if   score >= 105.0: return "A", "🔥 ELITE / ALL-EUROLEAGUE SQUAD! You drafted absolute superstars."
    elif score >=  85.0: return "B", "💪 PLAYOFF CONTENDER! A highly competitive lineup of solid starters."
    elif score >=  65.0: return "C", "⚖️ MID-TABLE TEAM. An average draft with a mix of stars and role players."
    elif score >=  45.0: return "D", "📉 REBUILDING PHASE. Your squad has too many bench players."
    else:                return "E", "🪑 GARBAGE TIME SQUAD. You drafted deep rotation players."

def get_unique_teams(df):
    raw_teams = df['Team'].dropna().unique()
    individual_teams = set()
    for team_string in raw_teams:
        for t in team_string.split('/'):
            individual_teams.add(t.strip())
    return list(individual_teams)


# ─────────────────────────────────────────────
# 4. Bootstrap: pick a random season ONCE per session
# ─────────────────────────────────────────────
if 'season_name' not in st.session_state:
    all_seasons = get_all_seasons()

    if not all_seasons:
        st.error(
            "❌ Could not retrieve the list of seasons from the Google Sheet. "
            "Make sure the spreadsheet is set to **Anyone with the link → Viewer**."
        )
        st.stop()

    chosen_name = random.choice(list(all_seasons.keys()))
    chosen_gid  = all_seasons[chosen_name]

    df = load_season(chosen_gid)
    required = ['Team', 'Player', 'Position', 'PTS', 'TRB', 'AST', 'STL', 'BLK']
    missing  = [r for r in required if r not in df.columns]
    if missing or df.empty:
        st.error(f"Season sheet '{chosen_name}' is missing columns: {missing}. Found: {list(df.columns)}")
        st.stop()

    unique_teams = get_unique_teams(df)

    st.session_state.season_name   = chosen_name
    st.session_state.df            = df
    st.session_state.unique_teams  = unique_teams
    st.session_state.game_started  = False
    st.session_state.round_num     = 1
    st.session_state.grand_total_stats      = 0.0
    st.session_state.selected_players_info  = []
    st.session_state.available_teams        = unique_teams.copy()
    st.session_state.current_team           = random.choice(unique_teams) if unique_teams else None
    if st.session_state.current_team in st.session_state.available_teams:
        st.session_state.available_teams.remove(st.session_state.current_team)

# Convenient local aliases
df           = st.session_state.df
unique_teams = st.session_state.unique_teams
season_name  = st.session_state.season_name


# ─────────────────────────────────────────────
# 5. SCREEN 1 — Welcome
# ─────────────────────────────────────────────
if not st.session_state.game_started:
    st.title("🏀 EuroLeague Squad Draft Game")
    st.markdown("---")
    st.subheader(f"📅 Season: **{season_name}**")
    st.write("")
    st.subheader("Can you build an elite roster?")
    st.write("• You will draft a team over **5 rounds**.")
    st.write("• Each round reveals a completely random EuroLeague squad.")
    st.write("• **Roster Requirement:** Exactly **2 Guards (G), 2 Forwards (F), and 1 Center (C)**.")
    st.write("")

    if st.button("🚀 Start Game", use_container_width=True, type="primary"):
        st.session_state.game_started = True
        st.rerun()


# ─────────────────────────────────────────────
# 6. SCREEN 2 — Game Over Report
# ─────────────────────────────────────────────
elif st.session_state.round_num > 5:
    st.title("🏆 Final Squad Report")
    st.caption(f"📅 Season: {season_name}")
    st.markdown("---")

    for p in st.session_state.selected_players_info:
        pos_display = f" [{p['pos']}]" if p['pos'] else ""
        st.markdown(f"**• {p['name']}**{pos_display} ({p['team']})")
        st.caption(f"➔ {p['pts']:.1f} PTS | {p['trb']:.1f} TRB | {p['ast']:.1f} AST | {p['stl']:.1f} STL | {p['blk']:.1f} BLK")
        st.divider()

    grade, message = get_squad_grade(st.session_state.grand_total_stats)
    st.success(f"🏅 YOUR SQUAD GRADE: **[ GRADE {grade} ]** (Total Stats: {st.session_state.grand_total_stats:.1f})")
    st.info(f"📢 STATUS: {message}")

    if st.button("🔄 Play Again (new random season)", use_container_width=True):
        # Wipe the whole session so a new season is picked on next run
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


# ─────────────────────────────────────────────
# 7. SCREEN 3 — Active Game Rounds
# ─────────────────────────────────────────────
else:
    st.title(f"Round {st.session_state.round_num} / 5")
    st.caption(f"📅 Season: {season_name}")

    g_count = sum(1 for p in st.session_state.selected_players_info if p.get('pos_clean') == 'G')
    f_count = sum(1 for p in st.session_state.selected_players_info if p.get('pos_clean') == 'F')
    c_count = sum(1 for p in st.session_state.selected_players_info if p.get('pos_clean') == 'C')

    st.markdown("### 📋 Your Roster Requirements")
    c1, c2, c3 = st.columns(3)
    c1.metric("🏀 Guards",   f"{g_count} / 2")
    c2.metric("💪 Forwards", f"{f_count} / 2")
    c3.metric("🪑 Centers",  f"{c_count} / 1")

    if st.session_state.selected_players_info:
        with st.expander("🏀 View Current Roster Details", expanded=False):
            for p in st.session_state.selected_players_info:
                pos_log = f" ({p['pos']})" if p['pos'] else ""
                st.write(f"• **{p['name']}**{pos_log} [{p['team']}] ➔ {p['pts']:.1f} PTS | {p['trb']:.1f} TRB")

    st.markdown("---")
    st.subheader(f"🎲 Random Team: :blue[{st.session_state.current_team}]")
    st.write("Tap an available player's name to draft them:")

    team_mask      = df['Team'].apply(lambda x: plays_for_team(x, st.session_state.current_team))
    current_roster = df[team_mask]
    players        = current_roster['Player'].unique()

    if len(players) == 0:
        st.warning(f"⚠️ No players found matching the team **{st.session_state.current_team}**.")
        if st.button("Skip Team & Draw Another"):
            if st.session_state.available_teams:
                st.session_state.current_team = random.choice(st.session_state.available_teams)
                st.session_state.available_teams.remove(st.session_state.current_team)
            st.rerun()
    else:
        has_valid_move      = False
        player_buttons_data = []

        for name in players:
            p_row     = current_roster[current_roster['Player'] == name].iloc[0]
            pos_upper = (
                str(p_row['Position']).strip().upper()
                if 'Position' in current_roster.columns and pd.notna(p_row['Position'])
                else ""
            )
            pos_clean = ""
            if   "G" in pos_upper: pos_clean = "G"
            elif "F" in pos_upper: pos_clean = "F"
            elif "C" in pos_upper: pos_clean = "C"

            is_disabled = False
            suffix      = ""
            if   pos_clean == "G" and g_count >= 2: is_disabled = True; suffix = " 🚫 [G Full]"
            elif pos_clean == "F" and f_count >= 2: is_disabled = True; suffix = " 🚫 [F Full]"
            elif pos_clean == "C" and c_count >= 1: is_disabled = True; suffix = " 🚫 [C Full]"

            if not is_disabled:
                has_valid_move = True

            button_label = f"{name} ({pos_upper}){suffix}" if pos_upper else f"{name}{suffix}"
            player_buttons_data.append({
                'name': name, 'label': button_label, 'disabled': is_disabled,
                'row': p_row, 'pos_clean': pos_clean, 'pos_upper': pos_upper
            })

        if not has_valid_move:
            st.error("⚠️ **Roster Constraint Lockout!** All players on this team fill positions you've already maxed out.")
            if st.button("🔄 Draw a Different Team", use_container_width=True, type="primary"):
                if st.session_state.available_teams:
                    st.session_state.current_team = random.choice(st.session_state.available_teams)
                    st.session_state.available_teams.remove(st.session_state.current_team)
                st.rerun()
        else:
            cols = st.columns(2)
            for i, pdata in enumerate(player_buttons_data):
                col = cols[i % 2]
                if col.button(
                    pdata['label'],
                    key=f"btn_{pdata['name']}_{st.session_state.round_num}",
                    use_container_width=True,
                    disabled=pdata['disabled']
                ):
                    row = pdata['row']
                    pts, trb, ast, stl, blk = row['PTS'], row['TRB'], row['AST'], row['STL'], row['BLK']

                    st.session_state.grand_total_stats += (pts + trb + ast + stl + blk)
                    st.session_state.selected_players_info.append({
                        'name':      pdata['name'],
                        'team':      st.session_state.current_team,
                        'pos':       pdata['pos_upper'],
                        'pos_clean': pdata['pos_clean'],
                        'pts': pts, 'trb': trb, 'ast': ast, 'stl': stl, 'blk': blk
                    })

                    st.session_state.round_num += 1
                    if st.session_state.available_teams and st.session_state.round_num <= 5:
                        st.session_state.current_team = random.choice(st.session_state.available_teams)
                        st.session_state.available_teams.remove(st.session_state.current_team)
                    st.rerun()
