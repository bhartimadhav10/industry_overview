from flask import Flask, request, jsonify
import logging
import google.generativeai as genai
from flask_cors import CORS
import os
import re
from dotenv import load_dotenv  # Add this
from flask_cors import CORS, cross_origin

# Load environment variables from .env file

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
CORS(app)
# Configure Gemini API
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

def clean_text(text):
    """
    Clean and format the generated text to maintain numbered list structure with 1.) format
    """
    lines = text.split('\n')
    cleaned_lines = []
    current_point = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Match both "1)..." and "1.)..." patterns
        match = re.match(r'(\d+)[.)]\s*(.*)', line)
        if match:
            if current_point is not None:
                cleaned_lines.append(current_point)
            current_point = f"{match.group(1)}.) {match.group(2)}"
        else:
            if current_point is not None:
                current_point += " " + line
            else:
                current_point = f"1.) {line}"
    
    if current_point is not None:
        cleaned_lines.append(current_point)
    
    return '\n'.join(cleaned_lines)

def generate_section_gemini(prompt):
    """
    Generate text using Gemini with explicit numbering format
    """
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-thinking-exp-01-21')
        response = model.generate_content(
            f"{prompt} Present each key point as a numbered list starting with \n1.), "
            "with each point on a new line. Use exactly this format: '1.) Point one' "
            "followed by '\n2.) Point two', etc. Never use markdown.",
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 1000,
            }
        )
        return clean_text(response.text)
    except Exception as e:
        logging.error(f"Error calling Gemini API: {e}")
        return "Error generating text."

@app.route('/generate_report', methods=['POST'])
@cross_origin()
def generate_report():
    """
    Generate report with exact JSON format including spaces in keys and numbered points
    """
    try:
        data = request.get_json(force=True)
    except Exception as e:
        logging.error(f"Error parsing JSON: {e}")
        return jsonify({"error": "Invalid JSON payload"}), 401

    if not data or "query" not in data:
        return jsonify({"error": "Please provide the startup query in the 'query' field."}), 400

    startup_idea = data["query"]
    logging.info(f"Processing query: {startup_idea}")

    sections = {
        "executive summary": f"Provide a concise executive summary for '{startup_idea}' with 5 key points in numbered format with '\n' after every point",
        "industry overview": f"Analyze the industry for '{startup_idea}' with 5 numbered key insights with '\n' after every point ",
        "target market analysis": f"Describe target market for '{startup_idea}' with 5 numbered demographic and psychographic points with '\n' after every point",
        "competitor analysis": f"List 5 key competitor insights for '{startup_idea}' in numbered format with '\n' after every point",
        "market pricing": f"Outline 5 pricing strategy points for '{startup_idea}' as numbered list with '\n' after every point",
        "swot analysis": f"Present SWOT analysis for '{startup_idea}' as 4 numbered points (one for each category) with '\n' after every point ",
        "trends": f"List 5 emerging trends relevant to '{startup_idea}' as numbered points with '\n' after every point",
        "regulatory": f"Describe 3 regulatory considerations for '{startup_idea}' as numbered points with '\n' after every point",
        "go to market": f"Outline 5 go-to-market strategies for '{startup_idea}' as numbered points with '\n' after every point",
        "financial projections": f"Provide 5 financial projections for '{startup_idea}' as numbered points with '\n' after every point "
    }

    report = {}
    for section, prompt_text in sections.items():
        generated = generate_section_gemini(prompt_text)
        report[section] = generated

    return jsonify(report)

@app.route('/', methods=['GET'])
def index():
    return "Startup Report Generator API - POST to /generate_report with JSON {'idea': 'your-idea'}"

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
