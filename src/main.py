"""
src/main.py
"""
import sys
import os
import json
import glob
import re
from pathlib import Path
from loguru import logger

# Import your modules
from src.parsers.lin_parser import LinParser
from src.core.referee import Referee
from src.core.dd_solver import DDSolver
from src.core.storyteller import Storyteller
from src.core.contract_solver import ContractSolver
from src.core.hand_viewer import HandViewer

logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")

OUTPUT_DIR = "data/session_results"

def clean_board_name(raw_id):
    """
    Converts 'o1' -> 'Board 1', '14' -> 'Board 14'.
    Keeps custom names like 'SemiFinals' intact.
    """
    # Remove 'o' (Open) or 'c' (Closed) prefix if followed by a number
    if re.match(r'^[oc]\d+$', raw_id):
        number = raw_id[1:]
        return f"Board {number}"
    
    # If it's just a raw number, add "Board "
    if raw_id.isdigit():
        return f"Board {raw_id}"
        
    return raw_id

def calculate_hcp(hand_dict):
    hcp = 0
    values = {'A': 4, 'K': 3, 'Q': 2, 'J': 1}
    for suit in hand_dict.values():
        for card in suit:
            if card and card[0].upper() in values:
                hcp += values[card[0].upper()]
    return hcp

def enrich_hand_data(game):
    compass_map = {'N': 'North', 'S': 'South', 'E': 'East', 'W': 'West'}
    enriched = {}
    for short_seat, full_seat in compass_map.items():
        raw_hand = game.hands.get(short_seat, {})
        hcp = calculate_hcp(raw_hand)
        cards_formatted = {s: "".join(raw_hand.get(s, [])) for s in ['S', 'H', 'D', 'C']}
        p_name = game.player_names.get(short_seat, "Unknown")
        enriched[full_seat] = {"name": p_name, "stats": {"hcp": hcp, "cards": cards_formatted}}
    return enriched

def format_result_display(contract, tricks_taken):
    if not contract or contract == "PASS": return "Pass"
    try:
        level = int(contract[0])
        target = level + 6
        diff = tricks_taken - target
        if diff > 0: return f"{contract} +{diff}"
        elif diff == 0: return f"{contract} ="
        else: return f"{contract} {diff}"
    except:
        return contract

def process_file(file_path: str):
    logger.info(f"Processing file: {file_path}")
    
    # Get the file name (e.g. "Tournament_A" from "data/Tournament_A.lin")
    file_stem = Path(file_path).stem
    
    parser = LinParser()
    referee = Referee()
    storyteller = Storyteller()
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    games = parser.parse_file(file_path)
    logger.info(f"Found {len(games)} boards in {file_stem}.")

    for i, game in enumerate(games):
        # 1. CLEAN THE NAME
        display_name = clean_board_name(game.board_id)

        # 2. ANALYSIS
        dealer_metrics = referee.analyze_dealer_opening(game.dealer, game.hands[game.dealer], game.vulnerability)
        
        responder_metrics = None
        if len(game.auction) > 0 and dealer_metrics.suggested_opening != 'PASS':
            r_seat = 'N' if game.dealer == 'S' else 'E'
            responder_metrics = referee.analyze_response(r_seat, game.hands.get(r_seat,{}), dealer_metrics.suggested_opening, game.auction)

        dd_metrics = DDSolver.analyze(game.hands)
        dd_summary = DDSolver.format_for_ai(dd_metrics)
        dd_json = dd_metrics.makeable_contracts if dd_metrics else {}

        contract, declarer, dbl = ContractSolver.get_contract(game.dealer, game.auction)
        tricks = game.claimed_tricks if game.claimed_tricks is not None else 0
        
        # 3. AI GENERATION
        # Pass the "Display Name" to the AI so it says "In Board 1..." instead of "In o1..."
        hv_url = HandViewer.generate_url(game)
        ai_data = storyteller.generate_commentary(display_name, dealer_metrics, responder_metrics, dd_summary)

        # 4. SAVE JSON
        full_dealer = {'N':'North', 'S':'South', 'E':'East', 'W':'West'}.get(game.dealer, game.dealer)
        full_declarer = {'N':'North', 'S':'South', 'E':'East', 'W':'West'}.get(declarer, declarer)
        result_str = format_result_display(contract, tricks)

        full_record = {
            "facts": {
                "board": display_name,     # Now "Board 1"
                "board_raw": game.board_id, # Keep "o1" just in case
                "source_file": file_stem,  # "Tournament_A"
                "dealer": full_dealer,
                "vulnerability": game.vulnerability,
                "hands": enrich_hand_data(game),
                "auction": game.auction,
                "contract": contract,
                "declarer": declarer,
                "declarer_full": full_declarer,
                "tricks_taken": tricks,
                "result_display": result_str,
                "doubled": dbl,
                "handviewer_url": hv_url
            },
            "dds": dd_json,
            "ai_analysis": ai_data
        }
        
        # Unique Filename: board_{FILE}_{BOARDID}.json
        # This ensures collisions are impossible if you have 16 files of "Board 1"
        filename = f"board_{file_stem}_{game.board_id}.json"
        
        with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
            json.dump(full_record, f, indent=2)

def main():
    if len(sys.argv) < 2:
        print("Usage: python src/main.py <file_or_directory>")
        sys.exit(1)
        
    input_path = sys.argv[1]
    
    if os.path.isdir(input_path):
        print(f"📂 Batch Mode: Scanning {input_path}...")
        lin_files = glob.glob(os.path.join(input_path, "*.lin"))
        if not lin_files:
            print("No .lin files found!")
            return
            
        print(f"Found {len(lin_files)} files to process.")
        for f in lin_files:
            try:
                process_file(f)
            except Exception as e:
                logger.error(f"Failed to process {f}: {e}")
    else:
        process_file(input_path)

if __name__ == "__main__":
    main()