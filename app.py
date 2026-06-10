import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="EuroLeague Squad Draft Game", page_icon="🏀", layout="centered")

SPREADSHEET_ID = "1xPjvZ0vnRN_arbIWIJemXRzH9U9Krb3jZCcCfifILAw"

# ─────────────────────────────────────────────
# 1. Fetch all sheet names + gids from the public spreadsheet
# ─────────────────────────────────────────────
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

ROSTER_OPTIONS = {
    "2 Guards - 2 Forwards - 1 Center": {"G": 2, "F": 2, "C": 1},
    "2 Guards - 1 Forward - 2 Centers": {"G": 2, "F": 1, "C": 2},
    "3 Guards - 1 Forward - 1 Center":  {"G": 3, "F": 1, "C": 1},
    "1 Guard - 3 Forwards - 1 Center":  {"G": 1, "F": 3, "C": 1},
    "1 Guard - 2 Forwards - 2 Centers": {"G": 1, "F": 2, "C": 2},
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

    position_priority = ['positions', 'position', 'pos', 'pos.', 'role', 'player-position']
    chosen_pos_col = None
    for priority in position_priority:
        match = next((col for col in df.columns if col.lower() == priority), None)
        if match:
            chosen_pos_col = match
            break
    if not chosen_pos_col:
        chosen_pos_col = next((col for col in df.columns if 'position' in col.lower()), None)

    for col in df.columns:
        clow = col.lower()
        if clow == 'team':          rename_dict[col] = 'Team'
        elif clow == 'player':      rename_dict[col] = 'Player'
        elif col == chosen_pos_col: rename_dict[col] = 'Position'
        elif clow == 'pts':         rename_dict[col] = 'PTS'
        elif clow == 'trb':         rename_dict[col] = 'TRB'
        elif clow == 'ast':         rename_dict[col] = 'AST'
        elif clow == 'stl':         rename_dict[col] = 'STL'
        elif clow == 'blk':         rename_dict[col] = 'BLK'
        elif clow == 'pir':         rename_dict[col] = 'PIR'
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
    if   score >= 85.0:  return "A", "🔥 ELITE / ALL-EUROLEAGUE SQUAD! You drafted high-efficiency superstars (Avg 17+ PIR)."
    elif score >= 65.0:  return "B", "💪 PLAYOFF CONTENDER! A highly competitive lineup of quality starters (Avg 13+ PIR)."
    elif score >= 45.0:  return "C", "⚖️ MID-TABLE TEAM. An average draft with solid, balanced contributors (Avg 9+ PIR)."
    elif score >= 25.0:  return "D", "📉 REBUILDING PHASE. Your squad relies too much on low-impact or bench players (Avg 5+ PIR)."
    else:                return "E", "🪑 GARBAGE TIME SQUAD. Deep rotation players with minimal efficiency metrics (Avg < 5 PIR)."

def get_unique_teams(df):
    raw_teams = df['Team'].dropna().unique()
    individual_teams = set()
    for team_string in raw_teams:
        for t in team_string.split('/'):
            individual_teams.add(t.strip())
    return list(individual_teams)


def parse_position(raw_pos: str) -> list[str]:
    if not raw_pos or raw_pos.strip().upper() in ("", "NAN", "NONE"):
        return []

    if " - " in raw_pos:
        raw_pos = raw_pos.split(" - ", 1)[1]

    parts = [p.strip().upper() for p in raw_pos.split("/")]

    clean = set()
    for p in parts:
        if p in ("G", "PG", "SG"):
            clean.add("G")
        elif p in ("F", "SF", "PF"):
            clean.add("F")
        elif p == "C" or p.startswith("C"):
            clean.add("C")
        else:
            if "G" in p: clean.add("G")
            if "F" in p: clean.add("F")
            if "C" in p: clean.add("C")

    return [pos for pos in ["G", "F", "C"] if pos in clean]


# Helper to compute tactical board positioning offsets smoothly
def get_court_coords(count, y_level):
    if count == 1:
        return [(y_level, 50)]
    elif count == 2:
        return [(y_level, 30), (y_level, 70)]
    elif count == 3:
        return [(y_level + 4, 22), (y_level, 50), (y_level + 4, 78)]
    return [(y_level, int(100 * (i + 1) / (count + 1))) for i in range(count)]


# ─────────────────────────────────────────────
# 4. Helper: pick a fresh random season + team
# ─────────────────────────────────────────────
def pick_random_season_and_team(pool_seasons, exclude_seasons=None):
    exclude_seasons = exclude_seasons if exclude_seasons is not None else set()
    available = [s for s in pool_seasons if s not in exclude_seasons]
    
    if not available:
        exclude_seasons.clear()
        available = list(pool_seasons)

    random.shuffle(available)
    for season_name in available:
        gid = SEASONS[season_name]
        df  = load_season(gid)
        if df.empty:
            continue
        required = ['Team', 'Player', 'Position', 'PTS', 'TRB', 'AST', 'STL', 'BLK', 'PIR']
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
    st.session_state.game_started           = False
    st.session_state.round_num              = 1
    st.session_state.grand_total_stats      = 0.0
    st.session_state.selected_players_info  = []
    st.session_state.used_seasons           = set()
    st.session_state.pool_seasons           = list(SEASONS.keys())
    st.session_state.current_season         = None
    st.session_state.current_df             = None
    st.session_state.current_team           = None
    
    st.session_state.max_g                  = 2
    st.session_state.max_f                  = 2
    st.session_state.max_c                  = 1


# ─────────────────────────────────────────────
# 6. SCREEN 1 — Welcome & Settings
# ─────────────────────────────────────────────
if not st.session_state.game_started:
    st.title("🏀 EuroLeague Squad Draft Game")
    st.markdown("---")
    st.subheader("Can you build an elite roster?")
    st.write("• You will draft a team over **5 rounds**.")
    st.write("• Each round reveals a random team from a random EuroLeague season within your setup pool.")
    st.write("• You must exactly hit your configured target roster constraints below.")
    st.write("")
    
    st.markdown("### 📅 Step 1: Configure Draft Pool")
    chosen_seasons = st.multiselect(
        "Select seasons to include in the random pool:",
        options=list(SEASONS.keys()),
        default=[],  
        placeholder="Choose one or multiple seasons..."
    )

    st.markdown("### 📋 Step 2: Choose Roster Requirement")
    chosen_requirement = st.selectbox(
        "Select required positions combination for your final roster:",
        options=list(ROSTER_OPTIONS.keys()),
        index=0
    )

    if st.button("🚀 Start Game", use_container_width=True, type="primary"):
        if not chosen_seasons:
            st.error("⚠️ You must choose at least one season to populate your draft pool!")
        else:
            limits = ROSTER_OPTIONS[chosen_requirement]
            st.session_state.max_g = limits["G"]
            st.session_state.max_f = limits["F"]
            st.session_state.max_c = limits["C"]

            st.session_state.pool_seasons = chosen_seasons
            season_name, df, team = pick_random_season_and_team(
                pool_seasons=st.session_state.pool_seasons,
                exclude_seasons=st.session_state.used_seasons
            )
            if season_name:
                st.session_state.used_seasons.add(season_name)
                st.session_state.current_season = season_name
                st.session_state.current_df     = df
                st.session_state.current_team   = team
                st.session_state.game_started   = True
                st.rerun()
            else:
                st.error("⚠️ Encountered issues reading connection channels. Double-check your chosen seasons.")


# ─────────────────────────────────────────────
# 7. SCREEN 2 — Game Over Report (WITH BASKETBALL HALF-COURT)
# ─────────────────────────────────────────────
elif st.session_state.round_num > 5:
    st.title("🏆 Final Squad Report")
    st.markdown("---")

    # 1. Sort roster into specific position bins for court placement
    guards   = [p for p in st.session_state.selected_players_info if p.get('pos_clean') == 'G']
    forwards = [p for p in st.session_state.selected_players_info if p.get('pos_clean') == 'F']
    centers  = [p for p in st.session_state.selected_players_info if p.get('pos_clean') == 'C']

    g_positions = get_court_coords(len(guards), 74)
    f_positions = get_court_coords(len(forwards), 46)
    c_positions = get_court_coords(len(centers), 18)

    # 2. Build HTML chips to sit over court coordinates
    player_chips_html = ""
    
    for idx, p in enumerate(guards):
        top, left = g_positions[idx]
        player_chips_html += f"""
        <div style="position: absolute; top: {top}%; left: {left}%; transform: translate(-50%, -50%); background: rgba(17, 20, 30, 0.9); border: 2px solid #FF5500; box-shadow: 0 4px 10px rgba(255,85,0,0.3); padding: 4px 12px; border-radius: 20px; color: white; text-align: center; white-space: nowrap; font-family: sans-serif; z-index: 10;">
            <div style="font-size: 0.6rem; font-weight: 900; color: #FF5500;">GUARD</div>
            <div style="font-size: 0.85rem; font-weight: bold;">{p['name']}</div>
        </div>
        """
    for idx, p in enumerate(forwards):
        top, left = f_positions[idx]
        player_chips_html += f"""
        <div style="position: absolute; top: {top}%; left: {left}%; transform: translate(-50%, -50%); background: rgba(17, 20, 30, 0.9); border: 2px solid #3388FF; box-shadow: 0 4px 10px rgba(51,136,255,0.3); padding: 4px 12px; border-radius: 20px; color: white; text-align: center; white-space: nowrap; font-family: sans-serif; z-index: 10;">
            <div style="font-size: 0.6rem; font-weight: 900; color: #3388FF;">FORWARD</div>
            <div style="font-size: 0.85rem; font-weight: bold;">{p['name']}</div>
        </div>
        """
    for idx, p in enumerate(centers):
        top, left = c_positions[idx]
        player_chips_html += f"""
        <div style="position: absolute; top: {top}%; left: {left}%; transform: translate(-50%, -50%); background: rgba(17, 20, 30, 0.9); border: 2px solid #00CC66; box-shadow: 0 4px 10px rgba(0,204,102,0.3); padding: 4px 12px; border-radius: 20px; color: white; text-align: center; white-space: nowrap; font-family: sans-serif; z-index: 10;">
            <div style="font-size: 0.6rem; font-weight: 900; color: #00CC66;">CENTER</div>
            <div style="font-size: 0.85rem; font-weight: bold;">{p['name']}</div>
        </div>
        """

    # 3. Render the whole canvas (Crisp inline SVG + Overlay chips)
    st.markdown("### 📋 Lineup Tactical Board")
    st.markdown(
        f"""
        <div style="position: relative; width: 100%; max-width: 580px; margin: 0 auto 25px auto;">
            <svg viewBox="0 0 500 450" style="width:100%; border-radius:14px; background:#11141e; border: 2px solid #2d3748; display: block;">
                <rect x="170" y="0" width="160" height="170" fill="none" stroke="rgba(255,255,255,0.12)" stroke-width="2"/>
                <path d="M 170,170 A 80,80 0 0,0 330,170" fill="none" stroke="rgba(255,255,255,0.12)" stroke-width="2"/>
                <path d="M 40,0 L 40,20 A 210,210 0 0,0 460,20 L 460,0" fill="none" stroke="rgba(255,255,255,0.2)" stroke-width="2.5" stroke-dasharray="4 2"/>
                <path d="M 210,450 A 40,40 0 0,1 290,450" fill="none" stroke="rgba(255,255,255,0.12)" stroke-width="2"/>
                <line x1="220" y1="25" x2="280" y2="25" stroke="rgba(255,255,255,0.4)" stroke-width="3"/>
                <circle cx="250" cy="33" r="8" fill="none" stroke="#ff5500" stroke-width="2"/>
            </svg>
            {player_chips_html}
        </div>
        """,
        unsafe_allow_html=True
    )

    # 4. Standard list display underneath tactical map
    with st.expander("📊 View Detailed Scouting Logs", expanded=True):
        for p in st.session_state.selected_players_info:
            pos_display = f" [{p['pos']}]" if p['pos'] else ""
            st.markdown(f"**• {p['name']}**{pos_display} ({p['team']}) — *{p['season']}*")
            st.caption(f"➔ {p['pts']:.1f} PTS | {p['trb']:.1f} TRB | {p['ast']:.1f} AST | {p['stl']:.1f} STL | {p['blk']:.1f} BLK")
            st.divider()

    grade, message = get_squad_grade(st.session_state.grand_total_stats)
    st.success(f"🏅 YOUR SQUAD GRADE: **[ GRADE {grade} ]** (Total PIR Accumulated: {st.session_state.grand_total_stats:.1f})")
    st.info(f"📢 STATUS: {message}")

    if st.button("🔄 Play Again", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


# ─────────────────────────────────────────────
# 8. SCREEN 3 — Active Game Rounds (STATS REMOVED FROM VIEW)
# ─────────────────────────────────────────────
else:
    st.title(f"Round {st.session_state.round_num} / 5")

    g_count = sum(1 for p in st.session_state.selected_players_info if p.get('pos_clean') == 'G')
    f_count = sum(1 for p in st.session_state.selected_players_info if p.get('pos_clean') == 'F')
    c_count = sum(1 for p in st.session_state.selected_players_info if p.get('pos_clean') == 'C')

    st.markdown("### 📋 Your Roster Requirements")
    c1, c2, c3 = st.columns(3)
    c1.metric("🏀 Guards",   f"{g_count} / {st.session_state.max_g}")
    c2.metric("💪 Forwards", f"{f_count} / {st.session_state.max_f}")
    c3.metric("🪑 Centers",  f"{c_count} / {st.session_state.max_c}")

    if st.session_state.selected_players_info:
        with st.expander("🏀 View Current Roster Details", expanded=False):
            for p in st.session_state.selected_players_info:
                pos_log = f" ({p['pos']})" if p['pos'] else ""
                st.write(f"• **{p['name']}**{pos_log} [{p['team']}] *{p['season']}*")

    st.markdown("---")
    st.subheader(f"🎲 :blue[{st.session_state.current_team}] — *{st.session_state.current_season}*")
    st.write("Tap an available player's name to draft them:")

    current_df     = st.session_state.current_df
    team_mask      = current_df['Team'].apply(lambda x: plays_for_team(x, st.session_state.current_team))
    current_roster = current_df[team_mask]
    players        = current_roster['Player'].unique()

    def draw_next_round():
        season_name, df, team = pick_random_season_and_team(
            pool_seasons=st.session_state.pool_seasons,
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
        has_valid_move = False
        player_data = []

        roster_slots = {
            "G": (g_count, st.session_state.max_g), 
            "F": (f_count, st.session_state.max_f), 
            "C": (c_count, st.session_state.max_c)
        }

        for name in players:
            p_row = current_roster[current_roster['Player'] == name].iloc[0]
            raw_pos = (
                str(p_row['Position']).strip()
                if 'Position' in current_roster.columns and pd.notna(p_row['Position'])
                else ""
            )
            eligible_positions = parse_position(raw_pos)

            if not eligible_positions:
                player_data.append({
                    'name': name, 'row': p_row, 'positions': [], 'pos_upper': "?"
                })
                continue

            pos_info = []
            for pos_clean in eligible_positions:
                filled, limit = roster_slots[pos_clean]
                slot_full = filled >= limit
                if not slot_full:
                    has_valid_move = True
                
                pos_info.append({
                    'pos_clean': pos_clean,
                    'disabled': slot_full
                })

            pos_display = "/".join(eligible_positions) if len(eligible_positions) > 1 else eligible_positions[0]
            player_data.append({
                'name': name, 'row': p_row, 'positions': pos_info, 'pos_upper': pos_display
            })

        if not has_valid_move:
            st.error("⚠️ **Roster Constraint Lockout!** All players fill positions you've already maxed out.")
            if st.button("🔄 Draw a Different Team", use_container_width=True, type="primary"):
                draw_next_round()
                st.rerun()
        else:
            cols = st.columns(2)
            for i, pdata in enumerate(player_data):
                col = cols[i % 2]
                with col:
                    if not pdata['positions']:
                        st.markdown(
                            f"""
                            <div style="background: #2d3748; border-radius: 12px; padding: 16px; margin-bottom: 12px; border-left: 6px solid #cbd5e0;">
                                <span style="color: #cbd5e0; font-weight: bold;">🚫 {pdata['name']}</span> <span style="color: #a0aec0; font-size: 0.8rem;">[Unknown Position]</span>
                            </div>
                            """, 
                            unsafe_allow_html=True
                        )
                    else:
                        row = pdata['row']
                        
                        st.markdown(
                            f"""
                            <div style="
                                background: linear-gradient(135deg, #1e2230 0%, #11141e 100%);
                                border-radius: 12px;
                                padding: 16px;
                                border-left: 6px solid #FF5500;
                                box-shadow: 0 4px 12px rgba(0,0,0,0.4);
                                margin-bottom: 8px;
                            ">
                                <div style="color: #FF5500; font-size: 0.8rem; font-weight: bold; letter-spacing: 0.5px; margin-bottom: 4px;">
                                    {pdata['pos_upper']}
                                </div>
                                <div style="color: white; font-size: 1.2rem; font-weight: bold; margin-bottom: 4px;">
                                    {pdata['name']}
                                </div>
                            </div>
                            """, 
                            unsafe_allow_html=True
                        )
                        
                        num_pos = len(pdata['positions'])
                        btn_cols = st.columns(num_pos)
                        
                        for j, pos_dict in enumerate(pdata['positions']):
                            with btn_cols[j]:
                                if st.button(
                                    f"Draft as {pos_dict['pos_clean']}",
                                    key=f"btn_{pdata['name']}_{pos_dict['pos_clean']}_{st.session_state.round_num}",
                                    use_container_width=True,
                                    disabled=pos_dict['disabled']
                                ):
                                    pts, trb, ast, stl, blk = row['PTS'], row['TRB'], row['AST'], row['STL'], row['BLK']
                                    pir = float(row['PIR']) if pd.notna(row['PIR']) else 0.0

                                    st.session_state.grand_total_stats += pir
                                    
                                    st.session_state.selected_players_info.append({
                                        'name':      pdata['name'],
                                        'team':      st.session_state.current_team,
                                        'season':    st.session_state.current_season,
                                        'pos':       pdata['pos_upper'],
                                        'pos_clean': pos_dict['pos_clean'],
                                        'pts': pts, 'trb': trb, 'ast': ast, 'stl': stl, 'blk': blk
                                    })

                                    st.session_state.round_num += 1
                                    if st.session_state.round_num <= 5:
                                        draw_next_round()
                                    st.rerun()
