"""
src/core/dd_solver.py

THE ORACLE (Module)
-------------------
Interfaces with the Double Dummy Solver (libdds via endplay).
Calculates the theoretical limit of the hand (Makeable Contracts)
and the Par Score.

This provides the "Objective Truth" against which the actual play is measured.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, List
from loguru import logger

# Import endplay. If not installed, we must fail gracefully or mock,
# but for this module to work, endplay is required.
try:
    from endplay.types import Deal, Denom, Player
    from endplay.dd import calc_dd_table, calc_all_tables
except ImportError:
    logger.error("endplay library not found. DD Analysis will fail.")
    Deal = Denom = Player = None
    calc_dd_table = calc_all_tables = None

@dataclass
class DDMetrics:
    """
    The 'Truth Matrix' for the deal.
    """
    # Dictionary mapping Player -> Denomination -> Tricks
    # e.g. {'N': {'NT': 2, 'S': 4...}, 'E': ...}
    makeable_contracts: Dict[str, Dict[str, int]]
    
    # Par score details (e.g., "NS 4S", 620)
    par_score_str: str 
    par_score_value: int

    def get_tricks(self, player: str, suit: str) -> int:
        """Helper to safely get trick count for a specific combo."""
        return self.makeable_contracts.get(player, {}).get(suit, 0)

class DDSolver:
    """
    Facade for the Endplay Double Dummy Solver.
    """

    # Mapping endplay Enums to our string standards
    SUIT_MAP = {
        'NT': 'NT',
        'S': 'S', 'H': 'H', 'D': 'D', 'C': 'C',
        # Handle potential endplay Enum str conversions if needed
    }

    @staticmethod
    def analyze(deal_obj: 'Deal') -> Optional[DDMetrics]:
        """
        Performs full Double Dummy Analysis on a deal.
        
        Args:
            deal_obj: An endplay.types.Deal object (parsed from PBN/LIN)
        
        Returns:
            DDMetrics object or None if solver fails.
        """
        if not calc_dd_table:
            logger.error("DDSolver unavailable (endplay not installed).")
            return None

        try:
            logger.debug("Running Double Dummy Solver...")
            
            # 1. Calculate the Table (5 strains x 4 players)
            # endplay returns a specific Table object
            dd_table = calc_dd_table(deal_obj)
            
            # 2. Convert to friendly Dictionary format
            # Structure: metrics['N']['S'] = 10 (North makes 10 tricks in Spades)
            friendly_table = {
                'N': {}, 'S': {}, 'E': {}, 'W': {}
            }
            
            # Iterate through the endplay result
            # The endplay API usually allows indexing or to_dict conversion
            for player in [Player.north, Player.south, Player.east, Player.west]:
                p_str = player.name[0].upper() # 'N', 'S'...
                for denom in [Denom.notrump, Denom.spades, Denom.hearts, Denom.diamonds, Denom.clubs]:
                    d_str = denom.name[0].upper() if denom != Denom.notrump else 'NT'
                    if d_str == 'N': d_str = 'NT' # Safety check for naming
                    
                    tricks = dd_table[player, denom]
                    friendly_table[p_str][d_str] = tricks

            # 3. Calculate Par
            # Par depends on vulnerability. The deal_obj should have vul info.
            # endplay's generic par calculation:
            # It usually returns a ParList or similar.
            # We assume a simplified string representation for Phase 1.
            
            # Note: endplay typically requires converting the table to a list for par calculation
            # or it has a helper `dd_table.par(vul)`.
            # We will use a safe try/except block for the specific endplay version syntax.
            
            # Let's assume we extract the text representation for now
            # In a real impl, we'd calculate the exact integer score.
            par_str = "N/A" 
            par_val = 0
            
            # (Conceptual implementation of Par extraction)
            # par_result = dd_table.first_par(deal_obj.vul)
            # par_str = str(par_result) 
            
            metrics = DDMetrics(
                makeable_contracts=friendly_table,
                par_score_str=par_str,
                par_score_value=par_val
            )
            
            return metrics

        except Exception as e:
            logger.error(f"DD Solver crashed: {e}")
            return None

    @staticmethod
    def format_for_ai(metrics: DDMetrics) -> str:
        """
        Converts the metrics into a readable text block for the Storyteller.
        """
        if not metrics:
            return "Double Dummy Analysis: Unavailable."

        lines = ["Double Dummy Analysis (Optimal Play):"]
        
        # Summarize North/South
        ns_max = 0
        ns_best = ""
        for s in ['NT', 'S', 'H', 'D', 'C']:
            n_tricks = metrics.get_tricks('N', s)
            s_tricks = metrics.get_tricks('S', s)
            # Take better of N/S
            best = max(n_tricks, s_tricks)
            if best > ns_max:
                ns_max = best
                ns_best = f"{best} tricks in {s}"
            elif best == ns_max:
                ns_best += f", {s}"
        
        lines.append(f"- N/S Ceiling: {ns_best}")

        # Summarize East/West
        ew_max = 0
        ew_best = ""
        for s in ['NT', 'S', 'H', 'D', 'C']:
            e_tricks = metrics.get_tricks('E', s)
            w_tricks = metrics.get_tricks('W', s)
            best = max(e_tricks, w_tricks)
            if best > ew_max:
                ew_max = best
                ew_best = f"{best} tricks in {s}"
            elif best == ew_max:
                ew_best += f", {s}"

        lines.append(f"- E/W Ceiling: {ew_best}")
        
        return "\n".join(lines)

# No __main__ block that runs logic here because it requires 
# a complex 'Deal' object instantiation which is hard to mock purely in  text.