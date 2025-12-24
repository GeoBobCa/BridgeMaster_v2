"""
src/core/dd_solver.py

THE ORACLE (Final Fix)
----------------------
Handles both Dictionary hands AND Deal objects to prevent crashes.
"""

from dataclasses import dataclass
from typing import Dict, Optional, List, Union
from loguru import logger

# --- IMPORT BLOCK ---
try:
    # Try the newer structure first
    from endplay.types import Deal, Denom, Player
    from endplay.dd import calc_dd_table
except ImportError:
    try:
        # Fallback to older structure
        from endplay.types import Deal, Denom, Player
        from endplay.dds import calc_dd_table
    except ImportError:
        logger.error("Endplay library not found. Solver disabled.")
        Deal = Denom = Player = None
        calc_dd_table = None

@dataclass
class DDMetrics:
    makeable_contracts: Dict[str, Dict[str, int]]

    def get_tricks(self, player: str, suit: str) -> int:
        return self.makeable_contracts.get(player, {}).get(suit, 0)

class DDSolver:

    @staticmethod
    def _hands_to_pbn(hands: Dict[str, Dict[str, List[str]]]) -> str:
        """Helper: Converts Dict hands to PBN string."""
        order = ['N', 'E', 'S', 'W'] 
        pbn_parts = []
        
        for seat in order:
            # Handle varied key formats (N vs North)
            hand_data = hands.get(seat) or hands.get(seat[0]) or {}
            
            def clean_suit(suit_key):
                cards = hand_data.get(suit_key, [])
                if isinstance(cards, list): return "".join(cards)
                return str(cards).replace(" ", "")

            s = clean_suit('S').replace("10", "T")
            h = clean_suit('H').replace("10", "T")
            d = clean_suit('D').replace("10", "T")
            c = clean_suit('C').replace("10", "T")
            pbn_parts.append(f"{s}.{h}.{d}.{c}")
            
        return "N:" + " ".join(pbn_parts)

    @staticmethod
    def analyze(hands_data: Union[Dict, 'Deal']) -> Optional[DDMetrics]:
        """
        UNIVERSAL ENTRY POINT
        Accepts EITHER a Dictionary OR a Deal Object.
        """
        if not calc_dd_table:
            return None

        try:
            deal_obj = None

            # CASE A: It's already a Deal Object (Fixes your specific error)
            if Deal and isinstance(hands_data, Deal):
                deal_obj = hands_data

            # CASE B: It's a Dictionary (Standard path)
            elif isinstance(hands_data, dict):
                pbn_string = DDSolver._hands_to_pbn(hands_data)
                
                # Validation: Check deck size
                card_count = sum(1 for c in pbn_string if c in "AKQJT98765432")
                if card_count != 52:
                    logger.warning(f"Deck Error: Found {card_count} cards. Expected 52.")
                    return None
                    
                deal_obj = Deal(pbn_string)
            
            else:
                logger.error(f"Solver received unknown data type: {type(hands_data)}")
                return None

            # RUN SOLVER
            dd_table = calc_dd_table(deal_obj)
            
            # Format Output
            friendly_table = { 'N': {}, 'S': {}, 'E': {}, 'W': {} }
            for player_obj in Player:
                p_str = player_obj.name[0].upper()
                for denom_obj in Denom:
                    # Handle naming differences (notrump vs NT)
                    d_name = denom_obj.name
                    d_str = 'NT' if d_name == 'notrump' else d_name[0].upper()
                    
                    # Newer endplay versions allow [player, denom]
                    friendly_table[p_str][d_str] = dd_table[player_obj, denom_obj]

            return DDMetrics(makeable_contracts=friendly_table)

        except Exception as e:
            logger.error(f"DD Solver crashed: {e}")
            return None

    @staticmethod
    def format_for_ai(metrics: DDMetrics) -> str:
        if not metrics: return "Double Dummy Analysis: Unavailable."
        lines = ["Double Dummy Analysis (Optimal Play):"]
        for axis, p1, p2 in [("N/S", "N", "S"), ("E/W", "E", "W")]:
            best_tricks = 0
            best_contract = ""
            for s in ['NT', 'S', 'H', 'D', 'C']:
                t = max(metrics.get_tricks(p1, s), metrics.get_tricks(p2, s))
                if t > best_tricks:
                    best_tricks = t
                    best_contract = f"{t} in {s}"
                elif t == best_tricks:
                    best_contract += f", {s}"
            lines.append(f"- {axis} Ceiling: {best_contract}")
        return "\n".join(lines)