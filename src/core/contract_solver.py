"""
src/core/contract_solver.py

HISTORY ANALYST
---------------
Determines the final contract, declarer, and result from the auction/play logs.
"""

from typing import List, Tuple

class ContractSolver:
    # Order of suits for determination (Clubs to NoTrump)
    SUITS = ['C', 'D', 'H', 'S', 'N'] 
    PLAYERS = ['S', 'W', 'N', 'E'] # Standard LIN order

    @staticmethod
    def get_contract(dealer: str, auction: List[str]) -> Tuple[str, str, str]:
        """
        Analyzes the auction to find the Final Contract.
        Returns: (contract_string, declarer_seat, doubled_status)
        Example: ("4S", "N", "") or ("3NT", "S", "X")
        """
        # If no auction or passed out
        if not auction or auction == ['p'] * 4:
            return ("PASS", "", "")

        # 1. Simulate the Auction to track Declarer
        # Track who bid each suit first for each partnership
        # map: {'NS': {'C': None...}, 'EW': {'C': None...}}
        first_bidder = {
            'NS': {s: None for s in ContractSolver.SUITS},
            'EW': {s: None for s in ContractSolver.SUITS}
        }

        # Normalize Dealer to index (S=0, W=1, N=2, E=3)
        # Note: Adjust if your LIN parser uses different mapping
        player_map = {'S': 0, 'W': 1, 'N': 2, 'E': 3}
        current_idx = player_map.get(dealer, 0)
        
        last_bid = None
        last_bidder_idx = -1
        doubled = ""

        for call in auction:
            c = call.lower()
            if c in ['p', 'pass']:
                pass
            elif c == 'd':
                doubled = "X"
            elif c == 'r':
                doubled = "XX"
            else:
                # Real Bid (e.g. '1s', '3n')
                doubled = ""
                last_bid = c
                last_bidder_idx = current_idx
                
                # Extract suit/strain
                suit_char = c[-1].upper()
                if suit_char == 'T': suit_char = 'N' # Handle 1NT vs 1N
                
                # Identify partnership
                player_name = ContractSolver.PLAYERS[current_idx]
                partnership = 'NS' if player_name in ['N', 'S'] else 'EW'
                
                # If this is the first time this side bid this suit, record it
                if first_bidder[partnership].get(suit_char) is None:
                    first_bidder[partnership][suit_char] = player_name

            # Rotate to next player
            current_idx = (current_idx + 1) % 4

        if not last_bid:
            return ("PASS", "", "")

        # 2. Determine Declarer
        final_suit = last_bid[-1].upper()
        if final_suit == 'T': final_suit = 'N'
        
        winning_player = ContractSolver.PLAYERS[last_bidder_idx]
        winning_partnership = 'NS' if winning_player in ['N', 'S'] else 'EW'
        
        # The declarer is whoever mentioned the suit first for that partnership
        declarer = first_bidder[winning_partnership][final_suit]
        
        # Format Contract (e.g., "1n" -> "1NT")
        contract_display = last_bid.upper()
        if contract_display.endswith("N"): contract_display += "T"
        
        return (contract_display, declarer, doubled)