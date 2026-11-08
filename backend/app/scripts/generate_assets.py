"""Generator script to produce 36 high-signal challenge SVG pairs and seed_challenges.json."""

import json
from pathlib import Path

from app.core.stats import validate_significance_gate

# Ensure output directories exist
static_thumb_dir = Path("backend/app/static/thumbnails")
static_thumb_dir.mkdir(parents=True, exist_ok=True)
data_dir = Path("backend/data")
data_dir.mkdir(parents=True, exist_ok=True)

CHALLENGES_CONFIG = [
    (
        1,
        "Emotional Face vs Clean Product Focus",
        "Tech",
        "A",
        0.088,
        0.071,
        62000,
        62000,
        ("Shocked Expression", "WHY I SWITCHED", "#ff3366", "#1a0910", "FACE"),
        ("Minimal Clean Device", "THE NEW STANDARD", "#00d2ff", "#05131a", "PRODUCT"),
    ),
    (
        2,
        "High Contrast Yellow Warning vs Dark Mode",
        "Coding",
        "A",
        0.092,
        0.075,
        54000,
        54000,
        ("DON'T DO THIS", "1 BIG MISTAKE", "#ffe600", "#1c1800", "WARNING"),
        ("CLEAN REFACTOR", "Modern Best Practices", "#00ff88", "#001a0e", "PRO"),
    ),
    (
        3,
        "Provocative Question vs Concrete Metric",
        "Finance",
        "B",
        0.068,
        0.086,
        78000,
        78000,
        (
            "Are We In A Bubble?",
            "Market Analysis 2024",
            "#bd00ff",
            "#15021c",
            "QUESTION",
        ),
        ("+312% PROFIT", "Real Portfolio Breakdown", "#00f0ff", "#00171a", "METRIC"),
    ),
    (
        4,
        "Big Red Pointer Arrow vs Subtle Framing",
        "Gaming",
        "A",
        0.104,
        0.082,
        95000,
        95000,
        ("HIDDEN LOCATION", "Found at 03:00 AM", "#ff003b", "#1a0006", "SECRET"),
        ("Full Map Guide", "All Secrets Revealed", "#7928ca", "#0d0317", "GUIDE"),
    ),
    (
        5,
        "Split Screen Before/After vs Climactic Result",
        "Fitness",
        "A",
        0.079,
        0.063,
        48000,
        48000,
        ("DAY 1 vs DAY 90", "Insane Transformation", "#ff6b00", "#1a0b00", "PROGRESS"),
        ("FINAL PHYSIQUE", "My Strict Routine", "#00e5ff", "#00171a", "RESULT"),
    ),
    (
        6,
        "Urgent Mystery Silhouette vs Visible Hardware",
        "Tech",
        "B",
        0.065,
        0.083,
        71000,
        71000,
        ("TOP SECRET LEAK", "They Banned This", "#7000ff", "#0d001f", "LEAK"),
        (
            "NEW CHIP BENCHMARK",
            "M4 Pro Tested vs RTX",
            "#00ff66",
            "#001a0a",
            "BENCHMARK",
        ),
    ),
    (
        7,
        "Hand-Drawn Doodle Notes vs Polished Infographic",
        "Education",
        "A",
        0.095,
        0.077,
        43000,
        43000,
        ("HOW IT ACTUALLY WORKS", "Drawn on Napkin", "#ffe600", "#1f1c00", "SIMPLE"),
        (
            "SYSTEM ARCHITECTURE",
            "Enterprise Design 2024",
            "#0070f3",
            "#000c1c",
            "ARCHITECTURE",
        ),
    ),
    (
        8,
        "Large 3D Number Hook vs Abstract Topic",
        "Productivity",
        "A",
        0.089,
        0.070,
        52000,
        52000,
        ("10X FASTER", "Stop Wasting 4 Hours/Day", "#ff0070", "#1c000c", "SPEED"),
        ("DEEP WORK HABITS", "The Psychology of Flow", "#7928ca", "#0f031c", "HABITS"),
    ),
    (
        9,
        "Macro Extreme Zoom vs Studio Setup",
        "Design",
        "B",
        0.059,
        0.076,
        38000,
        38000,
        ("EVERY PIXEL MATTERS", "1000% Inspection", "#ff0055", "#1c000a", "DETAILS"),
        ("DREAM DESK 2024", "Clean Setup Tour", "#00dfd8", "#001717", "WORKSPACE"),
    ),
    (
        10,
        "Angry Red Alert vs Green Positive Check",
        "Security",
        "A",
        0.084,
        0.066,
        64000,
        64000,
        ("CRITICAL CVE FOUND", "Patch Immediately", "#ff0033", "#1a0005", "DANGER"),
        ("ZERO TRUST PASS", "100% Secure Checklist", "#00cc66", "#00140a", "VERIFIED"),
    ),
    (
        11,
        "Neon Cyberpunk Glow vs Editorial Monochrome",
        "AI",
        "B",
        0.072,
        0.091,
        88000,
        88000,
        ("CYBER AI AGENTS", "The Singularity Is Here", "#ff00aa", "#1c0013", "CYBER"),
        (
            "THE REASONING ERA",
            "Deep Research Evaluation",
            "#f5f5f7",
            "#111111",
            "RESEARCH",
        ),
    ),
    (
        12,
        "Price Comparison '$10 vs $10,000' vs 'Luxury Tour'",
        "Lifestyle",
        "A",
        0.112,
        0.089,
        110000,
        110000,
        (
            "$10 VS $10,000",
            "Cheap vs Expensive Flight",
            "#ffe600",
            "#1f1c00",
            "COMPARE",
        ),
        ("FIRST CLASS SUITE", "The Most Luxury Cabin", "#c5a059", "#17130a", "LUXURY"),
    ),
    (
        13,
        "Exclamation Badge 'STOP!' vs Informative Header",
        "Career",
        "A",
        0.087,
        0.069,
        57000,
        57000,
        (
            "STOP LEARNING REACT!",
            "Learn This Instead in 2024",
            "#ff0033",
            "#1c0006",
            "ALERT",
        ),
        (
            "THE 2024 ROADMAP",
            "Frontend Stack Breakdown",
            "#0070f3",
            "#000d1f",
            "ROADMAP",
        ),
    ),
    (
        14,
        "Giga-Speed Time Lapse vs Step-by-Step Tutorial",
        "Art",
        "A",
        0.081,
        0.064,
        46000,
        46000,
        (
            "100 HOURS IN 10 MINS",
            "Sculpting Full Clay Dragon",
            "#ff5500",
            "#1a0900",
            "TIMELAPSE",
        ),
        (
            "BEGINNER SCULPTING",
            "Basics & Tools Tutorial",
            "#a000ff",
            "#130021",
            "TUTORIAL",
        ),
    ),
    (
        15,
        "Secret Censored Black Bar vs Uncensored Preview",
        "Documentary",
        "A",
        0.098,
        0.076,
        82000,
        82000,
        (
            "[REDACTED] FILES",
            "What NASA Never Said",
            "#e50914",
            "#170102",
            "CLASSIFIED",
        ),
        ("APOLLO MISSIONS", "Restored 4K Footage", "#0099ff", "#00101c", "HISTORIC"),
    ),
    (
        16,
        "High-Saturation Food Close-up vs Plated Aesthetic",
        "Cooking",
        "A",
        0.103,
        0.084,
        91000,
        91000,
        (
            "CRISPY MELT CRUNCH",
            "The Ultimate Smash Burger",
            "#ff9900",
            "#1c1100",
            "CRAVING",
        ),
        ("CHEF'S SIGNATURE", "Fine Dining At Home", "#d4af37", "#171306", "CULINARY"),
    ),
    (
        17,
        "Vs Split Screen Face-off vs Solo Winner Spotlight",
        "Sports",
        "B",
        0.074,
        0.093,
        73000,
        73000,
        (
            "THE FINAL REMATCH",
            "Champion vs Challenger",
            "#ff0044",
            "#1a0007",
            "RIVALRY",
        ),
        ("UNDISPUTED GOAT", "Career Masterclass", "#ffd700", "#1c1800", "CHAMPION"),
    ),
    (
        18,
        "X-Ray Cutaway Graphic vs Exterior Photo",
        "Engineering",
        "A",
        0.091,
        0.073,
        67000,
        67000,
        (
            "INSIDE A JET ENGINE",
            "What Makes It Spin At Mach 2",
            "#00f0ff",
            "#00171a",
            "CUTAWAY",
        ),
        ("BOEING 787 TURBINE", "Engine Walkaround", "#4f5b66", "#0b0d0f", "EXTERIOR"),
    ),
    (
        19,
        "Bold White Text on Black vs Neon Gradient",
        "Philosophy",
        "A",
        0.083,
        0.067,
        51000,
        51000,
        (
            "THE ART OF LETTING GO",
            "Stoicism for the Modern Mind",
            "#ffffff",
            "#0a0a0a",
            "STOIC",
        ),
        ("MEDITATIONS ON FLOW", "Ancient Greek Wisdom", "#9b51e0", "#11091a", "WISDOM"),
    ),
    (
        20,
        "Money Stack Graphic vs Clean Chart Graph",
        "Finance",
        "A",
        0.096,
        0.078,
        63000,
        63000,
        (
            "$50K/MO PASSIVE",
            "How I Built 3 Income Streams",
            "#00e676",
            "#001c0e",
            "INCOME",
        ),
        (
            "COMPOUND INTEREST",
            "Index Fund Model 2024",
            "#2979ff",
            "#050e1f",
            "INVESTING",
        ),
    ),
    (
        21,
        "Direct Eye Contact Close-up vs Pointing Away",
        "Interview",
        "A",
        0.088,
        0.071,
        75000,
        75000,
        (
            "I'M LEAVING TECH",
            "The Dark Truth About Silicon Valley",
            "#ff3366",
            "#1c060c",
            "CONFESSION",
        ),
        ("MY NEXT CHAPTER", "Reflecting on 10 Years", "#00b0ff", "#00141f", "UPDATE"),
    ),
    (
        22,
        "1 Star vs 5 Star Comparison vs Solo Review",
        "Consumer",
        "A",
        0.108,
        0.085,
        105000,
        105000,
        (
            "1 STAR VS 5 STAR",
            "Testing Worst Amazon Items",
            "#ff0055",
            "#1c000a",
            "RATED",
        ),
        (
            "TOP 10 GADGETS",
            "Best Purchases of the Year",
            "#00e5ff",
            "#001a1c",
            "TOP PICKS",
        ),
    ),
    (
        23,
        "Countdown Timer 24H vs Relaxed Challenge",
        "Vlog",
        "A",
        0.094,
        0.073,
        86000,
        86000,
        (
            "24 HOURS SURVIVAL",
            "Trapped In The Frozen Woods",
            "#ff1744",
            "#1f0308",
            "CHALLENGE",
        ),
        (
            "WINTER CAMPING TRIP",
            "Bushcraft Shelter Build",
            "#8d6e63",
            "#140e0c",
            "OUTDOORS",
        ),
    ),
    (
        24,
        "Code Terminal Screengrab vs Abstract Brain/AI",
        "AI",
        "A",
        0.089,
        0.072,
        59000,
        59000,
        ("I REPLACED MYSELF", "Local LLM Agent Pipeline", "#00ff66", "#00170a", "DEV"),
        (
            "FUTURE OF COGNITION",
            "Neural Networks Explained",
            "#7c4dff",
            "#0f0a1f",
            "THEORY",
        ),
    ),
    (
        25,
        "Yellow Caution Tape vs Subtle Clean Badge",
        "News",
        "A",
        0.090,
        0.074,
        69000,
        69000,
        (
            "BREAKING INVESTIGATION",
            "They Hid This For 20 Years",
            "#ffd600",
            "#1c1700",
            "EXPOSED",
        ),
        (
            "POLICY DEEP DIVE",
            "Full Congressional Audit",
            "#607d8b",
            "#0d1114",
            "REPORT",
        ),
    ),
    (
        26,
        "Hand Holding Device vs Floating 3D Render",
        "Hardware",
        "A",
        0.085,
        0.069,
        53000,
        53000,
        (
            "IN THE HANDS",
            "Unfiltered Ergonomics Review",
            "#ffab00",
            "#1c1300",
            "HANDS ON",
        ),
        (
            "FUTURE VISION CONCEPT",
            "Titanium Frame Breakdown",
            "#e040fb",
            "#18061c",
            "CONCEPT",
        ),
    ),
    (
        27,
        "Speedrun Timer Hook vs Final Boss Screenshot",
        "Gaming",
        "A",
        0.101,
        0.080,
        92000,
        92000,
        (
            "WORLD RECORD 14:32",
            "Glitchless Speedrun Broken",
            "#00e676",
            "#001c0e",
            "RECORD",
        ),
        (
            "FINAL BOSS DEFEATED",
            "Level 1 No Damage Run",
            "#d50000",
            "#1a0000",
            "NO DAMAGE",
        ),
    ),
    (
        28,
        "Tear-down Disassembly vs Fully Built Device",
        "Makers",
        "A",
        0.093,
        0.075,
        49000,
        49000,
        (
            "EVERY SCREW TAKEN OUT",
            "Why Apple Glued This",
            "#29b6f6",
            "#05161f",
            "TEARDOWN",
        ),
        (
            "CUSTOM MECHANICAL MOD",
            "Machined Brass Enclosure",
            "#ffb300",
            "#1f1600",
            "BUILD",
        ),
    ),
    (
        29,
        "Big Bold Question Mark Hook vs Statement",
        "Science",
        "B",
        0.069,
        0.087,
        81000,
        81000,
        (
            "WHAT'S INSIDE A BLACK HOLE?",
            "The Event Horizon Mystery",
            "#9c27b0",
            "#140517",
            "MYSTERY",
        ),
        (
            "PHYSICS JUST BROKE",
            "James Webb New Discovery",
            "#ff1744",
            "#1a0207",
            "DISCOVERY",
        ),
    ),
    (
        30,
        "Single Dramatic Color Pop vs Full Rainbow Spectrum",
        "Photography",
        "A",
        0.086,
        0.068,
        44000,
        44000,
        (
            "THE MONO COLOR TRICK",
            "How Master Photographers Shoot",
            "#ff4081",
            "#1a060d",
            "COLOR POP",
        ),
        (
            "COLOR GRADING GUIDE",
            "LUTs and Curves Masterclass",
            "#00e5ff",
            "#00191c",
            "GRADING",
        ),
    ),
    (
        31,
        "Huge Red Circle Annotation vs Centered Hero Shot",
        "Urban",
        "A",
        0.097,
        0.078,
        77000,
        77000,
        ("DO NOT MISS THIS", "Abandoned Mega Bunker", "#ff1744", "#1c0307", "EXPLORE"),
        ("FORGOTTEN FORTRESS", "History Underground", "#78909c", "#0f1214", "URBEX"),
    ),
    (
        32,
        "Before/After Slider Graphic vs Single After Result",
        "Audio",
        "A",
        0.092,
        0.073,
        56000,
        56000,
        (
            "$20 MIC VS $2000 MIC",
            "Can You Hear The Difference?",
            "#00e676",
            "#001a0d",
            "BLIND TEST",
        ),
        (
            "PRO VOCAL CHAIN",
            "Clean Studio Processing",
            "#651fff",
            "#0c041f",
            "PRODUCTION",
        ),
    ),
    (
        33,
        "Shocked Face with Hands on Cheeks vs Calm Explainer",
        "Reaction",
        "A",
        0.106,
        0.084,
        115000,
        115000,
        (
            "NO WAY HE DID THIS!",
            "Pro Player Reaction",
            "#ff3d00",
            "#1f0700",
            "REACTION",
        ),
        (
            "MATCH BREAKDOWN",
            "Tactical Replay Analysis",
            "#0288d1",
            "#00121c",
            "ANALYSIS",
        ),
    ),
    (
        34,
        "Negative 'Why I Quit' vs Positive 'Why I Love'",
        "Career",
        "A",
        0.102,
        0.079,
        87000,
        87000,
        (
            "WHY I QUIT GOOGLE",
            "The Golden Handcuffs Trap",
            "#e53935",
            "#1c0706",
            "QUIT",
        ),
        ("WHY I LOVE TECH", "Growth & Freedom in 2024", "#43a047", "#09170a", "CAREER"),
    ),
    (
        35,
        "Numbered 'Day 100' Badge vs Generic Milestone",
        "Challenge",
        "A",
        0.095,
        0.076,
        72000,
        72000,
        (
            "I SURVIVED 100 DAYS",
            "Hardcore Island Challenge",
            "#ff6d00",
            "#1c0c00",
            "DAY 100",
        ),
        (
            "DESERT ISLAND LIFE",
            "Solo Survival Documentary",
            "#00b0ff",
            "#00141f",
            "SURVIVAL",
        ),
    ),
    (
        36,
        "Clean Floating Model Card vs Busy Feature Collage",
        "ML",
        "B",
        0.071,
        0.090,
        66000,
        66000,
        (
            "ALL 50 FEATURES LISTED",
            "Complete ML Framework Review",
            "#7e57c2",
            "#100b1a",
            "SPECS",
        ),
        (
            "ONE BENCHMARK TO RULE THEM",
            "Frontier Vision Tested",
            "#00e676",
            "#001c0e",
            "BENCHMARK",
        ),
    ),
]


def generate_svg(
    filename: str,
    title: str,
    subtitle: str,
    accent_color: str,
    bg_color: str,
    badge: str,
    variant: str,
):
    """Generate high-contrast, modern SVG thumbnail (16:9 ratio, 1280x720)."""
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <defs>
    <linearGradient id="bg_grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{bg_color}" />
      <stop offset="100%" stop-color="#0a0a0c" />
    </linearGradient>
    <linearGradient id="accent_grad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{accent_color}" />
      <stop offset="100%" stop-color="#ffffff" stop-opacity="0.3" />
    </linearGradient>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="30" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
  </defs>

  <!-- Background Base -->
  <rect width="1280" height="720" fill="url(#bg_grad)" />

  <!-- Ambient Glow Shape -->
  <circle cx="950" cy="360" r="320" fill="{accent_color}" opacity="0.18" filter="url(#glow)" />
  <circle cx="200" cy="600" r="250" fill="{accent_color}" opacity="0.12" filter="url(#glow)" />

  <!-- Geometric Grid Pattern Lines -->
  <g stroke="#ffffff" stroke-opacity="0.04" stroke-width="1.5">
    <line x1="0" y1="180" x2="1280" y2="180" />
    <line x1="0" y1="360" x2="1280" y2="360" />
    <line x1="0" y1="540" x2="1280" y2="540" />
    <line x1="320" y1="0" x2="320" y2="720" />
    <line x1="640" y1="0" x2="640" y2="720" />
    <line x1="960" y1="0" x2="960" y2="720" />
  </g>

  <!-- Hairline Card Container -->
  <rect x="50" y="50" width="1180" height="620" rx="24" fill="#121214" fill-opacity="0.75" stroke="#26262b" stroke-width="2" />

  <!-- Variant Pill Badge (Top Left) -->
  <rect x="90" y="90" width="140" height="52" rx="26" fill="{accent_color}" fill-opacity="0.2" stroke="{accent_color}" stroke-width="2" />
  <text x="160" y="125" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" font-size="22" font-weight="900" fill="{accent_color}" text-anchor="middle" letter-spacing="2">VARIANT {variant}</text>

  <!-- Topic Tag Pill (Top Right) -->
  <rect x="1000" y="90" width="190" height="46" rx="23" fill="#202026" stroke="#33333d" stroke-width="1.5" />
  <text x="1095" y="120" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" font-size="18" font-weight="700" fill="#a0a0b0" text-anchor="middle" letter-spacing="1.5">{badge}</text>

  <!-- Visual Center Piece / Graphic Element -->
  <g transform="translate(640, 310)">
    <!-- Concentric accent arcs -->
    <circle cx="0" cy="0" r="140" fill="none" stroke="{accent_color}" stroke-width="4" stroke-dasharray="16 12" opacity="0.6" />
    <circle cx="0" cy="0" r="100" fill="#18181f" stroke="{accent_color}" stroke-width="3" />
    <circle cx="0" cy="0" r="45" fill="{accent_color}" opacity="0.85" />
    <text x="0" y="15" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" font-size="44" font-weight="900" fill="#000000" text-anchor="middle">{variant}</text>
  </g>

  <!-- Hero Typography Header -->
  <text x="640" y="520" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" font-size="54" font-weight="900" fill="#ffffff" text-anchor="middle" letter-spacing="-1">
    {title}
  </text>

  <!-- Subtitle Hook -->
  <text x="640" y="580" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" font-size="26" font-weight="600" fill="#9e9ea8" text-anchor="middle" letter-spacing="0.5">
    {subtitle}
  </text>

  <!-- Bottom Accent Bar -->
  <rect x="50" y="660" width="1180" height="10" rx="5" fill="{accent_color}" opacity="0.8" />
</svg>'''
    with open(filename, "w", encoding="utf-8", newline="\n") as f:
        f.write(svg_content)


challenges_data = []

for item in CHALLENGES_CONFIG:
    idx, title, cat, winner, rate_a, rate_b, n_a, n_b, var_a, var_b = item

    uuid_str = f"c1000000-0000-0000-0000-{idx:012d}"
    fn_a = f"challenge_{idx:02d}_a.svg"
    fn_b = f"challenge_{idx:02d}_b.svg"

    clicks_a = round(n_a * rate_a)
    clicks_b = round(n_b * rate_b)

    # Verify statistical significance
    gate = validate_significance_gate(n_a, clicks_a, n_b, clicks_b)
    if not gate.is_valid:
        raise ValueError(f"Challenge {idx} failed gate: {gate.rejection_reason}")

    # Generate SVGs
    path_a = static_thumb_dir / fn_a
    path_b = static_thumb_dir / fn_b

    generate_svg(str(path_a), var_a[0], var_a[1], var_a[2], var_a[3], var_a[4], "A")
    generate_svg(str(path_b), var_b[0], var_b[1], var_b[2], var_b[3], var_b[4], "B")

    challenges_data.append(
        {
            "id": uuid_str,
            "title": title,
            "category": "youtube_thumbnails",
            "thumbnail_a_url": f"/static/thumbnails/{fn_a}",
            "thumbnail_b_url": f"/static/thumbnails/{fn_b}",
            "impressions_a": n_a,
            "clicks_a": clicks_a,
            "impressions_b": n_b,
            "clicks_b": clicks_b,
            "provenance_source": f"Creator Studio A/B Benchmark #{idx:03d} (DEMO DATA)",
        }
    )

seed_file = data_dir / "seed_challenges.json"
with open(seed_file, "w", encoding="utf-8", newline="\n") as f:
    json.dump(challenges_data, f, indent=2)

print(f"Generated {len(challenges_data)} challenge items and 72 SVGs successfully.")
