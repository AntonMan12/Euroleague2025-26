import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="EuroLeague Squad Draft Game", page_icon="🏀", layout="centered")

SPREADSHEET_ID = "1xPjvZ0vnRN_arbIWIJemXRzH9U9Krb3jZCcCfifILAw"

# ─────────────────────────────────────────────
# 1. Fetch all sheet names + gids from the public spreadsheet
# ─────────────────────────────────────────────
# All 25 EuroLeague seasons — hardcoded for reliability
SEASONS = {
    "2025-26": "543714600",
    "2024-25": "1549437101",
    "2023-24": "1831882140",
    "2022-23": "1520752226",
    "2021-22": "2089144730",
    "2020-21": "1816215049",
    "2019-20": "553933453",
    "2018-19": "1267099967",
    "2017-18": "1197135956",
    "2016-17": "179740526",
    "2015-16": "508885604",
    "2014-15": "1039861337",
    "2013-14": "14626217",
    "2012-13": "868645856",
    "2011-12": "1294164506",
    "2010-11": "984593909",
    "2009-10": "1189996356",
    "2008-09": "117181707",
    "2007-08": "1682008449",
    "2006-07": "432863192",
    "2005-06": "493050551",
    "2004-05": "718961987",
    "2003-04": "676363461",
    "2002-03": "691080699",
    "2001-02": "1203521641",
    "2000-01": "1987314852",
}

def get_all_seasons():
    return SEASONS


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
        elif clow in ['position','pos','pos.','role','p','player-position'] or 'position' in clow:
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


def parse_position(raw_pos: str) -> list[str]:
    """
    Handles both old and new position formats and returns a list of
    normalised position codes (G, F, C) that the player can fill.

    Old format: "G", "F/C", "PG/SG"
    New format: "Scottie Wilbekin - G", "Nikola Mirotic - F/C", "Shane Larkin - PG/SG"

    Examples:
        "G"                      → ["G"]
        "PG/SG"                  → ["G"]
        "F/C"                    → ["F", "C"]
        "Mirotic - F/C"          → ["F", "C"]
        "Shane Larkin - PG/SG"   → ["G"]
    """
    if not raw_pos or raw_pos.strip().upper() in ("", "NAN", "NONE"):
        return []

    # Strip everything up to and including " - " if present (new format)
    if " - " in raw_pos:
        raw_pos = raw_pos.split(" - ", 1)[1]

    # Now raw_pos is something like "G", "F/C", "PG/SG", "SF/PF"
    parts = [p.strip().upper() for p in raw_pos.split("/")]

    clean = set()
    for p in parts:
        # Normalize sub-positions to base G/F/C
        # Guard variants: G, PG, SG
        if p in ("G", "PG", "SG"):
            clean.add("G")
        # Forward variants: F, SF, PF
        elif p in ("F", "SF", "PF"):
            clean.add("F")
        # Center variants: C, C1, CT, CTR, CENTER
        elif p == "C" or p.startswith("C"):
            clean.add("C")
        # Catch-all for anything containing G/F/C if none of the above matched
        else:
            if "G" in p: clean.add("G")
            if "F" in p: clean.add("F")
            if "C" in p: clean.add("C")

    # Return in a stable order
    return [pos for pos in ["G", "F", "C"] if pos in clean]


# ─────────────────────────────────────────────
# 4. Helper: pick a fresh random season + team
# ─────────────────────────────────────────────
def pick_random_season_and_team(exclude_seasons=None):
    """
    Picks a random season (not in exclude_seasons) and a random team from it.
    Returns (season_name, df, team_name) or raises if nothing loads.
    """
    exclude_seasons = exclude_seasons or set()
    available = [s for s in SEASONS if s not in exclude_seasons]
    if not available:
        available = list(SEASONS.keys())  # reset if all used

    random.shuffle(available)
    for season_name in available:
        gid = SEASONS[season_name]
        df  = load_season(gid)
        if df.empty:
            continue
        required = ['Team', 'Player', 'Position', 'PTS', 'TRB', 'AST', 'STL', 'BLK']
        if any(r not in df.columns for r in required):
            continue
        teams = get_unique_teams(df)
        if not teams:
            continue
        team = random.choice(teams)
        return season_name, df, team
    return None, None, None


# ─────────────────────────────────────────────
# 5. Bootstrap: initialise session state
# ─────────────────────────────────────────────
if 'game_started' not in st.session_state:
    season_name, df, team = pick_random_season_and_team()
    st.session_state.game_started           = False
    st.session_state.round_num              = 1
    st.session_state.grand_total_stats      = 0.0
    st.session_state.selected_players_info  = []
    st.session_state.used_seasons           = {season_name} if season_name else set()
    st.session_state.current_season         = season_name
    st.session_state.current_df             = df
    st.session_state.current_team           = team


# ─────────────────────────────────────────────
# 6. SCREEN 1 — Welcome
# ─────────────────────────────────────────────
if not st.session_state.game_started:
    st.title("🏀 EuroLeague Squad Draft Game")
    st.markdown("---")
    st.subheader("Can you build an elite roster?")
    st.write("• You will draft a team over **5 rounds**.")
    st.write("• Each round reveals a random team from a **random EuroLeague season**.")
    st.write("• **Roster Requirement:** Exactly **2 Guards (G), 2 Forwards (F), and 1 Center (C)**.")
    st.write("")

    if st.button("🚀 Start Game", use_container_width=True, type="primary"):
        st.session_state.game_started = True
        st.rerun()


# ─────────────────────────────────────────────
# 7. SCREEN 2 — Game Over Report
# ─────────────────────────────────────────────
elif st.session_state.round_num > 5:
    st.title("🏆 Final Squad Report")
    st.markdown("---")

    for p in st.session_state.selected_players_info:
        pos_display = f" [{p['pos']}]" if p['pos'] else ""
        st.markdown(f"**• {p['name']}**{pos_display} ({p['team']}) — *{p['season']}*")
        st.caption(f"➔ {p['pts']:.1f} PTS | {p['trb']:.1f} TRB | {p['ast']:.1f} AST | {p['stl']:.1f} STL | {p['blk']:.1f} BLK")
        st.divider()

    grade, message = get_squad_grade(st.session_state.grand_total_stats)
    st.success(f"🏅 YOUR SQUAD GRADE: **[ GRADE {grade} ]** (Total Stats: {st.session_state.grand_total_stats:.1f})")
    st.info(f"📢 STATUS: {message}")

    if st.button("🔄 Play Again", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


# ─────────────────────────────────────────────
# 8. SCREEN 3 — Active Game Rounds
# ─────────────────────────────────────────────
else:
    st.title(f"Round {st.session_state.round_num} / 5")
    st.caption(f"📅 Season: **{st.session_state.current_season}** | 🏀 Team: **{st.session_state.current_team}**")

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
                st.write(f"• **{p['name']}**{pos_log} [{p['team']}] *{p['season']}* ➔ {p['pts']:.1f} PTS | {p['trb']:.1f} TRB")

    st.markdown("---")
    st.subheader(f"🎲 :blue[{st.session_state.current_team}]")
    st.write("Tap an available player's name to draft them:")

    current_df     = st.session_state.current_df
    team_mask      = current_df['Team'].apply(lambda x: plays_for_team(x, st.session_state.current_team))
    current_roster = current_df[team_mask]
    players        = current_roster['Player'].unique()

    def draw_next_round():
        """Pick a new random season+team and store in session state."""
        season_name, df, team = pick_random_season_and_team(
            exclude_seasons=st.session_state.used_seasons
        )
        if season_name:
            st.session_state.used_seasons.add(season_name)
            st.session_state.current_season = season_name
            st.session_state.current_df     = df
            st.session_state.current_team   = team

    if len(players) == 0:
        st.warning(f"⚠️ No players found for **{st.session_state.current_team}**.")
        if st.button("Skip & Draw Another"):
            draw_next_round()
            st.rerun()
    else:
        has_valid_move      = False
        player_buttons_data = []

        roster_slots = {"G": (g_count, 2), "F": (f_count, 2), "C": (c_count, 1)}

        for name in players:
            p_row   = current_roster[current_roster['Player'] == name].iloc[0]
            raw_pos = (
                str(p_row['Position']).strip()
                if 'Position' in current_roster.columns and pd.notna(p_row['Position'])
                else ""
            )
            eligible_positions = parse_position(raw_pos)

            if not eligible_positions:
                player_buttons_data.append({
                    'name': name, 'label': f"{name} (?) 🚫 [Unknown pos]",
                    'disabled': True, 'row': p_row, 'pos_clean': "", 'pos_upper': "?"
                })
                continue

            for pos_clean in eligible_positions:
                filled, limit = roster_slots[pos_clean]
                slot_full     = filled >= limit
                slot_label    = {"G": "G Full", "F": "F Full", "C": "C Full"}[pos_clean]
                pos_display   = "/".join(eligible_positions) if len(eligible_positions) > 1 else pos_clean

                if slot_full:
                    suffix, is_disabled = f" 🚫 [{slot_label}]", True
                else:
                    suffix, is_disabled = f" → draft as {pos_clean}", False
                    has_valid_move = True

                player_buttons_data.append({
                    'name': name, 'label': f"{name} ({pos_display}){suffix}",
                    'disabled': is_disabled, 'row': p_row,
                    'pos_clean': pos_clean, 'pos_upper': pos_display
                })

        if not has_valid_move:
            st.error("⚠️ **Roster Constraint Lockout!** All players fill positions you've already maxed out.")
            if st.button("🔄 Draw a Different Team", use_container_width=True, type="primary"):
                draw_next_round()
                st.rerun()
        else:
            cols = st.columns(2)
            for i, pdata in enumerate(player_buttons_data):
                col = cols[i % 2]
                if col.button(
                    pdata['label'],
                    key=f"btn_{pdata['name']}_{pdata['pos_clean']}_{st.session_state.round_num}",
                    use_container_width=True,
                    disabled=pdata['disabled']
                ):
                    row = pdata['row']
                    pts, trb, ast, stl, blk = row['PTS'], row['TRB'], row['AST'], row['STL'], row['BLK']

                    st.session_state.grand_total_stats += (pts + trb + ast + stl + blk)
                    st.session_state.selected_players_info.append({
                        'name':      pdata['name'],
                        'team':      st.session_state.current_team,
                        'season':    st.session_state.current_season,
                        'pos':       pdata['pos_upper'],
                        'pos_clean': pdata['pos_clean'],
                        'pts': pts, 'trb': trb, 'ast': ast, 'stl': stl, 'blk': blk
                    })

                    st.session_state.round_num += 1
                    if st.session_state.round_num <= 5:
                        draw_next_round()
                    st.rerun()
