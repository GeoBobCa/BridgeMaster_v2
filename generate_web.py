"""
generate_web.py
"""
import os
import json
import re
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

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
        if not os.path.exists(self.in_dir): return

        files = [f for f in os.listdir(self.in_dir) if f.endswith(".json")]
        if not files: return

        hands_data = []
        for f in files:
            try:
                with open(os.path.join(self.in_dir, f), 'r', encoding='utf-8') as json_file:
                    data = json.load(json_file)
                    # Create the unique filename here
                    source = data['facts'].get('source_file', 'Unknown')
                    board_name = data['facts'].get('board', 'Board')
                    
                    # File Name: "Tournament_A_Board_1.html"
                    # We strip special chars to be safe
                    safe_source = re.sub(r'[^a-zA-Z0-9]', '_', source)
                    safe_board = re.sub(r'[^a-zA-Z0-9]', '_', board_name)
                    
                    data['page_filename'] = f"{safe_source}_{safe_board}.html"
                    hands_data.append(data)
            except Exception as e:
                print(f"Warning processing {f}: {e}")
        
        # Sort by Source File then Board Number
        def get_sort_key(item):
            s = item['facts'].get('source_file', '')
            b = item['facts'].get('board', '0')
            nums = re.findall(r'\d+', b)
            n = int(nums[0]) if nums else 0
            return (s, n)

        hands_data.sort(key=get_sort_key)
        
        self._render("index.html", "index.html", hands=hands_data)
        
        for hand in hands_data:
            self._render("hand_detail.html", hand['page_filename'], hand=hand)
            
        print(f"✅ Website generated in: {self.out_dir}")

    def _render(self, tpl, out, **kwargs):
        template = self.env.get_template(tpl)
        content = template.render(**kwargs)
        with open(os.path.join(self.out_dir, out), 'w', encoding='utf-8') as f:
            f.write(content)

    def _create_templates(self):
        # 1. INDEX
        index_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8"><title>Bridge Session</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        </head>
        <body class="bg-light"><div class="container py-5">
        <h1 class="mb-4">Bridge Session Results</h1>
        <div class="row">
        {% for item in hands %}
        <div class="col-md-3 mb-3">
            <div class="card shadow-sm h-100">
                <div class="card-header text-muted small text-truncate">
                    {{ item.facts.source_file }}
                </div>
                <div class="card-body text-center">
                    <h5 class="card-title">{{ item.facts.board }}</h5>
                    <span class="badge bg-primary mb-3">{{ item.ai_analysis.get('verdict', 'Pending') }}</span>
                    <p class="card-text fw-bold">{{ item.facts.result_display }}</p>
                    <a href="{{ item.page_filename }}" class="btn btn-outline-dark btn-sm w-100">View Analysis</a>
                </div>
            </div>
        </div>
        {% endfor %}
        </div></div></body></html>
        """
        
        # 2. DETAIL
        detail_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8"><title>{{ hand.facts.board }}</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
            <style>
                .hand-box { background: #fdfdfd; border: 1px solid #ccc; padding: 10px; border-radius: 5px; font-size: 0.9rem; }
                .suit-symbol { display: inline-block; width: 15px; text-align: center; font-weight: bold; }
                .suit-S { color: black; } .suit-H { color: red; } .suit-D { color: orange; } .suit-C { color: green; }
                .dealer-badge { background-color: #000; color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 0.7em; margin-left: 5px; }
                .dds-make { background-color: #d4edda; color: #155724; font-weight: bold; }
            </style>
        </head>
        <body class="bg-white"><div class="container py-4">
            <div class="d-flex justify-content-between mb-4">
                <a href="index.html" class="btn btn-outline-secondary">&larr; Back</a>
                <div>
                    <h2 class="m-0 d-inline">{{ hand.facts.board }}</h2>
                    <span class="text-muted ms-2 fs-5">({{ hand.facts.source_file }})</span>
                </div>
                <a href="{{ hand.facts.handviewer_url }}" target="_blank" class="btn btn-danger">Replay</a>
            </div>
            
            <div class="row mb-5">
                <div class="col-md-8">
                    <div class="card bg-success bg-opacity-10 border-success h-100">
                        <div class="card-body position-relative" style="min-height: 400px;">
                            <div class="position-absolute top-50 start-50 translate-middle text-center bg-white p-3 border rounded shadow-sm" style="z-index: 2;">
                                <strong>{{ hand.facts.board }}</strong><br>
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
                     </div>
                     
                     <div class="card border-info">
                        <div class="card-header bg-info text-white">Double Dummy</div>
                        <div class="card-body p-0">
                            {% if hand.dds %}
                            <table class="table table-sm table-bordered mb-0 text-center">
                                <thead class="table-light"><tr><th></th><th>NT</th><th>S</th><th>H</th><th>D</th><th>C</th></tr></thead>
                                <tbody>
                                    {% for seat in ['N', 'S', 'E', 'W'] %}
                                    <tr>
                                        <td><strong>{{ seat }}</strong></td>
                                        {% for strain in ['NT', 'S', 'H', 'D', 'C'] %}
                                            {% set lookup_key = 'N' if strain == 'NT' else strain %}
                                            {% set tricks = hand.dds[seat].get(lookup_key, '-') %}
                                            <td class="{{ 'dds-make' if tricks != '-' and ((strain=='NT' and tricks>=9) or ((strain=='H' or strain=='S') and tricks>=10) or tricks>=11) else '' }}">{{ tricks }}</td>
                                        {% endfor %}
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                            {% endif %}
                        </div>
                    </div>
                </div>
            </div>

            <h4 class="section-header">🔍 1. Critique</h4>
            <div class="mb-5">
                {% if hand.ai_analysis.actual_critique %}
                <ul class="list-group">{% for p in hand.ai_analysis.actual_critique %}<li class="list-group-item border-0">🔹 {{ p }}</li>{% endfor %}</ul>
                {% endif %}
            </div>
            
            <h4 class="section-header">📘 2. Fundamentals</h4>
            <div class="card mb-5 border-primary"><div class="card-body">
                <p class="lead">{{ hand.ai_analysis.basic_section.analysis }}</p>
            </div></div>

            <h4 class="section-header">🎓 3. Coach's Corner</h4>
            <div class="row">
                {% if hand.ai_analysis.coaches_corner %}
                    {% for item in hand.ai_analysis.coaches_corner %}
                    <div class="col-md-6 mb-3"><div class="card bg-light h-100"><div class="card-body">
                        <small class="text-uppercase text-muted">{{ item.player }} | {{ item.category }}</small>
                        <h5 class="card-title">{{ item.topic }}</h5>
                    </div></div></div>
                    {% endfor %}
                {% endif %}
            </div>

        </div></body></html>
        """
        
        with open(os.path.join(self.tpl_dir, "index.html"), 'w', encoding='utf-8') as f:
            f.write(index_html)
        with open(os.path.join(self.tpl_dir, "hand_detail.html"), 'w', encoding='utf-8') as f:
            f.write(detail_html)

if __name__ == "__main__":
    WebGenerator().generate_all()