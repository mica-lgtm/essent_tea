"""
run_full_system.py — Orquestador del sistema completo Essent Tea

Ejecuta en secuencia:
  1. Landing Builder   → genera landing_v1.html con todos los placeholders
  2. Landing Tester    → simula 5.000 clientes (20 agentes reales + conversión simulada)
  3. Agente Optimizer  → analiza y genera landing_v2.html con cambios priorizados
"""

import asyncio
import json
import os
import sys
import time

sys.path.insert(0, "/tmp")

from landing_builder import generar_landing_html, PLACEHOLDER_DEFAULTS
from landing_tester import testear_landing
from optimizer import analizar_y_sugerir_cambios


async def main(n_clientes: int = 5000):
    print("\n" + "═" * 62)
    print("  🍃 ESSENT TEA — Sistema Completo de Landing con IA")
    print("  5 Agentes · Personalización · Simulación · Optimización")
    print("═" * 62)

    # ── Verificar API Key ─────────────────────────────────────────────────────
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n  ❌ Error: ANTHROPIC_API_KEY no está en el entorno.")
        print("  Ejecutá: export ANTHROPIC_API_KEY='tu-api-key'")
        sys.exit(1)

    total_start = time.time()

    # ══════════════════════════════════════════════════════════════════════════
    # PASO 1: GENERAR LANDING v1
    # ══════════════════════════════════════════════════════════════════════════
    print("\n1️⃣  LANDING BUILDER — Generando landing con placeholders")
    print("─" * 62)
    t1 = time.time()

    html_template = generar_landing_html()

    # Versión con defaults (para preview visual sin agentes)
    html_preview = html_template
    for ph, val in PLACEHOLDER_DEFAULTS.items():
        html_preview = html_preview.replace(ph, val)

    with open("/tmp/landing_v1.html", "w", encoding="utf-8") as f:
        f.write(html_preview)

    print(f"  ✅ landing_v1.html generada ({len(html_preview):,} caracteres)")
    print(f"     Secciones: header, hero, social-proof, benefits, product, faq,")
    print(f"                testimonials, guarantee, footer")
    print(f"     Placeholders: HEADLINE, SUBHEADER, CTA_TEXT, FEATURED_REVIEW,")
    print(f"                   PRECIO, STOCK_LABEL, BUNDLE, CTA_BUTTON, MARIDAJE")
    print(f"     Tiempo: {time.time()-t1:.1f}s")

    # ══════════════════════════════════════════════════════════════════════════
    # PASO 2: TESTEAR CON CLIENTES SIMULADOS
    # ══════════════════════════════════════════════════════════════════════════
    print(f"\n2️⃣  LANDING TESTER — Simulando {n_clientes:,} clientes")
    print("─" * 62)
    print(f"  Arquitectura:")
    print(f"    • Fase A: 5 agentes Claude corren para 20 arquetipos reales (paralelo)")
    print(f"    • Fase B: resultados cacheados → aplican a {n_clientes:,} clientes simulados")
    print(f"    • Conversión: modelo probabilístico calibrado por segmento")
    t2 = time.time()

    datos = await testear_landing(html_template, n_clientes=n_clientes)

    print(f"\n  ⏱️  Tiempo de testing: {time.time()-t2:.1f}s")

    # ══════════════════════════════════════════════════════════════════════════
    # PASO 3: AGENTE OPTIMIZER
    # ══════════════════════════════════════════════════════════════════════════
    print(f"\n3️⃣  AGENTE OPTIMIZER — Análisis y optimización")
    print("─" * 62)
    t3 = time.time()

    reporte, landing_v2 = await analizar_y_sugerir_cambios(datos, html_preview)

    with open("/tmp/landing_v2.html", "w", encoding="utf-8") as f:
        f.write(landing_v2)

    print(f"\n  ✅ landing_v2.html guardada ({len(landing_v2):,} caracteres)")
    print(f"  ⏱️  Tiempo de optimización: {time.time()-t3:.1f}s")

    # ══════════════════════════════════════════════════════════════════════════
    # RESUMEN FINAL
    # ══════════════════════════════════════════════════════════════════════════
    total_time = time.time() - total_start
    v1 = reporte.get("metricas_v1", {})
    v2 = reporte.get("proyeccion_v2", {})
    n_cambios = len(reporte.get("cambios", []))

    print("\n" + "═" * 62)
    print("  ✅ SISTEMA COMPLETADO — LISTO PARA PAUTAJE")
    print("═" * 62)

    print(f"""
  📊 COMPARATIVA LANDING v1 vs v2:
  ┌─────────────────────┬───────────────┬───────────────┐
  │ Métrica             │ Landing v1    │ Landing v2 *  │
  ├─────────────────────┼───────────────┼───────────────┤
  │ Conversión          │ {v1.get('conv_rate',0):.2%}         │ {v2.get('conv_rate',0):.2%} (+{v2.get('conv_rate',0)-v1.get('conv_rate',0):.2%})   │
  │ Ticket promedio     │ ${v1.get('avg_ticket',0):>11,.0f} │ ${v2.get('avg_ticket',0):>11,.0f} │
  │ Revenue ({n_clientes/1000:.0f}k visitas)│ ${v1.get('total_revenue',0):>11,.0f} │ ${v2.get('total_revenue',0):>11,.0f} │
  └─────────────────────┴───────────────┴───────────────┘
  * Proyección estimada basada en {n_cambios} cambios aplicados

  📁 ARCHIVOS GENERADOS:
     /tmp/landing_v1.html      — Landing original (con defaults)
     /tmp/landing_v2.html      — Landing optimizada
     /tmp/test_results.csv     — {n_clientes:,} clientes simulados (datos completos)
     /tmp/reporte_cambios.json — {n_cambios} cambios con impacto y prioridad
     /tmp/comparativa.md       — Análisis antes/después

  ⏱️  Tiempo total: {total_time:.0f}s
""")

    print("  💡 PRÓXIMOS PASOS:")
    print("     1. Abrir /tmp/landing_v2.html en el browser para revisar")
    print("     2. Integrar generate_pdp() en el webhook de Tienda Nube")
    print("     3. Usar reporte_cambios.json para priorizar el sprint de desarrollo")
    print("     4. Configurar Meta Pixel en el <head> antes de pautar")
    print()

    return reporte


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sistema completo Essent Tea")
    parser.add_argument("--clientes", type=int, default=5000,
                        help="Cantidad de clientes a simular (default: 5000)")
    args = parser.parse_args()

    asyncio.run(main(n_clientes=args.clientes))
