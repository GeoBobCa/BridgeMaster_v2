"""
generate_web.py

THE PUBLISHER (Fixed for DD Table Lookup)
-----------------------------------------
"""

import os
import json
import re
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

# --- CONFIGURATION ---
BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "data/session_results"
OUTPUT_DIR = BASE_DIR / "docs"
TEMPLATE_DIR = BASE_DIR / "src/templates"

class WebGenerator:
    def __init__(self):
        self.in_dir = str(INPUT_DIR)
        self.out_dir = str(OUTPUT_DIR)
        self.tpl_dir = str(TEMPLATE_DIR)
        
        os.makedirs(self.out_dir, exist_ok=True)
        os.makedirs(self.tpl_dir, exist_ok=True)
        
        self.env = Environment(loader=FileSystemLoader(self.tpl_dir))
        self._create_templates()

    def generate_all(self):
        print(f"📂 Scanning for JSON in: {self.in_dir}")
        if not os.path.exists(self.in_dir):
            print("❌ Input directory not found. Did you run the analyzer?")
            return

        files = [f for f in os.listdir(self.in_dir) if f.endswith(".json")]
        if not files:
            print("⚠️  No JSON files found!")
            return

        hands_data = []
        for f in files:
            try:
                with open(os.path.join(self.in_dir, f), 'r', encoding='utf-8') as json_file:
                    hands_data.append(json.load(json_file))
            except Exception as e:
                print(f"Warning processing {f}: {e}")
        
        def get_board_num(item):
            board_str = item.get('facts', {}).get('board', '0')
            nums = re.findall(r'\d+', board_str)
            return int(nums[0]) if nums else 0

        hands_data.sort(key=get_board_num)
        
        self._render("index.html", "index.html", hands=hands_data)
        
        for hand in hands_data:
            facts = hand.get('facts', {})
            page_title = facts.get('board', 'Board_Unknown')
            safe_filename = page_title.replace(' ', '_') + ".html"
            hand['handviewer_url'] = facts.get('handviewer_url', '#')
            
            self._render("hand_detail.html", safe_filename, hand=hand, title=page_title)
            
        print(f"✅ Website generated in: {self.out_dir}")
        print(f"   Open {self.out_dir}\\index.html to view.")

    def _render(self, tpl, out, **kwargs):
        template = self.env.get_template(tpl)
        content = template.render(**kwargs)
        with open(os.path.join(self.out_dir, out), 'w', encoding='utf-8') as f:
            f.write(content)

    def _create_templates(self):
        # 1. INDEX TEMPLATE (Unchanged)
        index_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8"><title>Bridge Session</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        </head>
        <body class="bg-light"><div class="container py-5"><h1 class="mb-4">Bridge Session</h1><div class="row">
        {% for item in hands %}
        <div class="col-md-3 mb-3"><div class="card shadow-sm h-100"><div class="card-body text-center">
            <h5 class="card-title">{{ item.facts.board }}</h5>
            <span class="badge bg-primary mb-3">{{ item.ai_analysis.get('verdict', 'Pending') }}</span>
            <p class="card-text fw-bold">{{ item.facts.result_display }}</p>
            <p class="card-text small text-muted">by {{ item.facts.declarer_full }}</p>
            <a href="{{ item.facts.board | replace(' ', '_') }}.html" class="btn btn-outline-dark btn-sm w-100">View</a>
        </div></div></div>
        {% endfor %}
        </div></div></body></html>
        """
        
        # 2. DETAIL TEMPLATE (Fixed DD Table Logic)
        detail_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8"><title>{{ title }}</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
            <style>
                .hand-box { background: #fdfdfd; border: 1px solid #ccc; padding: 10px; border-radius: 5px; font-size: 0.9rem; }
                .suit-symbol { display: inline-block; width: 15px; text-align: center; font-weight: bold; }
                .suit-S { color: black; } .suit-H { color: red; } .suit-D { color: orange; } .suit-C { color: green; }
                .dealer-badge { background-color: #000; color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 0.7em; margin-left: 5px; }
                .dir-badge { width: 35px; text-align: center; display: inline-block; margin-right: 10px; font-weight: bold; background-color: #6c757d; color: white; border-radius: 4px; padding: 2px 0; }
                .coach-card { background-color: #f8f9fa; border-left: 5px solid #0dcaf0; }
                .adv-card { background-color: #fff3cd; border-left: 5px solid #ffc107; }
                .dds-table th, .dds-table td { text-align: center; padding: 4px; font-family: monospace; }
                .dds-make { background-color: #d4edda; color: #155724; font-weight: bold; }
                .auction-table th { text-align: center; background-color: #f8f9fa; color: #666; font-size: 0.85rem; }
                .auction-table td { text-align: center; font-family: monospace; font-size: 1.1rem; height: 40px; }
            </style>
        </head>
        <body class="bg-white"><div class="container py-4">
            <div class="d-flex justify-content-between mb-4">
                <a href="index.html" class="btn btn-outline-secondary">&larr; Back</a>
                <h2 class="m-0">{{ title }} <span class="badge bg-primary fs-6 align-middle ms-2">{{ hand.ai_analysis.get('verdict', '') }}</span></h2>
                <a href="{{ hand.handviewer_url }}" target="_blank" class="btn btn-danger">Replay</a>
            </div>

            <div class="row mb-5">
                <div class="col-md-8">
                    <div class="card bg-success bg-opacity-10 border-success h-100">
                        <div class="card-body position-relative" style="min-height: 400px;">
                            <div class="position-absolute top-50 start-50 translate-middle text-center bg-white p-3 border rounded shadow-sm" style="z-index: 2;">
                                <strong>{{ title }}</strong><br>
                                Dlr: {{ hand.facts.dealer }} | Vul: {{ hand.facts.vulnerability }}
                            </div>
                            {% for seat in ['North', 'West', 'East', 'South'] %}
                            {% set pos = 'top-0 start-50 translate-middle-x mt-2 w-50' if seat == 'North' else 'bottom-0 start-50 translate-middle-x mb-2 w-50' if seat == 'South' else 'top-50 start-0 translate-middle-y ms-2 w-25' if seat == 'West' else 'top-50 end-0 translate-middle-y me-2 w-25' %}
                            <div class="position-absolute {{ pos }}">
                                <div class="hand-box shadow-sm">
                                    <strong>{{ seat }}</strong> ({{ hand.facts.hands[seat].name }})
                                    {% if hand.facts.dealer == seat %}<span class="dealer-badge">DLR</span>{% endif %}
                                    <div class="float-end fw-bold">{{ hand.facts.hands[seat].stats.hcp }} HCP</div>
                                    <hr class="my-1">
                                    {% for s in ['S','H','D','C'] %}<div><span class="suit-symbol suit-{{ s }}">{{ {"S":"♠","H":"♥","D":"♦","C":"♣"}[s] }}</span> {{ hand.facts.hands[seat].stats.cards[s] }}</div>{% endfor %}
                                </div>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                </div>

                <div class="col-md-4">
                    <div class="card mb-3">
                        <div class="card-header text-center">
                            <span class="fs-5 fw-bold">{{ hand.facts.result_display }}</span><br>
                            <span class="text-muted small">by {{ hand.facts.declarer_full }}</span>
                        </div>
                        <div class="card-body p-0">
                            <table class="table table-bordered mb-0 auction-table">
                                <thead><tr><th>WEST</th><th>NORTH</th><th>EAST</th><th>SOUTH</th></tr></thead>
                                <tbody>
                                    <tr>
                                    {% set offset = {'West':0, 'North':1, 'East':2, 'South':3}[hand.facts.dealer] %}
                                    {% for i in range(offset) %}<td></td>{% endfor %}
                                    {% for bid in hand.facts.auction %}
                                        {% if loop.index0 > 0 and (loop.index0 + offset) % 4 == 0 %}</tr><tr>{% endif %}
                                        <td>{{ bid }}</td>
                                    {% endfor %}
                                    {% set total = offset + hand.facts.auction|length %}
                                    {% set rem = 4 - (total % 4) %}
                                    {% if rem != 4 %}{% for i in range(rem) %}<td></td>{% endfor %}{% endif %}
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <div class="card border-info">
                        <div class="card-header bg-info text-white">Double Dummy Analysis</div>
                        <div class="card-body p-0">
                            {% if hand.dds %}
                            <table class="table table-sm table-bordered mb-0 dds-table">
                                <thead class="table-light"><tr><th></th><th>NT</th><th><span class="suit-S">♠</span></th><th><span class="suit-H">♥</span></th><th><span class="suit-D">♦</span></th><th><span class="suit-C">♣</span></th></tr></thead>
                                <tbody>
                                    {% for seat in ['N', 'S', 'E', 'W'] %}
                                    <tr>
                                        <td><strong>{{ seat }}</strong></td>
                                        {% for strain in ['NT', 'S', 'H', 'D', 'C'] %}
                                            {# KEY FIX: Check for 'NT' then fall back to 'N' #}
                                            {% set lookup_key = 'N' if strain == 'NT' else strain %}
                                            {% set tricks = hand.dds[seat].get(lookup_key, '-') %}
                                            
                                            {% set is_make = false %}
                                            {% if tricks != '-' %}
                                                {% set is_make = (strain=='NT' and tricks>=9) or ((strain=='H' or strain=='S') and tricks>=10) or ((strain=='C' or strain=='D') and tricks>=11) %}
                                            {% endif %}
                                            
                                            <td class="{{ 'dds-make' if is_make else '' }}">{{ tricks }}</td>
                                        {% endfor %}
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                            {% else %}<div class="p-3 text-muted text-center">Analysis unavailable</div>{% endif %}
                        </div>
                    </div>
                </div>
            </div>

            <h4 class="section-header">🔍 1. Critique</h4>
            <div class="mb-5">
                {% if hand.ai_analysis.actual_critique %}
                <ul class="list-group">{% for p in hand.ai_analysis.actual_critique %}<li class="list-group-item border-0">🔹 {{ p }}</li>{% endfor %}</ul>
                {% else %}<div class="alert alert-warning">Critique unavailable.</div>{% endif %}
            </div>
            
            <h4 class="section-header">📘 2. Fundamentals</h4>
            <div class="card mb-5 border-primary">
                <div class="card-body">
                    {% if hand.ai_analysis.basic_section %}
                    <p class="lead">{{ hand.ai_analysis.basic_section.analysis }}</p>
                    {% if hand.ai_analysis.basic_section.recommended_auction %}
                    <div class="accordion mt-3" id="accordionBasic">
                        {% set compass = ['North', 'East', 'South', 'West'] %}
                        {% set dealer_map = {'North': 0, 'East': 1, 'South': 2, 'West': 3} %}
                        {% set start_idx = dealer_map[hand.facts.dealer] %}
                        {% for step in hand.ai_analysis.basic_section.recommended_auction %}
                            {% set current_idx = (start_idx + loop.index0) % 4 %}
                            <div class="accordion-item">
                                <h2 class="accordion-header">
                                    <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#c{{ loop.index }}">
                                    <span class="dir-badge">{{ compass[current_idx][0] }}</span><strong>{{ step.bid }}</strong>
                                    </button>
                                </h2>
                                <div id="c{{ loop.index }}" class="accordion-collapse collapse" data-bs-parent="#accordionBasic">
                                    <div class="accordion-body">{{ step.explanation }}</div>
                                </div>
                            </div>
                        {% endfor %}
                    </div>
                    {% endif %}
                    {% endif %}
                </div>
            </div>

            <h4 class="section-header">🚀 3. Advanced Concepts</h4>
            <div class="card mb-5 adv-card">
                <div class="card-body">
                    {% if hand.ai_analysis.advanced_section %}
                        <p>{{ hand.ai_analysis.advanced_section.analysis }}</p>
                        {% if hand.ai_analysis.advanced_section.sequence %}
                        <div class="mt-4">
                            <h6>✨ Advanced Sequence:</h6>
                            <div class="accordion mt-3" id="accordionAdv">
                                {% set compass = ['North', 'East', 'South', 'West'] %}
                                {% set dealer_map = {'North': 0, 'East': 1, 'South': 2, 'West': 3} %}
                                {% set start_idx = dealer_map[hand.facts.dealer] %}
                                {% for step in hand.ai_analysis.advanced_section.sequence %}
                                    {% set current_idx = (start_idx + loop.index0) % 4 %}
                                    <div class="accordion-item">
                                        <h2 class="accordion-header">
                                            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#adv{{ loop.index }}">
                                                <span class="dir-badge" style="background-color: #ffc107; color: black;">{{ compass[current_idx][0] }}</span>
                                                <strong>{{ step.bid }}</strong>
                                            </button>
                                        </h2>
                                        <div id="adv{{ loop.index }}" class="accordion-collapse collapse" data-bs-parent="#accordionAdv">
                                            <div class="accordion-body text-muted">
                                                {{ step.explanation }}
                                            </div>
                                        </div>
                                    </div>
                                {% endfor %}
                            </div>
                        </div>
                        {% endif %}
                    {% else %}<p class="text-muted">Advanced analysis unavailable.</p>{% endif %}
                </div>
            </div>

            <h4 class="section-header">🎓 4. Coach's Corner</h4>
            <div class="row">
                {% if hand.ai_analysis.coaches_corner %}
                    {% for item in hand.ai_analysis.coaches_corner %}
                    <div class="col-md-6 mb-3"><div class="card coach-card h-100"><div class="card-body">
                        <small class="text-uppercase text-muted">{{ item.player }} | {{ item.category }}</small>
                        <h5 class="card-title">{{ item.topic }}</h5>
                    </div></div></div>
                    {% endfor %}
                {% else %}<div class="col-12"><p class="text-muted">No coaching tips generated.</p></div>{% endif %}
            </div>
        </div></body></html>
        """
        
        with open(os.path.join(self.tpl_dir, "index.html"), 'w', encoding='utf-8') as f:
            f.write(index_html)
        with open(os.path.join(self.tpl_dir, "hand_detail.html"), 'w', encoding='utf-8') as f:
            f.write(detail_html)

if __name__ == "__main__":
    WebGenerator().generate_all()