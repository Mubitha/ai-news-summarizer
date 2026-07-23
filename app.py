from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from groq import Groq
import re
import json
from langdetect import detect, DetectorFactory
import os

DetectorFactory.seed = 0

app = Flask(__name__)
CORS(app)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/summarize', methods=['POST'])
def summarize():
    data = request.get_json()
    
    # Payload இல்லையென்றால் கிராஷ் ஆகாமல் இருக்க safe check
    if not data or 'text' not in data:
        return jsonify({'error': 'No text field found in request body'}), 400

    article_text = data.get('text', '').strip()

    if not article_text:
        return jsonify({'error': 'No article text provided'}), 400

    if len(article_text) < 100:
        return jsonify({'error': 'Article too short. Please paste a longer news article.'}), 400

    try:
        # 2. Language Detection
        try:
            lang = detect(article_text)
        except Exception:
            lang = 'en'  # ஏதேனும் எர்ரர் வந்தால் Default-ஆக English எடுத்துக்கொள்ளும்

        # 3. Llama 3.3 Prompt Handover: கண்டறியப்பட்ட மொழியின் ISO குறியீட்டை நேரடியாக Prompt-ல் வழங்குகிறது
        lang_instruction = (
            f"IMPORTANT: The detected primary language code for this article is '{lang}'. "
            f"You MUST write ALL field values in language code '{lang}'. "
            "Do not translate JSON keys, ONLY write the string values in that language."
        )

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=1024,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content": f"""{lang_instruction}

Analyze this news article and return a structured JSON response with the following fields:
{{
  "headline": "A sharp, punchy 1-sentence headline (max 15 words)",
  "summary": "2-3 sentence plain-language summary of what happened",
  "key_points": ["point 1", "point 2", "point 3", "point 4"],
  "category": "one of: Politics, Technology, Business, Sports, Health, Science, World, Entertainment, Environment, Crime",
  "sentiment": "one of: Positive, Negative, Neutral",
  "reading_time": estimated reading time in seconds as integer,
  "importance": "one of: Breaking, High, Medium, Low",
  "who": "Main people/organizations involved",
  "what": "Core event in 10 words or less",
  "when": "Time context if mentioned",
  "where": "Location if mentioned",
  "why": "Reason/context in one sentence"
}}

Return ONLY the JSON.

Article:
{article_text}"""
                }
            ]
        )

        response_text = response.choices[0].message.content.strip()
        
    ு
        response_text = re.sub(r'^```json\s*', '', response_text)
        response_text = re.sub(r'\s*```$', '', response_text)

        result = json.loads(response_text)
        return jsonify({'success': True, 'detected_language': lang, 'data': result})

    except json.JSONDecodeError:
        return jsonify({'error': 'Failed to parse JSON response from LLM model'}), 500
    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
