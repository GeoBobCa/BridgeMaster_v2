"""
src/main.py

THE COORDINATOR
---------------
Entry point for BridgeMaster v2.0.
1. Reads input file (LIN).
2. Parses into BridgeGame objects.
3. Runs the 'Neuro-Symbolic' pipeline:
    - Hand Validation (Opener)
    - Response Validation (Responder)
    - Double Dummy Analysis (The Truth)
4. Outputs the Data Packet (which will eventually go to the AI).
"""

import sys
import argparse
from typing import Dict, List
from loguru import logger

# Project Imports
from src.parsers.lin_parser import LinParser, BridgeGame
from src.core.hand_validator import HandValidator
from src.core.response_validator import ResponseValidator
from src.core.dd_solver import DDSolver, DDMetrics

# Endplay Import (for data conversion)
try:
    from endplay.types import Deal, Denom, Player, Vul
except ImportError:
    logger.warning("endplay not installed. DD Analysis will be skipped.")
    Deal = None

class BridgeMasterEngine:
    
    @staticmethod
    def _convert_to_endplay_deal(game: BridgeGame) -> 'Deal':
        """
        Hydrates a simple BridgeGame dict into a complex endplay.Deal object.
        Required for the DD Solver.
        """
        if not Deal:
            return None

        # 1. PBN String Construction (Easiest way to load into endplay)
        # Format: N:DAT.K43.Q7543.87 KQ72.J65.AJ.KQ62 ...
        # We need to reconstruct the PBN string from our hands dict.
        
        pbn_parts = []
        # Endplay PBN usually expects North first
        for seat in ['N', 'E', 'S', 'W']:
            hand_dict = game.hands.get(seat, {})
            # Suits order: S, H, D, C
            s = "".join(hand_dict.get('S', []))
            h = "".join(hand_dict.get('H', []))
            d = "".join(hand_dict.get('D', []))
            c = "".join(hand_dict.get('C', []))
            pbn_parts.append(f"{s}.{h}.{d}.{c}")
        
        pbn_str = "N:" + " ".join(pbn_parts)
        
        try:
            deal = Deal(pbn_str)
            
            # Set Vulnerability
            # game.vulnerability is 'None', 'NS', 'EW', 'All'
            vul_map = {
                'None': Vul.none, 'NS': Vul.ns, 
                'EW': Vul.ew, 'All': Vul.both
            }
            deal.vul = vul_map.get(game.vulnerability, Vul.none)
            
            # Set Dealer (optional for DD, but good for completeness)
            # deal.dealer = ...
            
            return deal
        except Exception as e:
            logger.error(f"Failed to convert hand to endplay object: {e}")
            return None

    def process_file(self, file_path: str):
        logger.info(f"Processing file: {file_path}")
        
        # 1. PARSE
        games = LinParser.parse_file(file_path)
        logger.info(f"Found {len(games)} boards.")

        for i, game in enumerate(games):
            logger.info(f"\n--- BOARD {game.board_id} ---")
            
            # 2. VALIDATE OPENER (Dealer)
            dealer_seat = game.dealer
            dealer_hand = game.hands.get(dealer_seat)
            
            logger.info(f"Analyzing Dealer ({dealer_seat})...")
            opener_metrics = HandValidator.analyze(dealer_hand)
            logger.info(f"Dealer Suggestion: {opener_metrics.suggested_opening}")
            logger.info(f"Reason: {opener_metrics.rule_explanation}")
            
            # 3. VALIDATE RESPONDER (If Dealer opened)
            # Identify responder seat (Left of Dealer? No, Partner of Dealer)
            seats = ['N', 'E', 'S', 'W']
            d_idx = seats.index(dealer_seat)
            partner_idx = (d_idx + 2) % 4
            responder_seat = seats[partner_idx]
            responder_hand = game.hands.get(responder_seat)
            
            if opener_metrics.suggested_opening != "PASS":
                logger.info(f"Analyzing Responder ({responder_seat}) against {opener_metrics.suggested_opening}...")
                resp_metrics = ResponseValidator.analyze(
                    responder_hand, 
                    opener_metrics.suggested_opening
                )
                logger.info(f"Responder Suggestion: {resp_metrics.suggested_response}")
                logger.info(f"Convention: {resp_metrics.convention}")
            else:
                logger.info("Dealer passed. Skipping response analysis.")

            # 4. SOLVE (Double Dummy)
            logger.info("Running Double Dummy Analysis...")
            endplay_deal = self._convert_to_endplay_deal(game)
            if endplay_deal:
                dd_metrics = DDSolver.analyze(endplay_deal)
                summary = DDSolver.format_for_ai(dd_metrics)
                print(f"\n[TRUTH MATRIX]\n{summary}\n")
            else:
                logger.warning("Skipping DD Analysis (Conversion Failed or Lib Missing)")

def main():
    parser = argparse.ArgumentParser(description="BridgeMaster v2.0 - Core Pipeline")
    parser.add_argument("file", help="Path to LIN or PBN file")
    args = parser.parse_args()

    engine = BridgeMasterEngine()
    engine.process_file(args.file)

if __name__ == "__main__":
    # Configure logger to be concise
    logger.remove()
    logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    main()