"""Render an honest, theme-aware isometric city from GitHub daily counts.

Python standard library only. --refresh uses GITHUB_TOKEN; no credentials are stored.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
from html import escape
import json
import math
import os
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/contributions.json'


def fetch_calendar():
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        raise RuntimeError('Set GITHUB_TOKEN to refresh, or omit --refresh to use the saved snapshot.')
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=364)).replace(hour=0, minute=0, second=0, microsecond=0)
    query = '''query($from:DateTime!,$to:DateTime!){ user(login:"Alchemist-10") { contributionsCollection(from:$from,to:$to) { contributionCalendar { totalContributions weeks { contributionDays { date contributionCount weekday } } } } } }'''
    request = urllib.request.Request('https://api.github.com/graphql', data=json.dumps({'query':query,'variables':{'from':start.isoformat(),'to':now.isoformat()}}).encode(), headers={'Authorization':f'Bearer {token}','User-Agent':'Alchemist-10-profile-city','Content-Type':'application/json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get('errors'):
        raise RuntimeError('GitHub rejected the calendar query; keeping the previous snapshot.')
    return result['data']['user']['contributionsCollection']['contributionCalendar']


def validate(calendar):
    days = [d for w in calendar['weeks'] for d in w['contributionDays']]
    if not 350 <= len(days) <= 371:
        raise ValueError('Expected approximately one year of activity.')
    if len({d['date'] for d in days}) != len(days):
        raise ValueError('Duplicate calendar dates.')
    for day in days:
        datetime.strptime(day['date'], '%Y-%m-%d')
        if not isinstance(day['contributionCount'], int) or day['contributionCount'] < 0 or not 0 <= day['weekday'] <= 6:
            raise ValueError('Invalid day record.')
    if sum(d['contributionCount'] for d in days) != calendar['totalContributions']:
        raise ValueError('Calendar totals do not agree.')
    return days


def city(calendar, theme):
    days = validate(calendar)
    dark = theme == 'dark'
    bg, ink, muted, line = ('#080808','#eeeeee','#a1a1a1','#343434') if dark else ('#fafafa','#151515','#666666','#c5c5c5')
    total = calendar['totalContributions']
    active = sum(d['contributionCount'] > 0 for d in days)
    peak = max(d['contributionCount'] for d in days)
    period = f"{days[0]['date']} / {days[-1]['date']}"
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="490" viewBox="0 0 1200 490" role="img" aria-labelledby="title desc"><title id="title">Alchemist-10 contribution city</title><desc id="desc">{total} contributions across {len(days)} days; {active} active days. Each lot is one day; building height follows its count. No simulated contributions.</desc>',
         f'<defs><pattern id="hatch" width="4" height="4" patternUnits="userSpaceOnUse"><path d="M0 0L4 4" stroke="{ink}" stroke-width=".6"/></pattern></defs>',
         f'<rect width="1200" height="490" fill="{bg}"/>',
         f'<g font-family="monospace" fill="{ink}"><text x="46" y="46" font-size="12" letter-spacing="3">A YEAR, BUILT ONE DAY AT A TIME</text><text x="46" y="85" font-size="28" font-weight="bold">CONTRIBUTION CITY</text><text x="1154" y="46" text-anchor="end" font-size="12" fill="{muted}">ALCHEMIST-10 / GITHUB</text><text x="1154" y="81" text-anchor="end" font-size="12" fill="{muted}">{period}</text></g>']
    buildings = []
    for week_index, week in enumerate(calendar['weeks']):
        for day in week['contributionDays']:
            x = 90 + week_index * 17.4 + day['weekday'] * 11
            y = 328 - week_index * 2.1 + day['weekday'] * 6.3
            count = day['contributionCount']
            s.append(f'<path d="M{x:.1f},{y:.1f}l10,-5 10,5 -10,5z" fill="{bg}" stroke="{line}" stroke-width=".7"/>')
            if not count:
                continue
            height = 9 + 28 * math.log2(count + 1)
            shape = f'<g><title>{day["date"]}: {count} contributions</title>'
            shape += f'<path d="M{x:.1f},{y-height:.1f}l10,5v{height:.1f}l-10,-5z" fill="{bg}" stroke="{ink}" stroke-width=".8"/>'
            shape += f'<path d="M{x+10:.1f},{y-height+5:.1f}l10,-5v{height:.1f}l-10,5z" fill="url(#hatch)" stroke="{ink}" stroke-width=".8"/>'
            shape += f'<path d="M{x:.1f},{y-height:.1f}l10,-5 10,5 -10,5z" fill="{ink}" stroke="{ink}" stroke-width=".6"/>'
            for level in range(12, int(height)-4, 11):
                shape += f'<path d="M{x+3:.1f},{y-level:.1f}l4,2" stroke="{ink}" stroke-width="1.4"/>'
            buildings.append((y, shape + '</g>'))
    s.extend(shape for _, shape in sorted(buildings))
    s += [f'<path d="M46 392H1154" stroke="{line}"/>',f'<g font-family="monospace" fill="{ink}"><text x="46" y="426" font-size="28" font-weight="bold">{total}</text><text x="140" y="425" font-size="11" fill="{muted}">CONTRIBUTIONS</text><text x="365" y="426" font-size="28" font-weight="bold">{active}</text><text x="435" y="425" font-size="11" fill="{muted}">ACTIVE DAYS</text><text x="660" y="426" font-size="28" font-weight="bold">{peak}</text><text x="730" y="425" font-size="11" fill="{muted}">BUSIEST DAY</text><text x="46" y="464" font-size="10" fill="{muted}">ONE LOT = ONE DAY / HEIGHT FOLLOWS CONTRIBUTION COUNT / REFRESHED WEEKLY</text></g></svg>']
    return ''.join(s)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    calendar = fetch_calendar() if args.refresh else json.loads(DATA.read_text())
    validate(calendar)
    rendered = {theme:city(calendar,theme) for theme in ['dark','light']}
    if args.refresh:
        DATA.write_text(json.dumps(calendar,indent=2)+'\n', encoding='utf8')
    for theme, content in rendered.items():
        (ROOT / f'assets/contribution-city-{theme}.svg').write_text(content, encoding='utf8')
    print(f"Rendered city: {calendar['totalContributions']} actual contributions")


if __name__ == '__main__':
    main()
