"""
src/core/hand_viewer.py
Generates Bridge Base Online (BBO) HandViewer URLs.
"""

import urllib.parse
from typing import Dict, List

class HandViewer:
    BASE_URL = "http://www.bridgebase.com/tools/handviewer.html"

    @staticmethod
    def generate_url(game_obj) -> str:
        """
        Converts a BridgeGame object into a BBO Viewer URL.
        """
        params = {}
        
        # 1. Map Hands (N, S, E, W) -> (n, s, e, w)
        # Our data: {'N': {'S': ['A', 'K'], 'H': ['T', ...]}, ...}
        seat_map = {'N': 'n', 'S': 's', 'E': 'e', 'W': 'w'}
        
        for seat_code, bbo_key in seat_map.items():
            hand_dict = game_obj.hands.get(seat_code, {})
            
            # Helper to join list of cards ['A', 'K'] -> "AK"
            # BBO expects 'T' for 10, not '10'
            def get_suit(k):
                cards = hand_dict.get(k, [])
                return "".join(cards).replace("10", "T")

            s = get_suit('S')
            h = get_suit('H')
            d = get_suit('D')
            c = get_suit('C')
            
            # Format: s{spades}h{hearts}d{diams}c{clubs}
            params[bbo_key] = f"s{s}h{h}d{d}c{c}"

        # 2. Dealer
        # BBO codes: n, s, e, w
        dealer_map = {'N': 'n', 'S': 's', 'E': 'e', 'W': 'w'}
        params['d'] = dealer_map.get(game_obj.dealer, 'n')

        # 3. Vulnerability
        # BBO codes: n (none), b (both), e (ew), s (ns)
        vul_map = {'None': 'n', 'All': 'b', 'EW': 'e', 'NS': 's'}
        params['v'] = vul_map.get(game_obj.vulnerability, 'n')
        
        # 4. Board ID (Optional display)
        params['b'] = game_obj.board_id

        # 5. Auction (Optional - simple space-separated format usually works)
        if game_obj.auction:
             # Convert ['1N', 'p'] -> "1N-p" or similar
             params['a'] = "-".join(game_obj.auction).replace('Pass', 'p').replace('pass', 'p')

        query_string = urllib.parse.urlencode(params)
        return f"{HandViewer.BASE_URL}?{query_string}"