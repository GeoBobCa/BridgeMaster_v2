"""
src/core/hand_validator.py

THE REFEREE (Module) - v2.0
--------------------
Updates:
- Added Strong 2C logic (22+ HCP)
- Added Weak 2 logic (6-card suit, 5-10 HCP)
- Added Preemptive 3-level logic (7-card suit, < opening strength)
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple
from loguru import logger

@dataclass
class HandMetrics:
    hcp: int
    distribution: Dict[str, int]
    is_balanced: bool
    suggested_opening: str
    rule_explanation: str

class HandValidator:
    HCP_VALUES = {'A': 4, 'K': 3, 'Q': 2, 'J': 1}
    SUITS = ['S', 'H', 'D', 'C']

    @staticmethod
    def _calculate_hcp(cards_by_suit: Dict[str, List[str]]) -> int:
        points = 0
        for suit in HandValidator.SUITS:
            for card in cards_by_suit.get(suit, []):
                points += HandValidator.HCP_VALUES.get(card.upper(), 0)
        return points

    @staticmethod
    def _get_distribution(cards_by_suit: Dict[str, List[str]]) -> Dict[str, int]:
        return {s: len(cards_by_suit.get(s, [])) for s in HandValidator.SUITS}

    @staticmethod
    def _is_balanced(dist: Dict[str, int]) -> bool:
        """
        Balanced: No voids/singletons, max one doubleton.
        Usually 4333, 4432, 5332.
        """
        lengths = list(dist.values())
        if 0 in lengths or 1 in lengths:
            return False
        if lengths.count(2) > 1:
            return False
        # 5-card major 5332 is often treated as balanced for 1NT rebid purposes, 
        # but for Opening 1NT, usually 5M is allowed in modern SAYC.
        if max(lengths) > 5:
            return False
        return True

    @staticmethod
    def _determine_sayc_opening(hcp: int, dist: Dict[str, int], is_balanced: bool) -> Tuple[str, str]:
        """
        Full SAYC Logic Tree:
        1. Strong 2C (22+)
        2. 1NT / 2NT
        3. Standard 1-level Suit
        4. Weak 2s
        5. Preempts (3-level)
        6. Pass
        """

        # --- 1. THE STRONG HAND (2C) ---
        # SAYC: 22+ HCP is the benchmark for an artificial 2C opening.
        if hcp >= 22:
            return "2C", "Strong Opening (22+ HCP)"


        # --- 2. NOTRUMP LADDER ---
        # 2NT: 20-21 Balanced
        if 20 <= hcp <= 21 and is_balanced:
            return "2NT", "20-21 HCP, Balanced"
        
        # 1NT: 15-17 Balanced
        if 15 <= hcp <= 17 and is_balanced:
            return "1NT", "15-17 HCP, Balanced"


        # --- 3. NORMAL OPENING BIDS (12-21 HCP) ---
        if hcp >= 12:
            # Check Majors (5+ cards)
            s_len = dist['S']
            h_len = dist['H']
            
            if s_len >= 5 or h_len >= 5:
                if s_len > h_len:
                    return "1S", "Longest Major (5+ Spades)"
                elif h_len > s_len:
                    return "1H", "Longest Major (5+ Hearts)"
                else:
                    return "1S", "5-5 Majors, Open Higher"

            # Check Minors (Better/Longer)
            d_len = dist['D']
            c_len = dist['C']
            
            if d_len > c_len:
                return "1D", "Longest Minor"
            elif c_len > d_len:
                return "1C", "Longest Minor"
            else:
                # Equal length minor rules
                if d_len == 4: return "1D", "4-4 Minors, Standard 1D"
                if d_len == 3: return "1C", "3-3 Minors, Standard 1C"
                return "1D", "5-5 Minors, Open Higher"


        # --- 4. PREEMPTIVE BIDS (<12 HCP) ---
        # NOTE: Good suit quality (2 of top 3 honors) is usually required,
        # but for this Phase 1 validator, we use Length + HCP range.

        # WEAK 2s: 6-card suit, 5-10 HCP. (Not Clubs)
        if 5 <= hcp <= 10:
            # Check Diamonds, Hearts, Spades for length 6 exactly
            for suit in ['S', 'H', 'D']:
                if dist[suit] == 6:
                    return f"2{suit}", f"Weak 2 (6-card {suit}, 5-10 HCP)"

        # PREEMPTIVE 3-LEVEL: 7-card suit, < Opening Strength
        # Usually hcp is roughly 6-10 depending on vulnerability, 
        # but strictly <12 is the ceiling.
        if hcp < 12:
            for suit in ['S', 'H', 'D', 'C']:
                if dist[suit] >= 7:
                    return f"3{suit}", f"Preemptive (7+ card {suit})"


        # --- 5. PASS ---
        return "PASS", "Insufficient values for opening"

    @classmethod
    def analyze(cls, cards_by_suit: Dict[str, List[str]]) -> HandMetrics:
        logger.debug("Referee analyzing hand...")
        
        hcp = cls._calculate_hcp(cards_by_suit)
        dist = cls._get_distribution(cards_by_suit)
        balanced = cls._is_balanced(dist)
        
        bid, reason = cls._determine_sayc_opening(hcp, dist, balanced)
        
        metrics = HandMetrics(
            hcp=hcp,
            distribution=dist,
            is_balanced=balanced,
            suggested_opening=bid,
            rule_explanation=reason
        )
        return metrics