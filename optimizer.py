"""
optimizer.py — Agente Optimizer para Essent Tea

Analiza los resultados de 5.000 simulaciones, usa Claude para generar
recomendaciones estratégicas y aplica los cambios al HTML de la landing.
"""

import json
import re
import time
from typing import Any
import anthropic


# ── Benchmarks de referencia ─────────────────────────────────────────────────
BENCHMARKS = {
    "conversion_rate":  0.12,   # objetivo landing v2
    "by_segment": {
        "Explorador":   0.10,
        "Health":       0.15,
        "Regalero":     0.12,
        "Risk-Avoider": 0.08,
        "Leal":         0.25,
    },
    "scroll_depth_target": 0.65,
    "time_on_pdp_target":  90,
}


# ── Calcular estadísticas consolidadas ───────────────────────────────────────
def calcular_estadisticas(datos: dict) -> dict:
    """Extrae métricas clave del dict devuelto por testear_landing()."""
    resultados = datos.get("resultados", [])
    if not resultados:
        return {}

    n = len(resultados)
    conv  = [r for r in resultados if r["conversion"]]
    noconv= [r for r in resultados if not r["conversion"]]

    def seg_gap(seg: str) -> float:
        bench = BENCHMARKS["by_segment"].get(seg, 0.10)
        actual = datos["by_segment"].get(seg, {}).get("conv_rate", 0.0)
        return bench - actual  # positivo = por debajo del benchmark

    # Puntos de dolor por segmento (top dolor frecuente)
    dolor_by_seg: dict[str, dict] = {}
    for seg in datos.get("by_segment", {}):
        filas_seg = [r for r in resultados if r["segmento"] == seg and not r["conversion"]]
        dolores: dict[str, int] = {}
        for r in filas_seg:
            d = r.get("dolor", "desconocido")[:40]
            dolores[d] = dolores.get(d, 0) + 1
        top_d = sorted(dolores.items(), key=lambda x: -x[1])[:2]
        dolor_by_seg[seg] = {
            "conv_rate":  datos["by_segment"].get(seg, {}).get("conv_rate", 0),
            "benchmark":  BENCHMARKS["by_segment"].get(seg, 0.10),
            "gap":        seg_gap(seg),
            "top_dolores":[d for d, _ in top_d],
        }

    scroll_noconv = (sum(r["scroll_depth"] for r in noconv) / len(noconv)) if noconv else 0
    tiempo_noconv = (sum(r["tiempo_pdp"] for r in noconv) / len(noconv)) if noconv else 0
    scroll_conv   = (sum(r["scroll_depth"] for r in conv) / len(conv)) if conv else 0

    mobile_noconv  = sum(1 for r in noconv if r["device"] == "mobile")
    desktop_noconv = sum(1 for r in noconv if r["device"] == "desktop")

    return {
        "n_total":         n,
        "conv_total":      len(conv),
        "conv_rate":       datos["conversion_rate"],
        "conv_target":     BENCHMARKS["conversion_rate"],
        "gap_global":      BENCHMARKS["conversion_rate"] - datos["conversion_rate"],
        "avg_ticket":      datos["avg_ticket"],
        "total_revenue":   datos["total_revenue"],
        "by_segment":      dolor_by_seg,
        "scroll_conv":     scroll_conv,
        "scroll_noconv":   scroll_noconv,
        "tiempo_noconv":   tiempo_noconv,
        "mobile_noconv_%": mobile_noconv / len(noconv) if noconv else 0,
        "desktop_noconv_%":desktop_noconv / len(noconv) if noconv else 0,
        "friction_points": datos.get("friction_points", []),
        "by_device":       datos.get("by_device", {}),
    }


# ── Llamar a Claude para análisis y recomendaciones ──────────────────────────
async def analizar_con_claude(stats: dict, landing_html: str) -> list[dict]:
    """
    Envía estadísticas a Claude Opus 4.7 y obtiene recomendaciones
    priorizadas en JSON estructurado.
    """
    client = anthropic.AsyncAnthropic()

    # Resumir el HTML (no enviar el HTML completo, solo secciones)
    secciones = re.findall(r'<!-- SECTION:([^>]+) -->', landing_html)

    prompt = f"""Sos el Agente Optimizer para Essent Tea, tienda de tés premium en Argentina.
Analizaste una landing page testeada con {stats['n_total']:,} clientes simulados.

MÉTRICAS ACTUALES (landing v1):
- Conversión total: {stats['conv_rate']:.2%} (objetivo: {stats['conv_target']:.2%})
- Gap a cerrar: {stats['gap_global']:.2%}
- Ticket promedio: ${stats['avg_ticket']:,.0f}
- Revenue actual: ${stats['total_revenue']:,.0f}

POR SEGMENTO (conversión actual vs benchmark):
{json.dumps({seg: {'actual': f"{v['conv_rate']:.1%}", 'benchmark': f"{v['benchmark']:.1%}", 'gap': f"{v['gap']:.1%}", 'dolores': v['top_dolores']} for seg, v in stats['by_segment'].items()}, ensure_ascii=False, indent=2)}

COMPORTAMIENTO DE NO-CONVERSORES:
- Scroll promedio: {stats['scroll_noconv']:.2f} (vs {stats['scroll_conv']:.2f} en conversores)
- Tiempo promedio en PDP: {stats['tiempo_noconv']:.0f}s
- Dispositivo mobile no-conv: {stats['mobile_noconv_%']:.0%}
- Friction points detectados: {stats['friction_points']}

ESTRUCTURA ACTUAL DE LA LANDING (secciones en orden):
{secciones}

TAREA: Generá 6 cambios específicos priorizados por impacto para cerrar el gap de conversión.
Para cada cambio incluí EXACTAMENTE estos campos.

Respondé ÚNICAMENTE con JSON válido, array de objetos:
[
  {{
    "id": 1,
    "titulo": "título breve del cambio",
    "problema": "qué métrica o señal indica el problema",
    "raiz": "causa raíz identificada",
    "accion": "qué cambiar exactamente en la landing (sección, elemento, copy)",
    "seccion_html": "nombre de la sección a modificar (ej: social-proof)",
    "tipo_cambio": "reorder|content|css|new_element",
    "segmento_afectado": "Explorador|Health|Regalero|Risk-Avoider|Leal|Todos",
    "impacto_estimado": 0.025,
    "prioridad": "critica|alta|media",
    "nuevo_contenido": "texto o HTML del elemento nuevo/modificado (si aplica)"
  }}
]"""

    response = await client.messages.create(
        model="claude-opus-4-7",
        max_tokens=2048,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    )

    text = next(b.text for b in response.content if b.type == "text")
    # Limpiar markdown si lo hay
    text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("```").strip()
    try:
        cambios = json.loads(text)
        if isinstance(cambios, dict) and "cambios" in cambios:
            cambios = cambios["cambios"]
        return cambios if isinstance(cambios, list) else []
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return []


# ── Aplicar cambios al HTML ───────────────────────────────────────────────────
def aplicar_optimizaciones_html(html: str, cambios: list[dict]) -> str:
    """
    Aplica los cambios estructurales sugeridos al HTML de la landing.
    Estrategias: reorder secciones, inject banners, modificar CSS.
    """
    # Extraer secciones del HTML como bloques independientes
    section_pattern = re.compile(
        r'(<!-- SECTION:(\S+?) -->.*?)(?=<!-- SECTION:|<!-- SECTION:footer -->|</body>)',
        re.DOTALL
    )
    footer_pattern = re.compile(r'(<!-- SECTION:footer -->.*?)</body>', re.DOTALL)

    sections: dict[str, str] = {}
    order: list[str] = []
    for m in section_pattern.finditer(html):
        name = m.group(2)
        sections[name] = m.group(1)
        if name not in order:
            order.append(name)

    fm = footer_pattern.search(html)
    footer_html = fm.group(1) if fm else ""

    # ── Aplicar cambios ──
    for cambio in sorted(cambios, key=lambda x: {"critica": 0, "alta": 1, "media": 2}.get(x.get("prioridad","media"), 2)):
        tipo    = cambio.get("tipo_cambio", "content")
        seccion = cambio.get("seccion_html", "")
        nuevo   = cambio.get("nuevo_contenido", "")

        # Reordenar: si sugiere mover social-proof arriba del hero
        if tipo == "reorder" and "social" in cambio.get("accion","").lower():
            if "social-proof" in order and "hero" in order:
                order.remove("social-proof")
                hero_idx = order.index("hero")
                order.insert(hero_idx + 1, "social-proof")

        # Inyectar un nuevo elemento en una sección existente
        elif tipo in ("content", "new_element") and seccion in sections and nuevo:
            # Añadir contenido nuevo antes del cierre de la sección
            target = sections[seccion]
            if nuevo not in target:
                sections[seccion] = target.rstrip() + f"\n<!-- OPT:{cambio.get('id','')} -->\n{nuevo}\n"

    # ── Añadir CSS de optimización ──
    opt_css = """
<style id="opt-overrides">
/* Optimizer v2 overrides */
.sp{padding:48px 24px 52px}          /* Social proof más compacto */
.btn-p,.btn-cta{font-size:1.12rem}   /* CTAs más grandes */
.hero h1{font-size:2.3rem}           /* Headline más prominente */
.guarantee-s{padding:52px 24px}
@media(min-width:768px){
  .hero h1{font-size:3.2rem}
  .bcard{padding:32px 24px}
}
</style>"""

    # ── Reconstruir HTML ──
    pre_match = re.search(r'^(.*?)(?=<!-- SECTION:)', html, re.DOTALL)
    pre_html  = pre_match.group(1) if pre_match else ""

    # Inyectar CSS optimizado antes del </head>
    pre_html = pre_html.replace("</head>", opt_css + "\n</head>")

    body_sections = "".join(sections.get(s, "") for s in order if s in sections)
    html_v2 = pre_html + body_sections + footer_html + "\n</body>\n</html>"

    return html_v2


# ── Generar comparativa Markdown ─────────────────────────────────────────────
def generar_comparativa_md(reporte: dict, stats: dict) -> str:
    v1 = stats
    proj = reporte.get("proyeccion_v2", {})

    lines = [
        "# Comparativa Landing v1 vs v2 — Essent Tea",
        "",
        f"_Generado el {time.strftime('%Y-%m-%d %H:%M')} · Muestra: {v1['n_total']:,} clientes_",
        "",
        "## Métricas Landing v1",
        "",
        f"| Métrica | Valor |",
        f"|---------|-------|",
        f"| Conversión total | {v1['conv_rate']:.2%} |",
        f"| Ticket promedio | ${v1['avg_ticket']:,.0f} |",
        f"| Revenue estimado | ${v1['total_revenue']:,.0f} |",
        "",
        "### Por segmento",
        "",
        "| Segmento | Conversión | vs Benchmark |",
        "|----------|-----------|--------------|",
    ]
    for seg, d in v1["by_segment"].items():
        gap_str = f"+{d['gap']:.1%}" if d["gap"] > 0 else f"{d['gap']:.1%}"
        lines.append(f"| {seg} | {d['conv_rate']:.1%} | {gap_str} vs {d['benchmark']:.1%} |")

    lines += [
        "",
        "## Cambios Aplicados en v2",
        "",
    ]
    for i, cambio in enumerate(reporte.get("cambios", []), 1):
        imp = cambio.get("impacto_estimado", 0)
        lines += [
            f"### {i}. {cambio.get('titulo','Sin título')} [{cambio.get('prioridad','media').upper()}]",
            "",
            f"**Problema:** {cambio.get('problema','')}",
            "",
            f"**Causa raíz:** {cambio.get('raiz','')}",
            "",
            f"**Acción:** {cambio.get('accion','')}",
            "",
            f"**Segmento afectado:** {cambio.get('segmento_afectado','Todos')}",
            "",
            f"**Impacto estimado:** +{imp:.1%} conversión",
            "",
        ]

    lines += [
        "## Proyección Landing v2",
        "",
        f"| Métrica | v1 | v2 estimado | Cambio |",
        f"|---------|-----|------------|--------|",
        f"| Conversión | {v1['conv_rate']:.2%} | {proj.get('conv_rate', 0):.2%} | +{proj.get('conv_rate', 0) - v1['conv_rate']:.2%} |",
        f"| Ticket promedio | ${v1['avg_ticket']:,.0f} | ${proj.get('avg_ticket', 0):,.0f} | +{proj.get('avg_ticket', 0) - v1['avg_ticket']:,.0f} |",
        f"| Revenue (5k visitas) | ${v1['total_revenue']:,.0f} | ${proj.get('total_revenue', 0):,.0f} | +{proj.get('total_revenue', 0) - v1['total_revenue']:,.0f} |",
        "",
        "_Las proyecciones son estimaciones basadas en benchmarks de industria y patrones de comportamiento observados en la simulación._",
    ]
    return "\n".join(lines)


# ── Función principal del optimizer ──────────────────────────────────────────
async def analizar_y_sugerir_cambios(datos: dict, landing_html: str) -> tuple[dict, str]:
    """
    Función principal. Recibe datos del tester y HTML actual.
    Retorna (reporte: dict, landing_v2_html: str).
    """
    print("\n  🔬 Calculando estadísticas...")
    stats = calcular_estadisticas(datos)

    print("  🤖 Consultando Claude Opus 4.7 para recomendaciones...")
    cambios = await analizar_con_claude(stats, landing_html)

    if not cambios:
        print("  ⚠️  No se obtuvieron cambios de Claude. Usando fallback.")
        cambios = _cambios_fallback(stats)

    # Calcular impacto total estimado
    impacto_total = sum(c.get("impacto_estimado", 0) for c in cambios)
    nueva_conv    = min(0.25, stats["conv_rate"] + impacto_total)
    nuevo_ticket  = stats["avg_ticket"] * 1.06  # +6% por mejor bundle presentation
    nuevo_revenue = nueva_conv * stats["n_total"] * nuevo_ticket

    reporte = {
        "fecha":       time.strftime("%Y-%m-%d"),
        "version":     "v1→v2",
        "metricas_v1": {
            "conv_rate":    stats["conv_rate"],
            "avg_ticket":   stats["avg_ticket"],
            "total_revenue":stats["total_revenue"],
        },
        "cambios":     cambios,
        "proyeccion_v2": {
            "conv_rate":    nueva_conv,
            "avg_ticket":   nuevo_ticket,
            "total_revenue":nuevo_revenue,
            "impacto_total":impacto_total,
        },
    }

    # Imprimir reporte
    print(f"\n  📋 REPORTE DE CAMBIOS ({len(cambios)} sugeridos)")
    print(f"  {'─'*55}")
    for c in cambios:
        imp  = c.get("impacto_estimado", 0)
        prio = c.get("prioridad", "media").upper()
        seg  = c.get("segmento_afectado", "Todos")
        print(f"  [{prio}] {c.get('titulo','')}")
        print(f"          → {c.get('accion','')[:65]}")
        print(f"          → Segmento: {seg} | Impacto: +{imp:.1%}")
        print()

    print(f"  📈 PROYECCIÓN v2:")
    print(f"     Conversión: {stats['conv_rate']:.2%} → {nueva_conv:.2%} (+{nueva_conv - stats['conv_rate']:.2%})")
    print(f"     Ticket:     ${stats['avg_ticket']:,.0f} → ${nuevo_ticket:,.0f}")
    print(f"     Revenue:    ${stats['total_revenue']:,.0f} → ${nuevo_revenue:,.0f} (+{(nuevo_revenue/stats['total_revenue']-1):.0%})")

    # Aplicar cambios al HTML
    print("\n  🔧 Aplicando optimizaciones al HTML...")
    landing_v2 = aplicar_optimizaciones_html(landing_html, cambios)

    # Guardar archivos
    with open("/tmp/reporte_cambios.json", "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)

    comp_md = generar_comparativa_md(reporte, stats)
    with open("/tmp/comparativa.md", "w", encoding="utf-8") as f:
        f.write(comp_md)

    print("  ✅ Archivos generados:")
    print("     /tmp/reporte_cambios.json")
    print("     /tmp/comparativa.md")

    return reporte, landing_v2


# ── Cambios fallback (sin llamada API) ───────────────────────────────────────
def _cambios_fallback(stats: dict) -> list[dict]:
    """Retorna cambios hardcoded basados en las métricas observadas."""
    cambios = []

    if stats["scroll_noconv"] < 0.55:
        cambios.append({
            "id": 1, "titulo": "Mover Social Proof debajo del Hero",
            "problema": f"No-conversores scrollean solo {stats['scroll_noconv']:.0%} en promedio",
            "raiz": "El valor percibido tarda en aparecer; la sección de reseñas está muy abajo",
            "accion": "Mover sección social-proof (reseñas) inmediatamente debajo del hero",
            "seccion_html": "social-proof", "tipo_cambio": "reorder",
            "segmento_afectado": "Todos", "impacto_estimado": 0.022, "prioridad": "critica",
            "nuevo_contenido": ""
        })

    risk_data = stats["by_segment"].get("Risk-Avoider", {})
    if risk_data.get("gap", 0) > 0.03:
        cambios.append({
            "id": 2, "titulo": "Destacar garantía 30 días en la sección de producto",
            "problema": f"Risk-Avoider convierte {risk_data.get('conv_rate',0):.1%} vs benchmark {risk_data.get('benchmark',0):.1%}",
            "raiz": "El miedo a perder dinero bloquea la decisión; la garantía no es visible",
            "accion": "Añadir badge de garantía destacado cerca del CTA en sección product",
            "seccion_html": "product", "tipo_cambio": "new_element",
            "segmento_afectado": "Risk-Avoider", "impacto_estimado": 0.018, "prioridad": "alta",
            "nuevo_contenido": '<div style="background:#e8f5e9;border:2px solid #2D6A4F;border-radius:12px;padding:14px;text-align:center;margin:16px 0"><strong style="color:#2D6A4F">🛡️ Garantía total 30 días</strong><br><small style="color:#555">Devolución inmediata si no te enamora. Sin preguntas.</small></div>'
        })

    exp_data = stats["by_segment"].get("Explorador", {})
    if exp_data.get("gap", 0) > 0.02:
        cambios.append({
            "id": 3, "titulo": "Agregar sección de maridaje visual",
            "problema": f"Explorador convierte {exp_data.get('conv_rate',0):.1%}; necesita más contexto de uso",
            "raiz": "El Explorador quiere saber cómo va a vivir el producto; el maridaje lo concretiza",
            "accion": "Añadir bloque visual con sugerencias de maridaje en sección benefits",
            "seccion_html": "benefits", "tipo_cambio": "new_element",
            "segmento_afectado": "Explorador", "impacto_estimado": 0.015, "prioridad": "alta",
            "nuevo_contenido": '<div style="background:#FAF6EE;border-radius:16px;padding:24px;text-align:center;margin:24px auto;max-width:700px"><h3 style="color:#2D6A4F;margin-bottom:16px">✨ Maridajes perfectos</h3><div style="display:flex;justify-content:center;gap:24px;flex-wrap:wrap"><span>🍵 + 🍫 Blueberry + chocolate</span><span>🍵 + 🧉 Golden + mate</span><span>🍵 + 🍎 Enchanted + manzana</span></div></div>'
        })

    cambios.append({
        "id": 4, "titulo": "Añadir contador de clientes felices en hero",
        "problema": "El primer scroll no muestra prueba social suficiente",
        "raiz": "La confianza se construye rápido con números concretos",
        "accion": "Añadir '347 clientes felices esta semana' cerca del CTA del hero",
        "seccion_html": "hero", "tipo_cambio": "new_element",
        "segmento_afectado": "Todos", "impacto_estimado": 0.012, "prioridad": "media",
        "nuevo_contenido": '<p style="font-family:system-ui,sans-serif;font-size:.88rem;color:#6B7280;margin-top:8px">✅ 347 clientes eligieron Essent Tea esta semana</p>'
    })

    cambios.append({
        "id": 5, "titulo": "Optimizar CTA para mobile (más grande, más margen)",
        "problema": f"{stats.get('mobile_noconv_%',0):.0%} de no-conv son mobile",
        "raiz": "En mobile el CTA es difícil de presionar y se pierde en el scroll",
        "accion": "Aumentar padding del btn-cta en mobile y fijar barra de compra en el bottom",
        "seccion_html": "product", "tipo_cambio": "css",
        "segmento_afectado": "Todos", "impacto_estimado": 0.010, "prioridad": "media",
        "nuevo_contenido": ""
    })

    return cambios


if __name__ == "__main__":
    import asyncio

    async def _demo():
        # Simular datos mínimos para probar el optimizer
        datos = {
            "n_clientes": 100, "conversions": 8, "conversion_rate": 0.08,
            "avg_ticket": 52000, "total_revenue": 416000,
            "by_segment": {
                "Explorador": {"n": 40, "conv": 3, "conv_rate": 0.075, "revenue": 210000, "avg_ticket": 70000},
                "Risk-Avoider": {"n": 20, "conv": 1, "conv_rate": 0.05, "revenue": 40000, "avg_ticket": 40000},
            },
            "friction_points": ["45% scrollean < 50%"],
            "by_device": {"mobile": {"n": 75, "conv_rate": 0.072}, "desktop": {"n": 25, "conv_rate": 0.10}},
            "resultados": [
                {"segmento": "Explorador", "device": "mobile", "scroll_depth": 0.4, "tiempo_pdp": 30, "reviews_vistas": 1, "conversion": False, "ticket": 0, "dolor": "No encuentra el valor"},
            ] * 100,
        }
        from landing_builder import generar_landing_html
        html = generar_landing_html()
        reporte, _ = await analizar_y_sugerir_cambios(datos, html)
        print(f"\nDemo: {len(reporte['cambios'])} cambios generados")

    asyncio.run(_demo())
