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
        if is_pair and values[0] >= 12:  # QQ+
            return "PREMIUM", f"{RANKS[values[0]-2]}{RANKS[values[0]-2]} Pair"
        elif is_pair and values[0] >= 10:  # TT+
            return "STRONG", f"{RANKS[values[0]-2]}{RANKS[values[0]-2]} Pair"
        elif is_pair:
            return "MEDIUM", f"{RANKS[values[0]-2]}{RANKS[values[0]-2]} Pair"
        elif values[0] >= 14 and values[1] >= 13:  # AK
            return "STRONG", "AK"
        elif values[0] >= 14 and values[1] >= 12:  # AQ+
            return "STRONG", "AQ+"
        else:
            return "MEDIUM", "Other"
    
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
        return "STRONG", "Three of a Kind"
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

def get_pro_recommendation(hand_category, pair_context, board_texture, equity, pot_size, bet_to_call, street):
    """
    Returns PRO-level advice, not just math.
    Tells you EXACTLY what to do like a poker pro would.
    """
    result = {
        "action": "",
        "reason": "",
        "confidence": ""
    }
    
    facing_bet = bet_to_call > 0
    pot_odds = (bet_to_call / (pot_size + bet_to_call) * 100) if facing_bet else 0
    
    # ===== YOU'RE FIRST TO ACT (No bet to call) =====
    if not facing_bet:
        
        if hand_category == "PREMIUM":
            result["action"] = "✅ GO ALL-IN (or make big raise)"
            result["confidence"] = "VERY HIGH"
            result["reason"] = f"Premium hand on {street}. Build the pot. You'll win from weaker hands or draw thin from strong ones."
        
        elif hand_category == "MONSTER":
            result["action"] = "✅ GO ALL-IN or BET BIG (70-100% pot)"
            result["confidence"] = "VERY HIGH"
            result["reason"] = f"You have {HAND_NAMES.get(evaluate_hand([Card(c) for c in []])[:0], 'made hand')}. Extract max value."
        
        elif hand_category == "STRONG":
            if street == "Pre-flop":
                result["action"] = "✅ RAISE (3-4x big blind)"
                result["confidence"] = "HIGH"
            else:
                result["action"] = "✅ BET (50-70% pot)"
                result["confidence"] = "HIGH"
            result["reason"] = f"Strong hand. Bet to build pot, thin draws, and get value."
        
        elif hand_category == "MEDIUM":
            if board_texture == "DRY":
                result["action"] = "🟡 CHECK or small bet (30% pot)"
                result["confidence"] = "MEDIUM"
                result["reason"] = "Medium strength on dry board. Control the pot. Don't build it too much."
            else:
                result["action"] = "⚪ CHECK"
                result["confidence"] = "MEDIUM"
                result["reason"] = f"Wet board. Check to see what opponent does. You don't want to build the pot with medium strength."
        
        elif hand_category == "DRAWING":
            if pair_context == "Combo Draw":
                result["action"] = "✅ BET BIG (60-80% pot) - Semi-bluff"
                result["confidence"] = "HIGH"
                result["reason"] = "Combo draw has tons of outs. Bet to win now or hit your draw."
            else:
                result["action"] = "⚪ CHECK"
                result["confidence"] = "MEDIUM"
                result["reason"] = "Single draw. See next card cheap."
        
        else:  # AIR
            result["action"] = "⚪ CHECK"
            result["confidence"] = "HIGH"
            result["reason"] = "Nothing yet. Give up this hand and wait for better spot."
    
    # ===== SOMEONE BET AT YOU (you have to decide) =====
    else:
        
        # SMALL bet (under 50% pot)
        if bet_to_call < pot_size * 0.5:
            
            if hand_category == "PREMIUM":
                result["action"] = "✅ RAISE (make it 3-4x their bet)"
                result["confidence"] = "VERY HIGH"
                result["reason"] = "Premium hand. Punish them. Get as much money in as possible."
            
            elif hand_category == "MONSTER":
                result["action"] = "✅ RAISE (make it 2.5-3x their bet)"
                result["confidence"] = "VERY HIGH"
                result["reason"] = f"You have {pair_context or 'a monster'}. Milk them for value."
            
            elif hand_category == "STRONG":
                result["action"] = "✅ CALL (or raise if you want)"
                result["confidence"] = "HIGH"
                result["reason"] = "Strong hand vs small bet. Easy call. You're probably ahead."
            
            elif hand_category == "MEDIUM":
                if equity > pot_odds + 10:
                    result["action"] = "✅ CALL"
                    result["confidence"] = "MEDIUM"
                    result["reason"] = f"Medium hand but bet is small. {equity:.0f}% equity > {pot_odds:.0f}% pot odds. Call."
                else:
                    result["action"] = "🔴 FOLD"
                    result["confidence"] = "MEDIUM"
                    result["reason"] = f"Not profitable. Your equity {equity:.0f}% < pot odds {pot_odds:.0f}%."
            
            elif hand_category == "DRAWING":
                if equity > pot_odds:
                    result["action"] = "✅ CALL (semi-bluff raise if strong draw)"
                    result["confidence"] = "MEDIUM-HIGH"
                    result["reason"] = f"Draw has {equity:.0f}% equity > {pot_odds:.0f}% needed. Good call."
                else:
                    result["action"] = "🔴 FOLD"
                    result["confidence"] = "MEDIUM"
                    result["reason"] = "Not enough outs to justify the call."
            
            else:  # AIR
                result["action"] = "🔴 FOLD"
                result["confidence"] = "HIGH"
                result["reason"] = "You have nothing. Don't throw money away."
        
        # MEDIUM bet (50%-150% pot)
        elif bet_to_call < pot_size * 1.5:
            
            if hand_category == "PREMIUM":
                result["action"] = "✅ GO ALL-IN"
                result["confidence"] = "VERY HIGH"
                result["reason"] = "Premium hand. Push hard. Make them pay or fold."
            
            elif hand_category == "MONSTER":
                result["action"] = "✅ GO ALL-IN"
                result["confidence"] = "VERY HIGH"
                result["reason"] = "You have the best hand type. Get all the money in."
            
            elif hand_category == "STRONG":
                if equity > 60:
                    result["action"] = "✅ GO ALL-IN or raise big"
                    result["confidence"] = "HIGH"
                    result["reason"] = f"Strong hand with high equity ({equity:.0f}%). Push them."
                else:
                    result["action"] = "✅ CALL"
                    result["confidence"] = "MEDIUM-HIGH"
                    result["reason"] = f"Strong hand but equity only {equity:.0f}%. Call and see what happens."
            
            elif hand_category == "MEDIUM":
                result["action"] = "🔴 FOLD"
                result["confidence"] = "MEDIUM-HIGH"
                result["reason"] = "Medium hand can't stand this pressure. Fold and live to play another hand."
            
            elif hand_category == "DRAWING":
                if equity > 45 and pair_context == "Combo Draw":
                    result["action"] = "✅ CALL or GO ALL-IN (semi-bluff)"
                    result["confidence"] = "MEDIUM"
                    result["reason"] = f"Combo draw has {equity:.0f}% equity. Strong enough to get it in."
                elif equity > pot_odds:
                    result["action"] = "✅ CALL"
                    result["confidence"] = "MEDIUM"
                    result["reason"] = f"Draw profitable to call at {equity:.0f}% vs {pot_odds:.0f}%."
                else:
                    result["action"] = "🔴 FOLD"
                    result["confidence"] = "MEDIUM"
                    result["reason"] = "Draw not strong enough for this bet size."
            
            else:  # AIR
                result["action"] = "🔴 FOLD"
                result["confidence"] = "HIGH"
                result["reason"] = "Nothing to justify continuing."
        
        # BIG bet (over 150% pot, basically all-in)
        else:
            
            if hand_category == "PREMIUM":
                result["action"] = "✅ CALL ALL-IN"
                result["confidence"] = "VERY HIGH"
                result["reason"] = "Premium hand. You're going to showdown. Call."
            
            elif hand_category == "MONSTER":
                result["action"] = "✅ CALL ALL-IN"
                result["confidence"] = "VERY HIGH"
                result["reason"] = f"You have {pair_context}. This is a coinflip at best for them. Call."
            
            elif hand_category == "STRONG":
                if equity > 55:
                    result["action"] = "✅ CALL ALL-IN"
                    result["confidence"] = "HIGH"
                    result["reason"] = f"Strong hand with {equity:.0f}% equity. You're ahead. Call."
                elif equity > 45:
                    result["action"] = "🟡 CALL if you want to gamble"
                    result["confidence"] = "LOW"
                    result["reason"] = f"Close call at {equity:.0f}% equity. It's a flip/slight advantage."
                else:
                    result["action"] = "🔴 FOLD"
                    result["confidence"] = "MEDIUM"
                    result["reason"] = f"Strong hand but only {equity:.0f}% equity. You're behind. Fold."
            
            elif hand_category == "MEDIUM":
                result["action"] = "🔴 FOLD"
                result["confidence"] = "HIGH"
                result["reason"] = "Medium strength can't win all-in. Fold."
            
            elif hand_category == "DRAWING":
                if equity > 40 and pair_context == "Combo Draw":
                    result["action"] = "🟡 CALL if you can afford it (gamble)"
                    result["confidence"] = "LOW"
                    result["reason"] = f"Combo draw is {equity:.0f}% — close to a coin flip. Risky but possible."
                else:
                    result["action"] = "🔴 FOLD"
                    result["confidence"] = "HIGH"
                    result["reason"] = f"Draw only {equity:.0f}%. Not worth the risk all-in."
            
            else:  # AIR
                result["action"] = "🔴 FOLD"
                result["confidence"] = "VERY HIGH"
                result["reason"] = "You have absolutely nothing. Easy fold."
    
    return result

# ============ STREAMLIT UI ============
st.set_page_config(page_title="Pro Poker Advisor", page_icon="🃏", layout="wide")

st.markdown("""
<style>
    .action-font {font-size:48px !important; font-weight:bold; text-align:center; margin:30px 0;}
    .high-conf {color: #00AA00;}
    .med-conf {color: #FF9900;}
    .low-conf {color: #FF0000;}
    div.stButton > button {height:45px; font-size:16px; font-weight:bold;}
</style>
""", unsafe_allow_html=True)

st.title("🃏 Pro Poker Advisor")
st.caption("*No math, just what a pro would do*")

if 'hole' not in st.session_state:
    st.session_state.hole = []
if 'board' not in st.session_state:
    st.session_state.board = []
if 'pot' not in st.session_state:
    st.session_state.pot = 100

def cards_to_html(card_list):
    out = []
    for c in card_list:
        rank, suit = c[0], c[1]
        color = SUIT_COLOR[suit]
        symbol = SUIT_SYMBOLS[suit]
        out.append(f'<span style="color:{color}; font-size:32px; margin-right:6px; font-weight:bold;">{rank}{symbol}</span>')
    return ''.join(out) if out else "<i style='color:gray;'>none</i>"

col_disp1, col_disp2 = st.columns(2)
with col_disp1:
    st.write(f"**Your Hand:** {cards_to_html(st.session_state.hole)}", unsafe_allow_html=True)
with col_disp2:
    st.write(f"**Board:** {cards_to_html(st.session_state.board)}", unsafe_allow_html=True)

col_clear1, col_clear2 = st.columns(2)
with col_clear1:
    if st.button("🗑️ Clear Hand", use_container_width=True):
        st.session_state.hole = []
        st.rerun()
with col_clear2:
    if st.button("🗑️ Clear Board", use_container_width=True):
        st.session_state.board = []
        st.rerun()

st.divider()

mode = st.radio("👆 Select for:", ["Hand", "Board"], horizontal=True)

st.write("**Click cards to add:**")

suits_list = ['s', 'h', 'd', 'c']
for suit in suits_list:
    st.write(f"**{SUIT_SYMBOLS[suit]} {['Spades', 'Hearts', 'Diamonds', 'Clubs'][suits_list.index(suit)]}**")
    cols = st.columns(13)
    for i, rank in enumerate(RANKS):
        card_str = rank + suit
        with cols[i]:
            if st.button(f"{rank}{SUIT_SYMBOLS[suit]}", key=card_str, use_container_width=True):
                if mode == "Hand":
                    if len(st.session_state.hole) < 2 and card_str not in st.session_state.hole:
                        st.session_state.hole.append(card_str)
                        st.rerun()
                else:
                    if len(st.session_state.board) < 5 and card_str not in st.session_state.board and card_str not in st.session_state.hole:
                        st.session_state.board.append(card_str)
                        st.rerun()

st.divider()

st.write("**What's happening?**")
action = st.radio("Select situation:", ["You're first to act (no bet)", "Someone bet at you"], horizontal=True)

pot_size = st.number_input("Pot Size ($)", min_value=1, value=st.session_state.pot, step=10)
st.session_state.pot = pot_size

if action == "Someone bet at you":
    bet_to_call = st.number_input("How much to call? ($)", min_value=1, value=50, step=10)
else:
    bet_to_call = 0

st.caption(f"📊 **Pot: ${pot_size}** | **To Call: ${bet_to_call}**")

st.divider()

if len(st.session_state.hole) >= 2:
    try:
        hole_cards = [Card(c) for c in st.session_state.hole[:2]]
        board_cards = [Card(c) for c in st.session_state.board]
        
        street = {0: "Pre-flop", 3: "Flop", 4: "Turn", 5: "River"}.get(len(board_cards), "Pre-flop")
        
        equity, draws = calculate_equity_estimate(hole_cards, board_cards)
        hand_category, pair_context = categorize_hand(hole_cards, board_cards)
        board_texture = analyze_board_texture(board_cards)
        
        rec = get_pro_recommendation(
            hand_category, pair_context, board_texture,
            equity, pot_size, bet_to_call, street
        )
        
        # MAIN ACTION
        conf_color = "high-conf" if rec["confidence"] == "VERY HIGH" else ("med-conf" if "HIGH" in rec["confidence"] else "low-conf")
        st.markdown(f'<p class="action-font {conf_color}">{rec["action"]}</p>', unsafe_allow_html=True)
        
        st.markdown(f'<p style="font-size:20px; text-align:center; font-weight:bold; color:#333;">{rec["confidence"]}</p>', unsafe_allow_html=True)
        
        # REASONING
        st.info(f"**Why?** {rec['reason']}")
        
        # DETAILS
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Street", street)
        with col2:
            st.metric("Hand", hand_category)
        with col3:
            st.metric("Equity", f"{equity:.0f}%")
        with col4:
            if board_texture != "N/A":
                st.metric("Board", board_texture)
        
        if pair_context:
            st.caption(f"📍 **Hand Detail:** {pair_context}")
        
    except Exception as e:
        st.error(f"Error: {str(e)}")
else:
    st.info("👆 Select 2 hole cards to get started")
