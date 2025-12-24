"""
src/core/referee.py

THE REFEREE (Logic Engine)
--------------------------
Evaluates hands based on strict Bridge rules (HCP, Shape, Vulnerability).
This prevents the AI from "hallucinating" the point count or opening bids.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class DealerMetrics:
    hcp: int
    distribution: str  # e.g., "5-3-3-2"
    suggested_opening: str
    rule_explanation: str

@dataclass
class ResponderMetrics:
    hcp: int
    suggested_response: str
    convention: str

class Referee:
    def __init__(self):
        self.suit_order = ['S', 'H', 'D', 'C']

    def _calculate_hcp(self, hand: Dict[str, List[str]]) -> int:
        """Counts High Card Points (A=4, K=3, Q=2, J=1)."""
        hcp = 0
        values = {'A': 4, 'K': 3, 'Q': 2, 'J': 1}
        for suit in hand.values():
            for card in suit:
                # Handle 'T' or '10' or 'K'
                if not card: continue
                rank = card[0].upper()
                if rank in values:
                    hcp += values[rank]
        return hcp

    def _get_distribution(self, hand: Dict[str, List[str]]) -> str:
        """Returns shape string like '5-3-3-2'."""
        lengths = []
        # Sort by length descending for standard shape notation
        for s in self.suit_order:
            lengths.append(len(hand.get(s, [])))
        lengths.sort(reverse=True)
        return "-".join(map(str, lengths))

    def _is_balanced(self, hand: Dict[str, List[str]]) -> bool:
        """Checks for 4-3-3-3, 4-4-3-2, or 5-3-3-2 shapes."""
        shape = self._get_distribution(hand)
        return shape in ["4-3-3-3", "4-4-3-2", "5-3-3-2"]

    def _longest_suit(self, hand: Dict[str, List[str]]) -> str:
        """Returns the suit key (S, H, D, C) of the longest suit."""
        best_suit = 'S'
        max_len = -1
        # Check in standard rank order (S, H, D, C) so higher suits win ties
        for s in self.suit_order:
            l = len(hand.get(s, []))
            if l > max_len:
                max_len = l
                best_suit = s
        return best_suit

    def analyze_dealer_opening(self, seat: str, hand: Dict[str, List[str]], vul: str) -> DealerMetrics:
        """
        Determines the mathematically correct opening bid.
        """
        hcp = self._calculate_hcp(hand)
        shape = self._get_distribution(hand)
        balanced = self._is_balanced(hand)
        longest = self._longest_suit(hand)
        
        # LOGIC TREE
        bid = "PASS"
        reason = f"Insufficient values ({hcp} HCP)."

        # 1. STRONG OPENINGS
        if hcp >= 22:
            bid = "2C"
            reason = "Strong Opening (22+ HCP)"
        
        # 2. NOTRUMP LADDER
        elif balanced and 20 <= hcp <= 21:
            bid = "2NT"
            reason = "20-21 HCP, Balanced"
        elif balanced and 15 <= hcp <= 17:
            bid = "1NT"
            reason = "15-17 HCP, Balanced"
            
        # 3. SUIT OPENINGS (Rule of 20 check could go here)
        elif hcp >= 12:
            # Simple logic: Open longest suit
            # If 5-card Major, open it. Else open minor.
            s_len = len(hand.get('S', []))
            h_len = len(hand.get('H', []))
            
            if s_len >= 5 and s_len >= h_len:
                bid = "1S"
                reason = "12+ HCP, 5+ Spades"
            elif h_len >= 5:
                bid = "1H"
                reason = "12+ HCP, 5+ Hearts"
            else:
                # Minors: Better Minor
                d_len = len(hand.get('D', []))
                c_len = len(hand.get('C', []))
                if d_len > c_len:
                    bid = "1D"
                elif c_len > d_len:
                    bid = "1C"
                elif d_len == 3 and c_len == 3:
                    bid = "1C" # Standard 3-3
                else:
                    bid = "1D" # 4-4 Diamonds usually
                reason = "12+ HCP, No 5-card Major, Better Minor"

        # 4. PREEMPTS (Weak 2, 3, etc.)
        elif 6 <= hcp <= 10:
            long_suit_char = self._longest_suit(hand)
            long_suit_len = len(hand.get(long_suit_char, []))
            
            if long_suit_len == 6:
                bid = f"2{long_suit_char}"
                reason = f"Weak 2 (6-card {long_suit_char}, 6-10 HCP)"
            elif long_suit_len >= 7:
                bid = f"3{long_suit_char}"
                reason = f"Preempt (7+ card {long_suit_char}, Weak)"

        return DealerMetrics(
            hcp=hcp,
            distribution=shape,
            suggested_opening=bid,
            rule_explanation=reason
        )

    def analyze_response(self, seat: str, hand: Dict[str, List[str]], partner_bid: str, auction: List[str]) -> ResponderMetrics:
        """
        Very basic response logic logic.
        """
        hcp = self._calculate_hcp(hand)
        resp = "PASS"
        conv = "Standard"

        # Placeholder logic for common situations
        if partner_bid == '1NT':
            if hcp >= 8:
                # Check for Stayman/Transfer opportunities?
                # For now, just simplistic:
                resp = "3NT" if hcp >= 10 else "2NT"
                conv = "Quantitative"
            else:
                resp = "PASS"
                conv = "Weak"
                
        elif partner_bid.startswith('1'): # 1 of a suit
            if hcp >= 6:
                resp = "1S" # Placeholder for "Bid your suit"
                conv = "New Suit (Forcing)"
            else:
                resp = "PASS"
                conv = "Weak"

        return ResponderMetrics(
            hcp=hcp,
            suggested_response=resp,
            convention=conv
        )