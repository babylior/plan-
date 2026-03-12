"""
storyboard.py - Generates a visual storyboard HTML + image grid from segments with frames
"""
import os
import textwrap
from pathlib import Path
from typing import List, Dict, Optional
from PIL import Image, ImageDraw, ImageFont


# ── Frame card rendering ──────────────────────────────────────────────────────

CARD_WIDTH = 640
CARD_PADDING = 20
FONT_SIZE = 22
LINE_SPACING = 6
BG_COLOR = (15, 15, 15)
TEXT_COLOR = (255, 255, 255)
BORDER_COLOR = (60, 60, 60)
TIME_COLOR = (150, 200, 255)


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    """Try to load a nice font, fall back to default."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    """Wrap text so each line fits within max_width pixels."""
    words = text.split()
    lines: List[str] = []
    current = ""
    dummy = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(dummy)

    for word in words:
        test = (current + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def render_card(segment: Dict, index: int) -> Image.Image:
    """Render a storyboard card: frame image + timestamp + subtitle text."""
    frame_path = segment.get("frame_path")
    text = segment.get("text", "")
    start = segment.get("start", 0)
    end = segment.get("end", 0)
    timestamp = f"[{_fmt_time(start)} → {_fmt_time(end)}]"

    # Load frame image
    if frame_path and os.path.exists(frame_path):
        frame_img = Image.open(frame_path).convert("RGB")
        # Scale frame to card width maintaining aspect ratio
        aspect = frame_img.height / frame_img.width
        frame_h = int(CARD_WIDTH * aspect)
        frame_img = frame_img.resize((CARD_WIDTH, frame_h), Image.LANCZOS)
    else:
        frame_h = int(CARD_WIDTH * 9 / 16)
        frame_img = Image.new("RGB", (CARD_WIDTH, frame_h), (40, 40, 40))
        draw_placeholder = ImageDraw.Draw(frame_img)
        draw_placeholder.text(
            (CARD_WIDTH // 2, frame_h // 2),
            "No frame",
            fill=(120, 120, 120),
            anchor="mm",
        )

    # Prepare text area
    font_text = _load_font(FONT_SIZE)
    font_time = _load_font(int(FONT_SIZE * 0.8))
    font_num = _load_font(int(FONT_SIZE * 1.1))

    text_area_width = CARD_WIDTH - 2 * CARD_PADDING
    lines = _wrap_text(text, font_text, text_area_width)

    # Calculate text block height
    dummy = Image.new("RGB", (1, 1))
    draw_dummy = ImageDraw.Draw(dummy)
    line_h = draw_dummy.textbbox((0, 0), "Ay", font=font_text)[3] + LINE_SPACING
    time_h = draw_dummy.textbbox((0, 0), timestamp, font=font_time)[3] + LINE_SPACING
    num_h = draw_dummy.textbbox((0, 0), f"#{index+1}", font=font_num)[3]

    text_block_h = CARD_PADDING + num_h + 8 + time_h + 8 + len(lines) * line_h + CARD_PADDING

    total_h = frame_h + text_block_h
    card = Image.new("RGB", (CARD_WIDTH, total_h), BG_COLOR)

    # Paste frame
    card.paste(frame_img, (0, 0))

    draw = ImageDraw.Draw(card)

    # Draw border between frame and text
    draw.line([(0, frame_h), (CARD_WIDTH, frame_h)], fill=BORDER_COLOR, width=2)

    y = frame_h + CARD_PADDING

    # Card number
    draw.text((CARD_PADDING, y), f"#{index+1}", fill=TIME_COLOR, font=font_num)
    y += num_h + 8

    # Timestamp
    draw.text((CARD_PADDING, y), timestamp, fill=TIME_COLOR, font=font_time)
    y += time_h + 8

    # Subtitle lines
    for line in lines:
        draw.text((CARD_PADDING, y), line, fill=TEXT_COLOR, font=font_text)
        y += line_h

    # Outer border
    draw.rectangle([(0, 0), (CARD_WIDTH - 1, total_h - 1)], outline=BORDER_COLOR, width=2)

    return card


def _fmt_time(seconds: float) -> str:
    """Format seconds as MM:SS."""
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m:02d}:{s:02d}"


# ── Grid assembly ─────────────────────────────────────────────────────────────

def build_storyboard_image(
    segments: List[Dict],
    output_path: str,
    columns: int = 2,
) -> str:
    """
    Assemble all cards into a grid image and save as PNG.
    Returns the output path.
    """
    if not segments:
        raise ValueError("No segments to render.")

    print("  Rendering cards...")
    cards = [render_card(seg, i) for i, seg in enumerate(segments)]

    # Ensure all cards have the same width
    max_w = max(c.width for c in cards)
    resized = []
    for c in cards:
        if c.width != max_w:
            scale = max_w / c.width
            resized.append(c.resize((max_w, int(c.height * scale)), Image.LANCZOS))
        else:
            resized.append(c)

    # Arrange in columns
    rows = [resized[i : i + columns] for i in range(0, len(resized), columns)]

    gap = 10
    row_images = []
    for row in rows:
        row_h = max(c.height for c in row)
        row_img = Image.new("RGB", (max_w * columns + gap * (columns - 1), row_h), (5, 5, 5))
        x = 0
        for card in row:
            row_img.paste(card, (x, 0))
            x += max_w + gap
        row_images.append(row_img)

    total_h = sum(r.height for r in row_images) + gap * (len(row_images) - 1)
    total_w = row_images[0].width if row_images else max_w
    grid = Image.new("RGB", (total_w, total_h), (5, 5, 5))
    y = 0
    for row_img in row_images:
        grid.paste(row_img, (0, y))
        y += row_img.height + gap

    grid.save(output_path, format="PNG", optimize=True)
    print(f"  Storyboard image saved: {output_path}")
    return output_path


# ── HTML report ───────────────────────────────────────────────────────────────

def build_storyboard_html(segments: List[Dict], output_path: str, video_url: str = "") -> str:
    """
    Build a standalone HTML page showing all storyboard cards.
    Each card shows the frame (inline base64) and the subtitle.
    """
    import base64

    def img_to_b64(path: Optional[str]) -> str:
        if path and os.path.exists(path):
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        return ""

    cards_html = []
    for i, seg in enumerate(segments):
        b64 = img_to_b64(seg.get("frame_path"))
        img_tag = (
            f'<img src="data:image/jpeg;base64,{b64}" alt="frame {i+1}">'
            if b64
            else '<div class="no-frame">No frame</div>'
        )
        start = _fmt_time(seg["start"])
        end = _fmt_time(seg["end"])
        text = seg.get("text", "").replace("<", "&lt;").replace(">", "&gt;")
        cards_html.append(f"""
        <div class="card">
          <div class="frame-wrap">{img_tag}</div>
          <div class="info">
            <span class="num">#{i+1}</span>
            <span class="time">{start} → {end}</span>
            <p class="subtitle">{text}</p>
          </div>
        </div>""")

    source_line = f'<p class="source">Source: <a href="{video_url}">{video_url}</a></p>' if video_url else ""

    html = f"""<!DOCTYPE html>
<html lang="he" dir="auto">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Video Storyboard</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0d0d0d;
    color: #f0f0f0;
    font-family: 'Segoe UI', Arial, sans-serif;
    padding: 24px;
  }}
  h1 {{
    text-align: center;
    font-size: 2rem;
    margin-bottom: 8px;
    color: #96c8ff;
  }}
  .source {{
    text-align: center;
    font-size: 0.85rem;
    color: #888;
    margin-bottom: 28px;
    word-break: break-all;
  }}
  .source a {{ color: #96c8ff; }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 16px;
    max-width: 1400px;
    margin: 0 auto;
  }}
  .card {{
    background: #1a1a1a;
    border: 1px solid #333;
    border-radius: 10px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    transition: transform .15s, box-shadow .15s;
  }}
  .card:hover {{
    transform: translateY(-3px);
    box-shadow: 0 8px 24px rgba(0,0,0,.5);
  }}
  .frame-wrap img {{
    width: 100%;
    display: block;
  }}
  .no-frame {{
    background: #2a2a2a;
    height: 180px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #555;
    font-size: 0.9rem;
  }}
  .info {{
    padding: 12px 14px;
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }}
  .num {{
    font-size: 0.75rem;
    font-weight: 700;
    color: #96c8ff;
  }}
  .time {{
    font-size: 0.78rem;
    color: #96c8ff;
    opacity: .85;
  }}
  .subtitle {{
    font-size: 0.95rem;
    line-height: 1.5;
    color: #e8e8e8;
    direction: auto;
  }}
</style>
</head>
<body>
<h1>🎬 Video Storyboard</h1>
{source_line}
<div class="grid">
{''.join(cards_html)}
</div>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  HTML storyboard saved: {output_path}")
    return output_path
