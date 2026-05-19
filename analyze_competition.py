#!/usr/bin/env python3
import json
import os
import sys
import re
import asyncio

import google.generativeai as genai
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

def setup_gemini():
    """Setup Google Gemini API."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
        sys.exit(1)
    genai.configure(api_key=api_key)

async def fetch_url_playwright(url: str) -> str:
    """Fetch URL using Playwright and return rendered HTML."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            content = await page.content()
            await browser.close()
            return content
        except Exception as e:
            await browser.close()
            return f"Error fetching URL: {str(e)}"

def extract_text_from_html(html: str, max_chars: int = 8000) -> str:
    """Extract meaningful text from HTML."""
    soup = BeautifulSoup(html, 'html.parser')

    for script in soup(["script", "style", "nav", "footer"]):
        script.decompose()

    text = soup.get_text(separator='\n', strip=True)
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    text = '\n'.join(lines)

    return text[:max_chars]

def extract_structured_data(html: str) -> dict:
    """Extract structured data like awards, years, and tech mentions."""
    soup = BeautifulSoup(html, 'html.parser')

    awards = []
    years = set()
    techs = set()

    for elem in soup.find_all(['h2', 'h3', 'div', 'li']):
        text = elem.get_text(strip=True)
        if any(keyword in text.lower() for keyword in ['award', 'prize', 'winner', '수상', '입상', '우승']):
            awards.append(text[:200])

        year_match = re.findall(r'20\d{2}', text)
        years.update(year_match)

        tech_keywords = ['AI', 'ML', 'IoT', 'blockchain', 'cloud', 'web3', 'AR', 'VR', 'python', 'java', 'react', 'node', 'database', '인공지능']
        for tech in tech_keywords:
            if tech.lower() in text.lower():
                techs.add(tech)

    return {
        'awards': awards[:10],
        'years': sorted(list(years), reverse=True)[:5],
        'tech_mentions': list(techs)[:10]
    }

def analyze_with_gemini(url: str, html_content: str) -> dict:
    """Analyze content using Google Gemini API."""
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
      "description": "설명",
      "tech_stack": ["기술1", "기술2", ...],
      "flow_diagram": "ASCII 다이어그램"
    }}
  ]
}}
"""

    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(
            analysis_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=1024,
            )
        )

        result_text = response.text
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError:
        pass
    except Exception as e:
        print(f"⚠️ Gemini API 오류: {e}")
        return {
            "awards_analysis": "분석 실패",
            "tech_trends": [],
            "ideas": [],
            "error": str(e)
        }

    return {
        "awards_analysis": "분석 실패",
        "tech_trends": [],
        "ideas": []
    }

async def main():
    if len(sys.argv) < 2:
        print("사용법: python analyze_competition.py <URL>")
        sys.exit(1)

    url = sys.argv[1]
    setup_gemini()

    print(f"🌐 Playwright로 웹사이트 렌더링 중: {url}")
    html = await fetch_url_playwright(url)

    if html.startswith("Error"):
        print(html)
        sys.exit(1)

    print("📊 Google Gemini로 분석 중...")
    result = analyze_with_gemini(url, html)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
