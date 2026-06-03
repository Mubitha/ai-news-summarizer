import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from groq import Groq
import re
import json
from langdetect import detect

app = Flask(__name__)
CORS(app)


client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/summarize', methods=['POST'])
def summarize():
    data = request.get_json()
    article_text = data.get('text', '').strip()

    if not article_text:
        return jsonify({'error': 'No article text provided'}), 400

    if len(article_text) < 100:
        return jsonify({'error': 'Article too short. Please paste a longer news article.'}), 400

    try:
        try:
            lang = detect(article_text)
        except:
            lang = 'en'

        lang_instruction = (
            "IMPORTANT: You MUST detect the language of the provided article and respond "
            "with ALL fields in that SAME language only. Every single value must be in the detected language. "
            "Do not translate JSON keys, only translate the values."
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
        
        response_text = re.sub(r'^```json\s*', '', response_text)
        response_text = re.sub(r'\s*```$', '', response_text)

        result = json.loads(response_text)
        return jsonify({'success': True, 'data': result})

    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

# 🌟 பிக்ஸ் 2: Render சர்வருக்கான போர்ட் (Port) செட்டிங்ஸ் மாற்றியாச்சு!
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
