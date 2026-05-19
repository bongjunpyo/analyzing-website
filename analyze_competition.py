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

def extract_tech_keywords(text: str) -> list:
    """Extract technology keywords from text."""
    tech_keywords = {
        'AI': ['ai', 'artificial intelligence', '인공지능', 'machine learning', 'deep learning'],
        'IoT': ['iot', '사물인터넷', 'sensor', '센서'],
        'Cloud': ['cloud', '클라우드', 'aws', 'azure', 'gcp'],
        'Mobile': ['android', 'ios', 'app', 'mobile', '앱'],
        'Web': ['web', 'react', 'vue', 'angular', 'node.js', '웹'],
        'Python': ['python', 'tensorflow', 'pytorch', 'pandas'],
        'C++': ['c++', 'embedded', 'ros', 'cuda'],
        'Blockchain': ['blockchain', '블록체인', 'ethereum', 'smart contract'],
        'AR/VR': ['ar', 'vr', 'augmented reality', 'virtual reality'],
        'Database': ['database', 'sql', 'mongodb', 'postgresql', '데이터베이스']
    }

    found_techs = set()
    text_lower = text.lower()

    for category, keywords in tech_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                found_techs.add(category)
                break

    return list(found_techs)

def extract_structured_data(html: str) -> dict:
    """Extract structured data from HTML."""
    soup = BeautifulSoup(html, 'html.parser')

    awards = []
    years = set()
    all_text = soup.get_text()

    # Extract years
    year_matches = re.findall(r'20\d{2}', all_text)
    years.update(year_matches)

    # Extract award-related text
    for elem in soup.find_all(['h2', 'h3', 'div', 'li', 'p']):
        text = elem.get_text(strip=True)
        if any(kw in text.lower() for kw in ['award', 'prize', 'winner', '수상', '입상', '우승', '대상', '금상', '은상', '동상']):
            if len(text) > 10:
                awards.append(text[:250])

    techs = extract_tech_keywords(all_text)

    return {
        'awards': awards[:15],
        'years': sorted(list(set(years)), reverse=True)[:10],
        'tech_mentions': techs
    }

async def fetch_award_history(base_url: str) -> dict:
    """Fetch and analyze award history page."""
    # Try common award history URLs
    award_urls = [
        base_url.replace('free.php', '../community/award.php').replace('/competition/', '/community/'),
        base_url.rsplit('/', 1)[0] + '/../community/award.php',
        'https://www.eswcontest.or.kr/community/award.php'
    ]

    for url in award_urls:
        try:
            print(f"📜 수상이력 페이지 확인 중: {url}")
            html = await fetch_url_playwright(url)
            if not html.startswith("Error"):
                text = extract_text_from_html(html, max_chars=15000)
                data = extract_structured_data(html)
                return {
                    'found': True,
                    'url': url,
                    'awards': data['awards'],
                    'years': data['years'],
                    'techs': data['tech_mentions'],
                    'text_sample': text[:2000]
                }
        except:
            continue

    return {
        'found': False,
        'awards': [],
        'years': [],
        'techs': [],
        'text_sample': ''
    }

def analyze_with_gemini(url: str, main_html: str, award_data: dict) -> dict:
    """Analyze content using Google Gemini API."""
    main_text = extract_text_from_html(main_html, max_chars=8000)
    main_data = extract_structured_data(main_html)

    # Combine award history data
    combined_awards = award_data.get('awards', []) + main_data['awards']
    all_techs = set(award_data.get('techs', []) + main_data['tech_mentions'])

    analysis_prompt = f"""
경진대회 웹사이트 종합 분석:
URL: {url}

=== 수상이력 정보 ===
{json.dumps(combined_awards[:5], ensure_ascii=False, indent=2)}

=== 과거 우승작 사용 기술 ===
{', '.join(sorted(all_techs))}

=== 주요 파트너사 ===
LG전자 (스마트가전), 현대자동차 (모빌리티)

=== 대회 개요 ===
{main_text[:3000]}

요청:
1. 수상이력 기반 상위 5개 기술/분야 분석
2. 최신 기술 트렌드 파악
3. 경쟁력 있는 3가지 아이디어 (임베디드 제외)
4. 각 아이디어 기술 스택
5. ASCII 데이터 흐름도

JSON 형식 응답:
{{
  "awards_analysis": "수상이력 분석 (상위 기술/분야)",
  "past_winners_tech": ["기술1", "기술2", ...],
  "tech_trends": ["기술1", "기술2", ...],
  "ideas": [
    {{
      "title": "아이디어",
      "description": "설명",
      "tech_stack": ["기술1", "기술2"],
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
                max_output_tokens=1200,
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
            "past_winners_tech": list(all_techs),
            "tech_trends": list(all_techs),
            "ideas": [],
            "error": str(e)
        }

    return {
        "awards_analysis": "분석 실패",
        "past_winners_tech": list(all_techs),
        "tech_trends": list(all_techs),
        "ideas": []
    }

async def main():
    if len(sys.argv) < 2:
        print("사용법: python analyze_competition.py <URL>")
        sys.exit(1)

    url = sys.argv[1]
    setup_gemini()

    print(f"🌐 메인 페이지 렌더링 중: {url}")
    main_html = await fetch_url_playwright(url)

    if main_html.startswith("Error"):
        print(main_html)
        sys.exit(1)

    print("📜 수상이력 페이지 스크래핑 중...")
    award_data = await fetch_award_history(url)

    if award_data['found']:
        print(f"✅ 수상이력 발견: {award_data['years']}")
    else:
        print("⚠️ 수상이력 페이지 미발견 - 메인 페이지 정보로 분석")

    print("📊 Google Gemini로 분석 중...")
    result = analyze_with_gemini(url, main_html, award_data)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
