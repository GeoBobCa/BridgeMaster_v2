"""
src/core/response_validator.py

THE RESPONDER (Module)
----------------------
Determines the valid SAYC *First Response* to an opening bid.
This prevents the AI from hallucinating support without a fit, 
or suggesting a pass with game-going values.

Input: Responder's Hand + Partner's Opening Bid
Output: Suggested Response + Educational Explanation
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from loguru import logger

# Reuse static helpers from HandValidator (assuming they are importable)
# In a real project, these helpers (get_distribution, calculate_hcp) 
# might be moved to a shared 'utils' module. 
# For now, we import the class or duplicate small logic if strictly separated.
from src.core.hand_validator import HandValidator

@dataclass
class ResponseMetrics:
    suggested_response: str
    convention: str # e.g., "Stayman", "Limit Raise", "Natural"
    explanation: str

class ResponseValidator:
    
    @staticmethod
    def _parse_opening(bid: str) -> Tuple[int, str]:
        """Parses '1H' into (1, 'H'). Returns (0, '') if invalid."""
        if not bid or bid.upper() == "PASS":
            return 0, ""
        try:
            level = int(bid[0])
            suit = bid[1:].upper() # 'H', 'S', 'NT' ...
            return level, suit
        except:
            return 0, ""

    @staticmethod
    def _respond_to_major_opening(hcp: int, dist: Dict[str, int], open_suit: str) -> ResponseMetrics:
        """
        Logic for responding to 1H or 1S.
        Priorities:
        1. Support (Fit)
        2. New Major (1S over 1H)
        3. New Minor (2-level requires 10+ HCP)
        4. 1NT (6-9 HCP, no fit)
        """
        
        # 1. CHECK FOR FIT (3+ cards usually supports 5-card major opening)
        support_len = dist.get(open_suit, 0)
        has_fit = support_len >= 3

        if has_fit:
            # Simple Raise System (SAYC)
            if 6 <= hcp <= 9:
                return ResponseMetrics(f"2{open_suit}", "Single Raise", f"6-9 HCP, {support_len}+ card support")
            elif 10 <= hcp <= 12:
                return ResponseMetrics(f"3{open_suit}", "Limit Raise", f"10-12 HCP, {support_len}+ card support")
            elif hcp >= 13:
                # In full SAYC, this might be Jacoby 2NT or Splinter. 
                # For Phase 1, we suggest a Game force or generic game bid.
                return ResponseMetrics(f"4{open_suit}", "Game Raise", f"13+ HCP, Game Forcing values with fit")

        # 2. NO FIT: CHECK FOR SPADES (if partner opened Hearts)
        if open_suit == 'H':
            if dist['S'] >= 4 and hcp >= 6:
                return ResponseMetrics("1S", "Natural", "4+ Spades, 6+ HCP (Forcing)")

        # 3. NO FIT: 1NT RESPONSE (Forcing / Semi-forcing depending on style, SAYC usually 6-9)
        if 6 <= hcp <= 9:
             return ResponseMetrics("1NT", "Natural", "6-9 HCP, No Fit, Denies 4 Spades")

        # 4. NO FIT: NEW SUIT AT 2-LEVEL (Requires 10/11+ HCP)
        if hcp >= 11: # Conservative SAYC standard
            # Look for longest minor
            best_minor = 'D' if dist['D'] >= dist['C'] else 'C'
            if dist[best_minor] >= 4:
                 return ResponseMetrics(f"2{best_minor}", "New Suit (Forcing)", f"11+ HCP, 4+ {best_minor}")

        # 5. PASS
        return ResponseMetrics("PASS", "Weak", "Less than 6 HCP")

    @staticmethod
    def _respond_to_minor_opening(hcp: int, dist: Dict[str, int], open_suit: str) -> ResponseMetrics:
        """
        Logic for responding to 1C or 1D.
        Priority: Find 4-card Major.
        """
        if hcp < 6:
            return ResponseMetrics("PASS", "Weak", "Less than 6 HCP")

        # Check Majors (Up the line? Or longest? SAYC usually up the line or longest)
        # Check Hearts then Spades
        h_len = dist['H']
        s_len = dist['S']

        if h_len >= 4 and s_len >= 4:
            # With 4-4, bid 1H (up the line) usually, unless specific style
            return ResponseMetrics("1H", "Natural", "4-4 Majors, Bid up the line")
        
        if h_len >= 4:
            return ResponseMetrics("1H", "Natural", "4+ Hearts, 6+ HCP")
        
        if s_len >= 4:
            return ResponseMetrics("1S", "Natural", "4+ Spades, 6+ HCP")

        # No 4-card major: Inverted Minors or NT
        # Phase 1: Simple NT ladder
        if 6 <= hcp <= 10:
            return ResponseMetrics("1NT", "Natural", "6-10 HCP, Balanced, No Major")
        if 11 <= hcp <= 12:
            return ResponseMetrics("2NT", "Natural", "11-12 HCP, Balanced, No Major (Invitational)")
        if 13 <= hcp <= 15:
            return ResponseMetrics("3NT", "Natural", "13-15 HCP, Balanced, Game Values")

        # Fallback to minor raise if unbalanced (rare if no major)
        return ResponseMetrics(f"2{open_suit}", "Simple Raise", "6-9 HCP, Support, No Major")

    @staticmethod
    def _respond_to_1nt(hcp: int, dist: Dict[str, int]) -> ResponseMetrics:
        """
        Logic for responding to 1NT (15-17).
        Includes Stayman and Transfers.
        """
        # 0. Check Weak
        if hcp < 8 and dist['S'] < 5 and dist['H'] < 5 and dist['D'] < 6 and dist['C'] < 6:
             # Typically pass unless very weird shape
             # Actually, transfers can be made with 0 points.
             pass 

        # 1. TRANSFERS (Jacoby) - Takes precedence over Stayman usually if 5+ Major
        if dist['H'] >= 5:
            return ResponseMetrics("2D", "Jacoby Transfer", "5+ Hearts (Transfer to Hearts)")
        if dist['S'] >= 5:
            return ResponseMetrics("2H", "Jacoby Transfer", "5+ Spades (Transfer to Spades)")

        # 2. STAYMAN (4-card Major, 8+ HCP)
        if hcp >= 8:
            if dist['H'] == 4 or dist['S'] == 4:
                return ResponseMetrics("2C", "Stayman", "8+ HCP, Asking for 4-card Major")

        # 3. NATURAL NT RAISES
        if 8 <= hcp <= 9:
            return ResponseMetrics("2NT", "Invitational", "8-9 HCP, Balanced, No Major interest")
        if 10 <= hcp <= 15:
            return ResponseMetrics("3NT", "Game", "10-15 HCP, Balanced, No Major interest")

        # 4. PASS (Weak Balanced)
        return ResponseMetrics("PASS", "Weak", "<8 HCP, No 5-card Major")

    @classmethod
    def analyze(cls, cards_by_suit: Dict[str, List[str]], partner_bid: str) -> ResponseMetrics:
        """
        Main entry point for the Responder Logic.
        """
        hcp = HandValidator._calculate_hcp(cards_by_suit)
        dist = HandValidator._get_distribution(cards_by_suit)
        
        level, suit = cls._parse_opening(partner_bid)

        # Default fallback if parsing fails or unhandled bid (like 2C strong)
        if level == 0:
            return ResponseMetrics("UNKNOWN", "N/A", "Could not parse partner bid or Partner Passed")

        # Route logic based on suit
        if suit in ['H', 'S']:
            return cls._respond_to_major_opening(hcp, dist, suit)
        elif suit in ['C', 'D']:
            # Differentiate strong 2C? 
            # If level is 2 and suit is C, that's Strong. 
            # For Phase 1 we treat 1C/1D standard.
            if level == 1:
                return cls._respond_to_minor_opening(hcp, dist, suit)
        elif suit == 'NT':
            if level == 1:
                return cls._respond_to_1nt(hcp, dist)
        
        return ResponseMetrics("N/A", "Complex", "Logic for this auction path not yet implemented")

# Example usage for testing
if __name__ == "__main__":
    # Test: Partner opens 1NT. We have 9 HCP and 4 Spades.
    test_hand = {
        'S': ['K', 'J', '9', '2'],
        'H': ['Q', '3', '2'],
        'D': ['K', '4', '2'],
        'C': ['9', '8', '2']
    }
    # Expected: 2C (Stayman)
    
    result = ResponseValidator.analyze(test_hand, "1NT")
    print(f"Partner 1NT -> We Bid: {result.suggested_response} ({result.convention})")

    # Test: Partner opens 1H. We have 7 HCP and 3 Hearts.
    test_hand_2 = {
        'S': ['8', '2'],
        'H': ['K', '7', '5'], # 3 card support
        'D': ['A', 'J', '4', '2'],
        'C': ['9', '8', '5', '4']
    }
    # Expected: 2H (Single Raise)
    result2 = ResponseValidator.analyze(test_hand_2, "1H")
    print(f"Partner 1H -> We Bid: {result2.suggested_response} ({result2.convention})")