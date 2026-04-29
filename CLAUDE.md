# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Essent Tea is an Argentine premium loose-leaf tea brand. This repo contains a multi-agent AI system (5 Claude agents) that personalizes product landing pages (PDPs) in real time to increase conversion, plus an optimizer that reads A/B test results and applies changes to the HTML.

## Running the System

```bash
# Full pipeline: simulate visitors → optimize → generate v2 landing
python run_full_system.py

# Just test/simulate visitor behavior on a landing
python landing_tester.py

# Just run the PDP personalization agents
python essent_tea_pdp.py

# Just run the optimizer (reads test_results.csv, outputs landing_v2.html)
python optimizer.py
```

Requires `ANTHROPIC_API_KEY` in the environment.

## Architecture

### Agent Pipeline (`essent_tea_pdp.py`)
Two-phase async pipeline using the Anthropic SDK:

- **Phase 1 (parallel):** Clasificador (segment: Explorador / Health / Regalero / Risk-Avoider / Leal) + Detector (price sensitivity, objections, buying intent)
- **Phase 2 (parallel):** Headlines agent + Reseñas agent + Experiencia agent

Output is a `pdp_config` dict passed to `landing_builder.renderizar_landing()`.

### Landing Generation (`landing_builder.py`)
- `generar_landing_html()` — returns the HTML template with `{PLACEHOLDER}` tokens
- `renderizar_landing(template, pdp_config)` — replaces placeholders with agent outputs
- `PLACEHOLDER_DEFAULTS` — fallback values for all tokens
- Product→image mapping: `coleccion_origenes_x3`, `blueberry_top`, `golden_harmony`, `enchanted_fruits` → `images/*.webp`

### Optimizer (`optimizer.py`)
Reads `test_results.csv` (5,000 simulated visits), calls Claude to generate strategic recommendations, and applies changes directly to the landing HTML. Outputs `landing_v2.html` and `reporte_cambios.json`.

### Landing Variants
- `landing_v1.html` — baseline with real product images
- `landing_v2.html` — optimizer output; currently uses emoji placeholders instead of real `<img>` tags (needs fix)

## Images
All product images live in `images/` as `.webp` files:
- `logoweb.webp` — brand logo (used in header + footer)
- `coleccion origenes.webp` — hero + product section for the kit
- `blueberry top.webp`, `golden harmony.webp`, `enchanted fruits.webp` — individual products

When `landing_v2.html` is regenerated, make sure `renderizar_landing()` is used (not a raw optimizer patch) so images are preserved.

## Key Data Files
- `test_results.csv` — simulated A/B test data (5,000 rows)
- `reporte_cambios.json` — optimizer output: applied changes + conversion projections (v1→v2)
- `comparativa.md` — human-readable v1 vs v2 comparison

## Products & Segments
Four products: Colección Orígenes x3 ($62.970), Blueberry Top ($38.900), Golden Harmony ($39.970), Enchanted Fruits ($30.970).

Five buyer segments: Explorador, Health, Regalero, Risk-Avoider, Leal — each with different copy, offers, and urgency levels.
