"""
src/core/storyteller.py

THE NARRATOR (Updated for Google GenAI SDK v1.0)
------------------------------------------------
Uses the modern 'google-genai' library.
"""

import os
import json
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv
from google import genai
from google.genai import types

# 1. ROBUST ENV LOADING
# Explicitly find the .env file in the project root (2 levels up from this file)
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
env_path = project_root / ".env"

if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    # Fallback: try loading from current working directory
    load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")

class Storyteller:
    def __init__(self):
        if API_KEY:
            # New Client Initialization
            self.client = genai.Client(api_key=API_KEY)
        else:
            self.client = None
            logger.warning(f"Google API Key not found. Checked path: {env_path}")

    def generate_commentary(self, board_id, dealer_metrics, responder_metrics, dd_summary):
        """
        Orchestrates the AI call using the new SDK.
        """
        if not self.client:
            return self._get_placeholder()

        # 1. CONSTRUCT PROMPT
        prompt = f"""
        You are an expert Bridge Teacher. Explain this hand to a student.
        
        --- FACTS ---
        Board: {board_id}
        Dealer Suggestion: {dealer_metrics.suggested_opening} ({dealer_metrics.rule_explanation})
        Hand Stats: {dealer_metrics.hcp} HCP, Dist: {dealer_metrics.distribution}
        Responder Suggestion: {responder_metrics.suggested_response if responder_metrics else "N/A"}
        
        Double Dummy Analysis:
        {dd_summary}
        
        --- TASK ---
        Return valid JSON only. Structure:
        {{
            "verdict": "Short summary phrase",
            "actual_critique": ["Bullet 1", "Bullet 2"],
            "basic_section": {{
                "analysis": "Explanation for beginners.",
                "recommended_auction": [
                    {{ "bid": "1S", "explanation": "Shows 5+ Spades" }}
                ]
            }},
            "advanced_section": {{ "analysis": "Deeper analysis.", "sequence": [] }},
            "coaches_corner": [
                {{ "player": "North", "category": "Tip", "topic": "Advice" }}
            ]
        }}
        """

        try:
            # 2. CALL GEMINI (New Syntax)
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",  # Or "gemini-1.5-flash"
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            # 3. PARSE JSON
            # The new SDK handles JSON cleaning better if mime_type is set
            return json.loads(response.text)

        except Exception as e:
            logger.error(f"AI Generation failed: {e}")
            return self._get_placeholder()

    def _get_placeholder(self):
        return {
            "verdict": "Analysis Unavailable",
            "actual_critique": ["AI connection failed.", "Check API Key."],
            "basic_section": {"analysis": "N/A", "recommended_auction": []},
            "advanced_section": {"analysis": "N/A", "sequence": []},
            "coaches_corner": []
        }
    