"""
src/parsers/lin_parser.py

Handles the extraction of raw data from LIN files .
LIN files are messy, pipe-delimited strings used by BBO.

CRITICAL ASSUMPTION:
This parser converts the obscure LIN format into clean Python dictionaries
that the 'Referees' (Validators) can consume directly.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from loguru import logger

@dataclass
class BridgeGame:
    """
    Represents a single board parsed from a LIN file.
    """
    board_id: str
    player_names: Dict[str, str]  # {'S': 'User1', 'W': 'Bot', ...}
    dealer: str # 'N', 'S', 'E', 'W'
    vulnerability: str # 'None', 'NS', 'EW', 'All'
    
    # The Deal: {'S': {'S': ['K',...], 'H':...}, 'W': ...}
    hands: Dict[str, Dict[str, List[str]]] 
    
    # The Auction: List of bids ['1N', 'p', '2C', 'p']
    auction: List[str]
    
    # The Play: List of cards played ['SA', 'S2', ...]
    play_log: List[str]

class LinParser:
    """
    A robust, regex-based parser for LIN files.
    """

    # Mapping LIN dealer codes to Compass
    DEALER_MAP = {'1': 'S', '2': 'W', '3': 'N', '4': 'E'}
    
    # Mapping LIN vulnerability codes
    # o = None, n = NS, e = EW, b = Both
    VUL_MAP = {'o': 'None', '0': 'None', 'n': 'NS', 'e': 'EW', 'b': 'All'}

    @staticmethod
    def _parse_hand_string(hand_str: str) -> Dict[str, List[str]]:
        """
        Parses a single hand string like 'STHKD432C2' into a dict.
        Handles the case where suit markers (S, H, D, C) might be absent if void?
        Actually, LIN format usually looks like: S...H...D...C...
        """
        suits = {'S': [], 'H': [], 'D': [], 'C': []}
        if not hand_str:
            return suits
            
        # Regex to find suit markers and the cards following them
        # Matches 'S' followed by chars that are NOT S,H,D,C
        pattern = re.compile(r"([SHDC])([^SHDC]*)")
        matches = pattern.findall(hand_str)
        
        for suit_char, cards in matches:
            # Clean up the cards string (sometimes has trailing junk)
            clean_cards = list(cards.strip())
            suits[suit_char] = clean_cards
            
        return suits

    @staticmethod
    def _fill_missing_hand(hands: Dict[str, Dict[str, List[str]]]) -> Dict[str, Dict[str, List[str]]]:
        """
        If the LIN file omits the 4th hand (common optimization), calculate it.
        This prevents the 'HandValidator' from crashing on the 4th player.
        """
        # 1. Check which hand is missing
        missing_seat = None
        for seat in ['S', 'W', 'N', 'E']:
            if not hands.get(seat):
                missing_seat = seat
                break
        
        if not missing_seat:
            return hands # All present

        # 2. Reconstruct the deck
        full_deck = {
            'S': set('AKQJT98765432'),
            'H': set('AKQJT98765432'),
            'D': set('AKQJT98765432'),
            'C': set('AKQJT98765432')
        }
        
        # 3. Remove known cards
        for seat, hand in hands.items():
            if seat == missing_seat: continue
            for suit, cards in hand.items():
                for card in cards:
                    # Handle '10' vs 'T' standardization if needed
                    c = 'T' if card == '10' else card
                    if c in full_deck[suit]:
                        full_deck[suit].remove(c)

        # 4. Assign remaining to missing seat
        restored_hand = {}
        for suit in ['S', 'H', 'D', 'C']:
            # Sort for consistency (High to Low)
            # Define rank order
            ranks = "AKQJT98765432"
            sorted_cards = sorted(list(full_deck[suit]), key=lambda x: ranks.index(x))
            restored_hand[suit] = sorted_cards
            
        hands[missing_seat] = restored_hand
        return hands

    @classmethod
    def parse_file(cls, file_path: str) -> List[BridgeGame]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return cls.parse_content(content)
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return []

    @classmethod
    def parse_content(cls, content: str) -> List[BridgeGame]:
        """
        Main parsing logic.
        Splits content by line/record and extracts 'qx' (board), 'md' (deal), etc.
        """
        games = []
        
        # LIN files often have one game per line, or one massive line.
        # We assume standard BBO export format where pipe delimiters dictate fields.
        
        # A crude but effective way to split multiple games in one file
        # is often looking for the 'qx' tag (Board ID). 
        # But simpler: Treat the whole string as a stream of tags.
        
        # Tokenize by pipe '|'
        tokens = content.split('|')
        
        # State machine variables
        current_board_id = "Unknown"
        current_players = {}
        current_dealer = 'S'
        current_vul = 'None'
        current_hands = {}
        current_auction = []
        current_play = []
        
        # Helper to commit a game to the list
        def commit_game():
            if current_hands:
                # Fill missing hand if any
                full_hands = cls._fill_missing_hand(current_hands)
                
                game = BridgeGame(
                    board_id=current_board_id,
                    player_names=current_players.copy(),
                    dealer=current_dealer,
                    vulnerability=current_vul,
                    hands=full_hands,
                    auction=current_auction.copy(),
                    play_log=current_play.copy()
                )
                games.append(game)
        
        # Iterate tokens
        i = 0
        while i < len(tokens):
            tag = tokens[i]
            
            # 1. BOARD ID (qx) - usually starts a new segment
            if tag == 'qx':
                if i+1 < len(tokens):
                    # If we already have data, commit previous game
                    # (This logic implies we reset on every new board ID)
                    if current_hands: 
                        commit_game()
                        # Reset
                        current_auction = []
                        current_play = []
                        current_hands = {}
                    
                    # Set new ID (e.g., 'o1')
                    current_board_id = tokens[i+1]
                    i += 1

            # 2. PLAYERS (pn)
            elif tag == 'pn':
                if i+1 < len(tokens):
                    p_str = tokens[i+1]
                    names = p_str.split(',')
                    # Usually: South, West, North, East
                    seats = ['S', 'W', 'N', 'E']
                    for idx, name in enumerate(names):
                        if idx < 4:
                            current_players[seats[idx]] = name
                    i += 1

            # 3. DEAL (md)
            elif tag == 'md':
                if i+1 < len(tokens):
                    deal_str = tokens[i+1]
                    # Format: digit{South},{West},{North},{East}
                    # e.g., "1S...H...,...,..."
                    
                    if deal_str and deal_str[0].isdigit():
                        dealer_digit = deal_str[0]
                        current_dealer = cls.DEALER_MAP.get(dealer_digit, 'S')
                        
                        # The hands follow the dealer digit
                        hands_part = deal_str[1:]
                        hand_strs = hands_part.split(',')
                        
                        # LIN hands are ALWAYS ordered: South, West, North, East
                        # Regardless of who the dealer is.
                        seats = ['S', 'W', 'N', 'E']
                        temp_hands = {}
                        
                        for idx, h_str in enumerate(hand_strs):
                            if idx < 4:
                                temp_hands[seats[idx]] = cls._parse_hand_string(h_str)
                        
                        current_hands = temp_hands
                    i += 1

            # 4. VULNERABILITY (sv)
            elif tag == 'sv':
                if i+1 < len(tokens):
                    v_code = tokens[i+1]
                    current_vul = cls.VUL_MAP.get(v_code, 'None')
                    i += 1

            # 5. BIDS (mb) - These appear sequentially
            elif tag == 'mb':
                if i+1 < len(tokens):
                    bid = tokens[i+1]
                    # Normalize bid strings (e.g., 'p' -> 'PASS') if desired
                    # For now keep raw
                    if bid:
                        current_auction.append(bid)
                    i += 1

            # 6. PLAY (pc) - These appear sequentially
            elif tag == 'pc':
                if i+1 < len(tokens):
                    card = tokens[i+1]
                    if card:
                        current_play.append(card)
                    i += 1

            i += 1
            
        # Commit the final game found in the file
        if current_hands:
            commit_game()
            
        return games

# Example Check
if __name__ == "__main__":
    # A dummy LIN string fragment for testing
    # Board o1, Dealer South, Vul None
    # South holds Spades AKQ...
    # Auction: 1NT - Pass...
    dummy_lin = "qx|o1|pn|SouthBot,WestBot,NorthBot,EastBot|md|1SAKQHAKQD432C432,S432...||sv|0|mb|1N|mb|p|mb|p|mb|p|pc|S4|"
    
    parsed_games = LinParser.parse_content(dummy_lin)
    for g in parsed_games:
        print(f"Board: {g.board_id}")
        print(f"Dealer: {g.dealer}")
        print(f"South Hand S: {g.hands['S'].get('S')}")
        print(f"Auction: {g.auction}")
        print(f"Play Start: {g.play_log}")