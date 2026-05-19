#!/usr/bin/env python3
import json
import os
import sys
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from anthropic import Anthropic

client = Anthropic()

def fetch_url(url: str) -> str:
    """Fetch URL and return HTML content."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = response.apparent_encoding or 'utf-8'
        return response.text
    except Exception as e:
        return f"Error fetching URL: {str(e)}"

def extract_text_from_html(html: str, max_chars: int = 8000) -> str:
    """Extract meaningful text from HTML."""
    soup = BeautifulSoup(html, 'html.parser')

    # Remove script and style elements
    for script in soup(["script", "style", "nav", "footer"]):
        script.decompose()

    # Extract text
    text = soup.get_text(separator='\n', strip=True)

    # Clean up whitespace
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    text = '\n'.join(lines)

    # Limit to max_chars for token efficiency
    return text[:max_chars]

def extract_structured_data(html: str) -> dict:
    """Extract structured data like awards, years, and tech mentions."""
    soup = BeautifulSoup(html, 'html.parser')

    # Look for award/prize information
    awards = []
    years = set()
    techs = set()

    # Find potential award entries
    for elem in soup.find_all(['h2', 'h3', 'div', 'li']):
        text = elem.get_text(strip=True)
        if any(keyword in text.lower() for keyword in ['award', 'prize', 'winner', '수상', '입상', '우승']):
            awards.append(text[:200])
        # Extract years
        year_match = re.findall(r'20\d{2}', text)
        years.update(year_match)
        # Extract tech keywords
        tech_keywords = ['AI', 'ML', 'IoT', 'blockchain', 'cloud', 'web3', 'AR', 'VR', 'python', 'java', 'react', 'node', 'database', '인공지능', 'AI', 'IoT', 'blockchain']
        for tech in tech_keywords:
            if tech.lower() in text.lower():
                techs.add(tech)

    return {
        'awards': awards[:10],
        'years': sorted(list(years), reverse=True)[:5],
        'tech_mentions': list(techs)[:10]
    }

def analyze_with_claude(url: str, html_content: str) -> dict:
    """Analyze content using Claude Haiku with prompt caching."""
    text_content = extract_text_from_html(html_content)
    structured_data = extract_structured_data(html_content)

    analysis_prompt = f"""
웹사이트 분석 요청:
URL: {url}

추출된 정보:
- 수상 이력: {json.dumps(structured_data['awards'], ensure_ascii=False, indent=2)}
- 언급된 연도: {', '.join(structured_data['years'])}
- 기술 트렌드: {', '.join(structured_data['tech_mentions'])}

본문 (첫 8000자):
{text_content}

요청사항:
1. 상위 5개의 수상 기술/분야 분석
2. 최신 기술 트렌드 파악
3. 경쟁력 있는 3가지 아이디어 제시 (임베디드 시스템 제외)
4. 각 아이디어별 기술 스택
5. 간단한 데이터 흐름도 (ASCII 형식)

JSON 형식으로 응답:
{{
  "awards_analysis": "상위 기술/분야",
  "tech_trends": ["기술1", "기술2", ...],
  "ideas": [
    {{
      "title": "아이디어 제목",
      "description": "설명 (50자 이내)",
      "tech_stack": ["기술1", "기술2", ...],
      "flow_diagram": "ASCII 다이어그램"
    }}
  ]
}}
"""

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=[
            {
                "type": "text",
                "text": "당신은 기술 트렌드 분석 전문가입니다. 대회/공모전 웹사이트에서 추출한 정보를 분석하여 경쟁력 있는 프로젝트 아이디어를 제시합니다. 응답은 항상 유효한 JSON 형식이어야 합니다.",
                "cache_control": {"type": "ephemeral"}
            }
        ],
        messages=[
            {
                "role": "user",
                "content": analysis_prompt
            }
        ]
    )

    try:
        result_text = response.content[0].text
        # Try to extract JSON from response
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except (json.JSONDecodeError, IndexError):
        pass

    return {
        "awards_analysis": "분석 실패",
        "tech_trends": [],
        "ideas": [],
        "raw_response": result_text
    }

def main():
    if len(sys.argv) < 2:
        print("사용법: python analyze_competition.py <URL>")
        sys.exit(1)

    url = sys.argv[1]

    print(f"분석 중: {url}")
    html = fetch_url(url)

    if html.startswith("Error"):
        print(html)
        sys.exit(1)

    result = analyze_with_claude(url, html)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
