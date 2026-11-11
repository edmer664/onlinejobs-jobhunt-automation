"""
Template-Driven Resume PDF Builder.
Reads candidate profile configuration (config/profile.yaml or config/profile.json)
and generates a clean, single-page PDF resume using Playwright.
"""

import argparse
import asyncio
import os
import sys
from typing import Any, Dict

# Add src and repo root to sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")

for p in (PROJECT_ROOT, SRC_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from src.config_loader import get_candidate_profile
except ImportError:
    from config_loader import get_candidate_profile


def build_resume_html(profile: Dict[str, Any]) -> str:
    candidate = profile.get("candidate", {})
    name = candidate.get("display_name") or candidate.get("name") or "Candidate Name"
    location = candidate.get("location", "Remote, Worldwide")
    phone = candidate.get("phone", "+1-555-0199")
    email = candidate.get("email", "candidate@example.com")
    linkedin = candidate.get("linkedin", "https://linkedin.com")
    portfolio = candidate.get("portfolio_url", "https://example.com")
    degree = candidate.get("degree", "Bachelor of Science in Information Technology")

    experience_items = profile.get("verified_experience", [])
    skills_items = profile.get("candidate_skills", [])
    certifications = profile.get("candidate", {}).get("certifications", [])

    exp_html = ""
    for exp in experience_items:
        role = exp.get("role", "")
        company = exp.get("company", "")
        period = exp.get("period", "")
        bullets = exp.get("bullets", [])
        bullets_html = "".join(f"<li>{b}</li>" for b in bullets)
        exp_html += f"""
        <div class="exp-block">
            <div class="exp-header">
                <span class="exp-role">{role}</span>
                <span class="exp-period">{period}</span>
            </div>
            <div class="exp-company">{company}</div>
            <ul class="exp-bullets">
                {bullets_html}
            </ul>
        </div>
        """

    skills_labels = [s.get("label", s.get("name", "")) for s in skills_items if isinstance(s, dict)]
    skills_str = " • ".join(skills_labels) if skills_labels else "Virtual Assistance • Data Management • Executive Administration"

    certs_html = ""
    if certifications:
        certs_html = " • ".join(certifications)
    else:
        certs_html = "Certified Professional • Information Technology Specialist"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{name} - Resume</title>
<style>
  @page {{
    size: letter;
    margin: 0.4in 0.5in;
  }}
  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    color: #0D0D0D;
    background: #FFFFFF;
    line-height: 1.35;
    font-size: 9.5pt;
  }}
  .header {{
    text-align: center;
    border-bottom: 2px solid #0047DF;
    padding-bottom: 8px;
    margin-bottom: 12px;
  }}
  h1 {{
    font-size: 18pt;
    font-weight: 700;
    color: #0D0D0D;
    letter-spacing: -0.5px;
    margin-bottom: 4px;
    text-transform: uppercase;
  }}
  .subtitle {{
    font-size: 10pt;
    font-weight: 600;
    color: #0047DF;
    margin-bottom: 6px;
  }}
  .contact-bar {{
    font-size: 8.5pt;
    color: #4B5563;
    display: flex;
    justify-content: center;
    gap: 10px;
    flex-wrap: wrap;
  }}
  .contact-bar a {{
    color: #0047DF;
    text-decoration: none;
  }}
  .section {{
    margin-bottom: 12px;
  }}
  .section-title {{
    font-size: 10pt;
    font-weight: 700;
    color: #0047DF;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-bottom: 1px solid #E5E5E5;
    padding-bottom: 2px;
    margin-bottom: 6px;
  }}
  .exp-block {{
    margin-bottom: 8px;
  }}
  .exp-header {{
    display: flex;
    justify-content: space-between;
    font-weight: 600;
    font-size: 9.5pt;
  }}
  .exp-period {{
    color: #6B7280;
    font-weight: 500;
    font-size: 8.5pt;
  }}
  .exp-company {{
    font-size: 9pt;
    color: #374151;
    margin-bottom: 3px;
  }}
  .exp-bullets {{
    margin-left: 18px;
    font-size: 9pt;
  }}
  .exp-bullets li {{
    margin-bottom: 2px;
  }}
  .skills-text {{
    font-size: 9pt;
    line-height: 1.4;
  }}
</style>
</head>
<body>
  <div class="header">
    <h1>{name}</h1>
    <div class="subtitle">Remote Operations Specialist | Executive Virtual Assistant</div>
    <div class="contact-bar">
      <span>{location}</span> •
      <span>{phone}</span> •
      <span>{email}</span> •
      <a href="{linkedin}">LinkedIn</a> •
      <a href="{portfolio}">Portfolio</a>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Core Competencies & Tools</div>
    <div class="skills-text">{skills_str}</div>
  </div>

  <div class="section">
    <div class="section-title">Professional Experience</div>
    {exp_html}
  </div>

  <div class="section">
    <div class="section-title">Education & Certifications</div>
    <div class="exp-block">
      <div class="exp-header">
        <span class="exp-role">{degree}</span>
      </div>
      <div class="skills-text" style="margin-top: 3px;">
        <strong>Certifications:</strong> {certs_html}
      </div>
    </div>
  </div>
</body>
</html>"""


async def render_pdf(html_content: str, output_pdf_path: str):
    from playwright.async_api import async_playwright

    os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = await browser.new_page()
        await page.set_content(html_content, wait_until="networkidle")
        await page.pdf(
            path=output_pdf_path,
            format="Letter",
            print_background=True,
            margin={"top": "0.4in", "bottom": "0.4in", "left": "0.5in", "right": "0.5in"},
        )
        await browser.close()
    print(f"[Resume Builder] Successfully generated PDF resume: {output_pdf_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate PDF resume from candidate profile")
    parser.add_argument(
        "--config",
        help="Path to candidate profile configuration file (YAML or JSON)",
    )
    parser.add_argument(
        "--output",
        default=os.path.join(PROJECT_ROOT, "config", "resume.pdf"),
        help="Output path for PDF resume (default: config/resume.pdf)",
    )
    parser.add_argument(
        "--html-only",
        action="store_true",
        help="Generate HTML only without requiring Playwright",
    )
    args = parser.parse_args()

    profile = get_candidate_profile(args.config)
    html_content = build_resume_html(profile)

    html_out = os.path.splitext(args.output)[0] + ".html"
    with open(html_out, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[Resume Builder] Saved resume HTML: {html_out}")

    if not args.html_only:
        try:
            asyncio.run(render_pdf(html_content, args.output))
        except Exception as exc:
            print(f"[Resume Builder] Notice: Playwright PDF rendering encountered: {exc}")
            print(f"[Resume Builder] HTML file remains available at {html_out}")


if __name__ == "__main__":
    main()
