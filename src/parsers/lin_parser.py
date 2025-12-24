"""
src/parsers/lin_parser.py

Handles the extraction of raw data from LIN files.
Includes logic to reconstruct the 4th hand ('Short Deck') if omitted by BBO.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from loguru import logger

@dataclass
class BridgeGame:
    board_id: str
    player_names: Dict[str, str]
    dealer: str
    vulnerability: str
    hands: Dict[str, Dict[str, List[str]]] 
    auction: List[str]
    play_log: List[str]
    claimed_tricks: Optional[int] = None 

class LinParser:
    # Mapping LIN dealer codes to Compass
    DEALER_MAP = {'1': 'S', '2': 'W', '3': 'N', '4': 'E'}
    VUL_MAP = {'o': 'None', '0': 'None', 'n': 'NS', 'e': 'EW', 'b': 'All'}

    @staticmethod
    def _parse_hand_string(hand_str: str) -> Dict[str, List[str]]:
        suits = {'S': [], 'H': [], 'D': [], 'C': []}
        if not hand_str:
            return suits
            
        pattern = re.compile(r"([SHDC])([^SHDC]*)")
        matches = pattern.findall(hand_str)
        
        for suit_char, cards in matches:
            clean_cards = list(cards.strip())
            suits[suit_char] = clean_cards
        return suits

    @staticmethod
    def _fill_missing_hand(hands: Dict[str, Dict[str, List[str]]]) -> Dict[str, Dict[str, List[str]]]:
        """
        Reconstructs the 4th hand if BBO omitted it.
        Fix: Checks for 0 cards, not just missing keys.
        """
        # 1. Identify the empty/missing seat
        missing_seat = None
        
        # Check all 4 seats
        for seat in ['S', 'W', 'N', 'E']:
            hand = hands.get(seat)
            
            # Condition A: Seat key doesn't exist
            if hand is None:
                missing_seat = seat
                break
                
            # Condition B: Seat exists but has 0 cards (The "Short Deck" bug)
            card_count = sum(len(cards) for cards in hand.values())
            if card_count == 0:
                missing_seat = seat
                break
        
        # If everyone has cards, we are good
        if not missing_seat:
            return hands 

        # 2. Build a full deck
        full_deck = {
            'S': set('AKQJT98765432'),
            'H': set('AKQJT98765432'),
            'D': set('AKQJT98765432'),
            'C': set('AKQJT98765432')
        }
        
        # 3. Subtract all known cards
        for seat, hand in hands.items():
            if seat == missing_seat: continue
            
            for suit, cards in hand.items():
                for card in cards:
                    # Normalize '10' to 'T' for set matching if needed
                    c = 'T' if card == '10' else card
                    if c in full_deck[suit]:
                        full_deck[suit].remove(c)

        # 4. Assign remaining cards to the missing seat
        restored_hand = {}
        for suit in ['S', 'H', 'D', 'C']:
            # Sort them nicely (A -> 2)
            ranks = "AKQJT98765432"
            # Helper to sort by rank index
            sorted_cards = sorted(list(full_deck[suit]), key=lambda x: ranks.index(x) if x in ranks else 99)
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
        games = []
        tokens = content.split('|')
        
        current_board_id = "Unknown"
        current_players = {}
        current_dealer = 'S'
        current_vul = 'None'
        current_hands = {}
        current_auction = []
        current_play = []
        current_claimed_tricks = None 
        
        def commit_game():
            if current_hands:
                # Run the 4th hand logic before saving
                full_hands = cls._fill_missing_hand(current_hands)
                
                game = BridgeGame(
                    board_id=current_board_id,
                    player_names=current_players.copy(),
                    dealer=current_dealer,
                    vulnerability=current_vul,
                    hands=full_hands,
                    auction=current_auction.copy(),
                    play_log=current_play.copy(),
                    claimed_tricks=current_claimed_tricks 
                )
                games.append(game)
        
        i = 0
        while i < len(tokens):
            tag = tokens[i].strip()
            
            if tag == 'qx':
                if i+1 < len(tokens):
                    if current_hands: 
                        commit_game()
                        current_auction = []
                        current_play = []
                        current_hands = {}
                        current_claimed_tricks = None
                    current_board_id = tokens[i+1].strip()
                    i += 1

            elif tag == 'pn':
                if i+1 < len(tokens):
                    p_str = tokens[i+1]
                    names = p_str.split(',')
                    seats = ['S', 'W', 'N', 'E']
                    for idx, name in enumerate(names):
                        if idx < 4: current_players[seats[idx]] = name.strip()
                    i += 1

            elif tag == 'md':
                if i+1 < len(tokens):
                    deal_str = tokens[i+1].strip()
                    if deal_str and deal_str[0].isdigit():
                        dealer_digit = deal_str[0]
                        current_dealer = cls.DEALER_MAP.get(dealer_digit, 'S')
                        
                        hands_part = deal_str[1:]
                        hand_strs = hands_part.split(',')
                        seats = ['S', 'W', 'N', 'E']
                        temp_hands = {}
                        for idx, h_str in enumerate(hand_strs):
                            if idx < 4:
                                temp_hands[seats[idx]] = cls._parse_hand_string(h_str)
                        current_hands = temp_hands
                    i += 1

            elif tag == 'sv':
                if i+1 < len(tokens):
                    current_vul = cls.VUL_MAP.get(tokens[i+1].strip(), 'None')
                    i += 1

            elif tag == 'mb':
                if i+1 < len(tokens):
                    bid = tokens[i+1].strip()
                    if bid: current_auction.append(bid)
                    i += 1

            elif tag == 'pc':
                if i+1 < len(tokens):
                    card = tokens[i+1].strip()
                    if card: current_play.append(card)
                    i += 1

            elif tag == 'mc':
                if i+1 < len(tokens):
                    val = tokens[i+1].strip()
                    if val.isdigit(): current_claimed_tricks = int(val)
                    i += 1

            i += 1
            
        if current_hands:
            commit_game()
            
        return games