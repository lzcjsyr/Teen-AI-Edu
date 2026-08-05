#!/usr/bin/env python3
import sys
import os
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Capture high-resolution Retina screenshots of Xiaohongshu HTML cards.")
    parser.add_argument("html_path", type=str, help="Absolute path to the xiaohongshu_slides.html file.")
    args = parser.parse_args()
    
    html_file = Path(args.html_path).resolve()
    if not html_file.exists():
        print(f"Error: HTML file not found at {html_file}", file=sys.stderr)
        sys.exit(1)
        
    # If the HTML is located inside an 'html' subfolder, save screenshots to a sibling 'images' folder
    if html_file.parent.name == "html":
        output_dir = html_file.parent.parent / "images"
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = html_file.parent

    
    # Try importing playwright
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed. Attempting to install playwright library...", file=sys.stderr)
        import subprocess
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
            print("Installing browser binaries...", file=sys.stderr)
            subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
            from playwright.sync_api import sync_playwright
        except Exception as e:
            print(f"Failed to install Playwright: {e}", file=sys.stderr)
            print("Please make sure you have python3 and pip installed, and execute: pip install playwright && playwright install", file=sys.stderr)
            sys.exit(1)

    print(f"Opening {html_file} in headless Chromium...", file=sys.stderr)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Use device_scale_factor=2 for crisp Retina scale text and graphics!
        context = browser.new_context(device_scale_factor=2)
        page = context.new_page()
        
        # Open local HTML file
        page.goto(html_file.as_uri())
        
        # Wait for Web fonts and resources to load completely
        page.wait_for_load_state("networkidle")
        page.evaluate("document.fonts.ready")
        
        # Locate all .xhs-card containers
        cards = page.query_selector_all(".xhs-card")
        if not cards:
            print("Error: No card elements matching '.xhs-card' found.", file=sys.stderr)
            browser.close()
            sys.exit(1)
            
        print(f"Found {len(cards)} card(s). Capturing screenshots...", file=sys.stderr)
        
        for index, card in enumerate(cards, start=1):
            image_path = output_dir / f"slide_{index}.png"
            # Take a bounding-box element screenshot
            card.screenshot(path=str(image_path))
            print(f"Saved: {image_path.name}")
            
        browser.close()
        print("All screenshots successfully captured!")

if __name__ == "__main__":
    main()
