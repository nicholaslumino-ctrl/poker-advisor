import streamlit as st
from itertools import combinations
from collections import Counter

RANKS = '23456789TJQKA'
RANK_VALUES = {r: i for i, r in enumerate(RANKS, 2)}

class Card:
    def __init__(self, card_str):
        self.rank = card_str[0].upper()
        self.suit = card_str[1].lower()
        self.value = RANK_VALUES[self.rank]
    def __repr__(self):
        return f"{self.rank}{self.suit}"

def parse_cards(card_string):
    return [Card(c) for c in card_string.split()]

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

def hand_strength_score(rank_tuple):
    return (rank_tuple[0] * 12.5) + min(sum(rank_tuple[1]) / 14, 1) * 5

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
            draw_types.append("Open-Ended Straight Draw")
            break
    return outs, draw_types

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

def get_recommendation(equity, pot_size, bet_to_call):
    if bet_to_call == 0:
        if equity > 60:
            return "🟢 BET/RAISE for value", None
        elif equity > 35:
            return "🟡 CHECK or small BET", None
        else:
            return "⚪ CHECK", None
    pot_odds = bet_to_call / (pot_size + bet_to_call) * 100
    if equity > pot_odds + 15:
        rec = "🟢 RAISE (strong value)"
    elif equity > pot_odds:
        rec = "🟢 CALL (profitable)"
    elif equity > pot_odds - 10:
        rec = "🟡 MARGINAL - consider position/reads"
    else:
        rec = "🔴 FOLD (insufficient equity)"
    return rec, pot_odds

st.set_page_config(page_title="Hold'em Advisor", page_icon="🃏")
st.title("🃏 Texas Hold'em Advisor")

col1, col2 = st.columns(2)
with col1:
    hole_input = st.text_input("Your Hole Cards", placeholder="e.g., Ah Kh")
with col2:
    board_input = st.text_input("Board Cards", placeholder="e.g., Qh Jh 2c")

col3, col4, col5 = st.columns(3)
with col3:
    pot_size = st.number_input("Pot Size", min_value=0, value=100)
with col4:
    bet_to_call = st.number_input("Bet to Call", min_value=0, value=0)
with col5:
    num_opp = st.number_input("Opponents", min_value=1, value=1)

if st.button("🔍 Analyze Hand", use_container_width=True):
    if not hole_input:
        st.error("Please enter your hole cards!")
    else:
        try:
            hole_cards = parse_cards(hole_input)
            board_cards = parse_cards(board_input) if board_input else []
            
            street = {0: "Pre-flop", 3: "Flop", 4: "Turn", 5: "River"}.get(len(board_cards), "?")
            st.subheader(f"📍 Street: {street}")
            
            if len(board_cards) >= 3:
                all_cards = hole_cards + board_cards
                rank = evaluate_hand(all_cards)
                st.info(f"**Current Best Hand:** {HAND_NAMES[rank[0]]}")
            
            equity, draws = calculate_equity_estimate(hole_cards, board_cards)
            
            if draws:
                st.warning(f"**Draws:** {', '.join(set(draws))}")
            
            st.metric("Estimated Equity", f"{equity:.1f}%")
            
            recommendation, pot_odds = get_recommendation(equity, pot_size, bet_to_call)
            
            if pot_odds:
                st.caption(f"Pot odds needed: {pot_odds:.1f}%")
            
            st.markdown(f"## {recommendation}")
            
        except Exception as e:
            st.error(f"Error parsing cards: {e}. Use format like 'Ah Kd Ts'")

st.markdown("---")
st.caption("Card format: Rank+Suit (e.g. Ah=Ace hearts, Td=Ten diamonds, 2c, Ks, Qs)")
