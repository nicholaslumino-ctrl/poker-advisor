import streamlit as st
from itertools import combinations
from collections import Counter

RANKS = '23456789TJQKA'
RANK_VALUES = {r: i for i, r in enumerate(RANKS, 2)}
SUIT_SYMBOLS = {'s':'♠', 'h':'♥', 'd':'♦', 'c':'♣'}
SUIT_COLOR = {'s': 'black', 'c': 'black', 'h': 'red', 'd': 'red'}

class Card:
    def __init__(self, card_str):
        self.rank = card_str[0].upper()
        self.suit = card_str[1].lower()
        self.value = RANK_VALUES[self.rank]

def evaluate_hand(cards):
    best_rank = (0, [])
    for combo in combinations(cards, 5):
        rank = rank_5cards(combo)
        if rank > best_rank:
            best_rank = rank
    return best_rank

def rank_5cards(cards):
    values = sorted([c.value for c in cards], reverse=True)
    suits = [c.suit for c in cards]
    value_counts = Counter(values)
    is_flush = len(set(suits)) == 1
    unique_vals = sorted(set(values), reverse=True)
    is_straight = False
    straight_high = 0
    if len(unique_vals) >= 5:
        for i in range(len(unique_vals) - 4):
            if unique_vals[i] - unique_vals[i+4] == 4:
                is_straight = True
                straight_high = unique_vals[i]
                break
    if set([14,2,3,4,5]).issubset(set(values)):
        is_straight = True
        straight_high = 5
    counts = sorted(value_counts.items(), key=lambda x: (-x[1], -x[0]))
    count_pattern = [c[1] for c in counts]
    if is_straight and is_flush:
        return (8, [straight_high])
    elif count_pattern[0] == 4:
        return (7, [counts[0][0], counts[1][0]])
    elif count_pattern[0] == 3 and count_pattern[1] == 2:
        return (6, [counts[0][0], counts[1][0]])
    elif is_flush:
        return (5, values)
    elif is_straight:
        return (4, [straight_high])
    elif count_pattern[0] == 3:
        kickers = [c[0] for c in counts[1:3]]
        return (3, [counts[0][0]] + kickers)
    elif count_pattern[0] == 2 and count_pattern[1] == 2:
        pairs = sorted([counts[0][0], counts[1][0]], reverse=True)
        kicker = counts[2][0]
        return (2, pairs + [kicker])
    elif count_pattern[0] == 2:
        kickers = [c[0] for c in counts[1:4]]
        return (1, [counts[0][0]] + kickers)
    else:
        return (0, values)

HAND_NAMES = {8: "Straight Flush", 7: "Four of a Kind", 6: "Full House",
    5: "Flush", 4: "Straight", 3: "Three of a Kind",
    2: "Two Pair", 1: "One Pair", 0: "High Card"}

def get_outs(hole_cards, board_cards):
    all_known = hole_cards + board_cards
    used_values = [c.value for c in all_known]
    used_suits = Counter(c.suit for c in all_known)
    outs = 0
    draw_types = []
    for suit, count in used_suits.items():
        if count == 4:
            outs += 9
            draw_types.append("Flush Draw")
    unique_vals = sorted(set(used_values))
    for i in range(len(unique_vals) - 3):
        window = unique_vals[i:i+4]
        if window[-1] - window[0] == 3:
            outs += 8
            draw_types.append("OESD")
            break
    return outs, draw_types

def hand_strength_score(rank_tuple):
    return (rank_tuple[0] * 12.5) + min(sum(rank_tuple[1]) / 14, 1) * 5

def calculate_equity_estimate(hole_cards, board_cards):
    all_cards = hole_cards + board_cards
    if len(all_cards) >= 5:
        rank = evaluate_hand(all_cards)
        base_strength = hand_strength_score(rank)
    else:
        base_strength = 30
    outs, draws = get_outs(hole_cards, board_cards)
    cards_to_come = 5 - len(board_cards)
    if cards_to_come == 2:
        draw_equity = outs * 4
    elif cards_to_come == 1:
        draw_equity = outs * 2
    else:
        draw_equity = 0
    total_equity = min(base_strength + draw_equity, 95)
    return total_equity, draws

def analyze_board_texture(board_cards):
    if len(board_cards) < 3:
        return "N/A"
    suits = [c.suit for c in board_cards]
    values = sorted(set(c.value for c in board_cards))
    suit_counts = Counter(suits)
    max_suit_count = max(suit_counts.values())
    flush_draw_possible = max_suit_count >= 2
    gaps = [values[i+1] - values[i] for i in range(len(values)-1)]
    connected = any(g <= 2 for g in gaps) if gaps else False
    paired_board = len(values) < len(board_cards)
    wetness_score = 0
    if max_suit_count >= 3:
        wetness_score += 2
    elif flush_draw_possible:
        wetness_score += 1
    if connected:
        wetness_score += 2
    if paired_board:
        wetness_score -= 1
    if wetness_score >= 3:
        return "VERY WET"
    elif wetness_score >= 1:
        return "WET"
    else:
        return "DRY"

def get_pair_context(hole_cards, board_cards, rank):
    if rank[0] != 1 or len(board_cards) == 0:
        return None
    board_values = sorted([c.value for c in board_cards], reverse=True)
    hole_values = sorted([c.value for c in hole_cards], reverse=True)
    paired_value = rank[1][0]
    if hole_values[0] == hole_values[1] and paired_value == hole_values[0]:
        if paired_value > board_values[0]:
            return "Overpair"
        else:
            return "Underpair"
    if paired_value == board_values[0]:
        return "Top Pair"
    elif len(board_values) > 1 and paired_value == board_values[-1]:
        return "Bottom Pair"
    else:
        return "Middle Pair"

def categorize_hand(hole_cards, board_cards):
    all_cards = hole_cards + board_cards
    if len(all_cards) < 5:
        values = sorted([c.value for c in hole_cards], reverse=True)
        is_pair = values[0] == values[1]
        if is_pair and values[0] >= 11:
            return "MONSTER", None
        elif is_pair and values[0] >= 8:
            return "STRONG", None
        elif values[0] >= 13 and values[1] >= 11:
            return "STRONG", None
        else:
            return "MEDIUM", None
    rank = evaluate_hand(all_cards)
    outs, draws = get_outs(hole_cards, board_cards)
    pair_context = get_pair_context(hole_cards, board_cards, rank)
    if rank[0] >= 6:
        return "MONSTER", HAND_NAMES[rank[0]]
    elif rank[0] == 5:
        return "MONSTER", HAND_NAMES[rank[0]]
    elif rank[0] == 4:
        return "STRONG", HAND_NAMES[rank[0]]
    elif rank[0] == 3:
        return ("MONSTER" if len(board_cards) <= 4 else "STRONG"), "Three of a Kind"
    elif rank[0] == 2:
        return "STRONG", "Two Pair"
    elif rank[0] == 1:
        if pair_context in ["Overpair", "Top Pair"]:
            return "STRONG", pair_context
        elif pair_context == "Middle Pair":
            return "MEDIUM", pair_context
        else:
            return "WEAK", pair_context
    else:
        if outs >= 12:
            return "DRAWING", "Combo Draw"
        elif outs >= 8:
            return "DRAWING", "Strong Draw"
        elif outs >= 4:
            return "DRAWING", "Weak Draw"
        else:
            return "AIR", "Nothing"

def get_strategic_recommendation(hand_category, pair_context, board_texture, equity, pot_size, bet_to_call, street):
    facing_bet = bet_to_call > 0
    pot_odds = (bet_to_call / (pot_size + bet_to_call) * 100) if facing_bet else 0
    result = {"action": "", "sizing": "", "reasoning": "", "game_plan": ""}
    
    if hand_category == "MONSTER":
        if not facing_bet:
            if board_texture == "DRY" and street in ["Flop", "Turn"]:
                result["action"] = "🎣 CHECK (TRAP)"
                result["reasoning"] = f"Monster on {board_texture.lower()} board. Slow-play to induce bluffs."
                result["game_plan"] = "Bet big next street if checked back. Raise if they bet."
            else:
                result["action"] = "🟢 BET"
                result["sizing"] = "60-75% pot"
                result["reasoning"] = f"{board_texture.lower()} board — bet for protection + value."
                result["game_plan"] = "Keep betting for value."
        else:
            result["action"] = "🟢 RAISE"
            result["sizing"] = "3x their bet"
            result["reasoning"] = "Monster facing a bet — raise big for max value."
            result["game_plan"] = "Get all-in by river."
    
    elif hand_category == "STRONG":
        if not facing_bet:
            result["action"] = "🟢 BET"
            result["sizing"] = "50-65% pot"
            result["reasoning"] = f"{pair_context or 'Strong hand'} — bet for value/protection."
            result["game_plan"] = "Continue betting."
        else:
            if equity > pot_odds + 20:
                result["action"] = "🟢 RAISE"
                result["sizing"] = "2.5-3x"
                result["reasoning"] = "Equity far exceeds pot odds — raise for value."
            elif equity > pot_odds:
                result["action"] = "🟢 CALL"
                result["reasoning"] = "Profitable call."
            else:
                result["action"] = "🟡 CLOSE CALL"
                result["reasoning"] = "Very close — consider opponent tendencies."
            result["game_plan"] = "Re-evaluate next street."
    
    elif hand_category == "MEDIUM":
        if not facing_bet:
            if board_texture == "DRY":
                result["action"] = "🟡 SMALL BET"
                result["sizing"] = "30-40% pot"
                result["reasoning"] = "Thin value — can get called by worse."
            else:
                result["action"] = "⚪ CHECK"
                result["reasoning"] = "Wet board — control pot size."
        else:
            if equity > pot_odds:
                result["action"] = "🟡 CALL"
                result["reasoning"] = "Profitable but marginal."
            else:
                result["action"] = "🔴 FOLD"
                result["reasoning"] = "Insufficient equity."
        result["game_plan"] = "Play cautiously."
    
    elif hand_category == "DRAWING":
        if not facing_bet:
            if pair_context == "Combo Draw":
                result["action"] = "🟢 BET (semi-bluff)"
                result["sizing"] = "60-70% pot"
                result["reasoning"] = "Combo draw has huge equity."
            else:
                result["action"] = "⚪ CHECK"
                result["reasoning"] = "See next card cheap."
        else:
            if equity > pot_odds:
                if equity > pot_odds + 20:
                    result["action"] = "🟢 RAISE (semi)"
                else:
                    result["action"] = "🟢 CALL"
                result["reasoning"] = f"{equity:.0f}% equity vs {pot_odds:.0f}% needed."
            else:
                result["action"] = "🔴 FOLD"
                result["reasoning"] = "Not enough outs."
        result["game_plan"] = "Bet big if you hit. Bluff scary cards if you miss."
    
    else:
        if not facing_bet:
            result["action"] = "⚪ CHECK"
        else:
            result["action"] = "🔴 FOLD"
        result["reasoning"] = "No hand to continue with."
        result["game_plan"] = "Next hand."
    
    return result

# ============ STREAMLIT UI ============
st.set_page_config(page_title="Click Poker Advisor", page_icon="🃏", layout="wide")

st.markdown("""
<style>
    .big-font {font-size:40px !important; font-weight:bold; text-align:center; margin:20px 0;}
    div.stButton > button {height:45px; font-size:16px; font-weight:bold;}
</style>
""", unsafe_allow_html=True)

st.title("🃏 Click Poker Advisor")

# Initialize session state
if 'hole' not in st.session_state:
    st.session_state.hole = []
if 'board' not in st.session_state:
    st.session_state.board = []
if 'pot' not in st.session_state:
    st.session_state.pot = 100
if 'bet' not in st.session_state:
    st.session_state.bet = 0

def cards_to_html(card_list):
    out = []
    for c in card_list:
        rank, suit = c[0], c[1]
        color = SUIT_COLOR[suit]
        symbol = SUIT_SYMBOLS[suit]
        out.append(f'<span style="color:{color}; font-size:32px; margin-right:6px; font-weight:bold;">{rank}{symbol}</span>')
    return ''.join(out) if out else "<i style='color:gray;'>none</i>"

# Display selected cards
col_disp1, col_disp2 = st.columns(2)
with col_disp1:
    st.write(f"**Your Hand:** {cards_to_html(st.session_state.hole)}", unsafe_allow_html=True)
with col_disp2:
    st.write(f"**Board:** {cards_to_html(st.session_state.board)}", unsafe_allow_html=True)

# Clear buttons
col_clear1, col_clear2, col_clear3 = st.columns([1, 1, 2])
with col_clear1:
    if st.button("🗑️ Clear Hand", use_container_width=True):
        st.session_state.hole = []
        st.rerun()
with col_clear2:
    if st.button("🗑️ Clear Board", use_container_width=True):
        st.session_state.board = []
        st.rerun()

st.divider()

# Card selector mode
mode = st.radio("👆 Select for:", ["Hand", "Board"], horizontal=True)

st.write("**Click cards to add:**")

# FIXED CARD GRID - shows all suits
suits_list = ['s', 'h', 'd', 'c']
for suit in suits_list:
    st.write(f"**{SUIT_SYMBOLS[suit]} {['Spades', 'Hearts', 'Diamonds', 'Clubs'][suits_list.index(suit)]}**")
    cols = st.columns(13)
    for i, rank in enumerate(RANKS):
        card_str = rank + suit
        with cols[i]:
            btn_label = f"{rank}{SUIT_SYMBOLS[suit]}"
            btn_color = SUIT_COLOR[suit]
            
            if st.button(btn_label, key=card_str, use_container_width=True):
                if mode == "Hand":
                    if len(st.session_state.hole) < 2 and card_str not in st.session_state.hole:
                        st.session_state.hole.append(card_str)
                        st.rerun()
                else:
                    if len(st.session_state.board) < 5 and card_str not in st.session_state.board and card_str not in st.session_state.hole:
                        st.session_state.board.append(card_str)
                        st.rerun()

st.divider()

# Bet sizing
st.write("**Bet Scenario:**")
col_bet1, col_bet2, col_bet3, col_bet4, col_bet5 = st.columns(5)
with col_bet1:
    if st.button("Check", use_container_width=True):
        st.session_state.bet = 0
with col_bet2:
    if st.button("1/3 Pot", use_container_width=True):
        st.session_state.bet = max(1, st.session_state.pot // 3)
with col_bet3:
    if st.button("1/2 Pot", use_container_width=True):
        st.session_state.bet = max(1, st.session_state.pot // 2)
with col_bet4:
    if st.button("Full Pot", use_container_width=True):
        st.session_state.bet = st.session_state.pot
with col_bet5:
    if st.button("All-in", use_container_width=True):
        st.session_state.bet = st.session_state.pot * 2

# Pot input
pot_size = st.number_input("Pot Size ($)", min_value=1, value=st.session_state.pot, step=10)
st.session_state.pot = pot_size
bet_to_call = st.session_state.bet

st.caption(f"📊 **Pot: ${pot_size} | Bet to Call: ${bet_to_call}**")

st.divider()

# ANALYSIS
if len(st.session_state.hole) >= 2:
    try:
        hole_cards = [Card(c) for c in st.session_state.hole[:2]]
        board_cards = [Card(c) for c in st.session_state.board]
        
        street = {0: "Pre-flop", 3: "Flop", 4: "Turn", 5: "River"}.get(len(board_cards), "Pre-flop")
        
        equity, draws = calculate_equity_estimate(hole_cards, board_cards)
        hand_category, pair_context = categorize_hand(hole_cards, board_cards)
        board_texture = analyze_board_texture(board_cards)
        
        strat = get_strategic_recommendation(
            hand_category, pair_context, board_texture,
            equity, pot_size, bet_to_call, street
        )
        
        st.markdown(f'<p class="big-font">{strat["action"]}</p>', unsafe_allow_html=True)
        
        if strat["sizing"]:
            st.markdown(f"**Sizing:** {strat['sizing']}")
        
        col_metrics1, col_metrics2, col_metrics3 = st.columns(3)
        with col_metrics1:
            st.metric("Street", street)
        with col_metrics2:
            st.metric("Hand Type", hand_category)
        with col_metrics3:
            st.metric("Equity", f"{equity:.0f}%")
        
        col_details1, col_details2 = st.columns(2)
        with col_details1:
            if board_texture != "N/A":
                st.caption(f"**Board Texture:** {board_texture}")
        with col_details2:
            if pair_context:
                st.caption(f"**Hand Detail:** {pair_context}")
        
        st.info(f"**Reasoning:** {strat['reasoning']}")
        st.success(f"**Game Plan:** {strat['game_plan']}")
        
    except Exception as e:
        st.error(f"Error: {str(e)}")
else:
    st.info("👆 Select 2 hole cards to get started (board is optional)")
