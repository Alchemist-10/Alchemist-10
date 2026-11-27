"""Check local assets, SVG validity, actual calendar totals, and preserved links."""
from pathlib import Path
import importlib.util
import json
import re
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
text = (root/'README.md').read_text(encoding='utf-8-sig')
for asset in set(re.findall(r'assets/[a-zA-Z0-9_./-]+', text)):
    assert (root/asset).is_file(), f'Missing {asset}'
for svg in (root/'assets').glob('*.svg'):
    tree=ET.parse(svg)
    assert tree.getroot().tag.endswith('svg')
    assert '<script' not in svg.read_text().lower()
required_links = [
    'https://github.com/Alchemist-10/turbformer',
    'https://github.com/Alchemist-10/nexus_submitted',
    'https://nexus-landing-alpha.vercel.app/',
    'https://github.com/Alchemist-10/Telltale-DNS',
    'https://github.com/Alchemist-10/XEngine',
    'https://github.com/Alchemist-10/SynkIndia',
    'https://www.linkedin.com/in/akshay-vs-84381131a/',
    'mailto:akshaykailath2020@gmail.com',
]
for link in required_links:
    assert link in text, f'Missing {link}'
spec=importlib.util.spec_from_file_location('city',root/'scripts/render_city.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
calendar=json.loads((root/'data/contributions.json').read_text())
module.validate(calendar)
assert module.city(calendar,'dark')==(root/'assets/contribution-city-dark.svg').read_text()
bad=dict(calendar,totalContributions=calendar['totalContributions']+1)
try:
    module.validate(bad)
except ValueError:
    pass
else:
    raise AssertionError('Corrupted totals were accepted')
print(f'Profile assets and {len(required_links)} required links validated; contribution counts agree.')
