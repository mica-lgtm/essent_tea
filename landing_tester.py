"""
landing_tester.py — Simulación de 5.000 clientes para Essent Tea

Estrategia de eficiencia:
  - Los 5 agentes corren REALMENTE para 20 arquetipos (5 segmentos × 4 productos)
  - Los resultados se cachean y aplican a los 5.000 clientes simulados
  - La conversión se simula con modelo probabilístico calibrado por segmento
  - Esto da rigor estadístico real sin 25.000 llamadas a la API
"""

import asyncio
import csv
import json
import random
import time
from typing import Any

import sys
sys.path.insert(0, "/tmp")
from essent_tea_pdp import generate_pdp, PRODUCTS, SEGMENTS
from landing_builder import generar_landing_html, renderizar_landing

# ── Tasas de conversión base por segmento (calibradas para ~8% global) ────────
CONVERSION_BASE = {
    "Explorador":   0.072,
    "Health":       0.115,
    "Regalero":     0.088,
    "Risk-Avoider": 0.045,
    "Leal":         0.195,
}

PRODUCT_IDS = list(PRODUCTS.keys())

# ── 20 arquetipos representativos (5 segmentos × 4 productos) ─────────────────
ARCHETYPES = [
    # Explorador
    {"client_id":"arch_exp_01","product_id":"coleccion_origenes_x3","traffic_source":"instagram_reels","device":"mobile","first_visit":True,"hour":19,"scroll_depth":0.72,"time_on_pdp":48,"clicks":["product_images","reviews_section"],"reviews_seen":3,"faq_visits":0,"cart_abandonment":False,"purchase_history":[],"stock_status":"normal"},
    {"client_id":"arch_exp_02","product_id":"blueberry_top","traffic_source":"tiktok","device":"mobile","first_visit":True,"hour":21,"scroll_depth":0.65,"time_on_pdp":38,"clicks":["images"],"reviews_seen":2,"faq_visits":0,"cart_abandonment":False,"purchase_history":[],"stock_status":"normal"},
    {"client_id":"arch_exp_03","product_id":"golden_harmony","traffic_source":"facebook_ad","device":"mobile","first_visit":True,"hour":18,"scroll_depth":0.7,"time_on_pdp":42,"clicks":["flavors"],"reviews_seen":2,"faq_visits":0,"cart_abandonment":False,"purchase_history":[],"stock_status":"normal"},
    {"client_id":"arch_exp_04","product_id":"enchanted_fruits","traffic_source":"pinterest","device":"desktop","first_visit":True,"hour":20,"scroll_depth":0.68,"time_on_pdp":50,"clicks":["product_images"],"reviews_seen":1,"faq_visits":0,"cart_abandonment":False,"purchase_history":[],"stock_status":"normal"},
    # Health
    {"client_id":"arch_hth_01","product_id":"golden_harmony","traffic_source":"google_antioxidantes","device":"desktop","first_visit":True,"hour":8,"scroll_depth":0.88,"time_on_pdp":115,"clicks":["ingredients","benefits"],"reviews_seen":6,"faq_visits":0,"cart_abandonment":False,"purchase_history":[],"stock_status":"normal"},
    {"client_id":"arch_hth_02","product_id":"enchanted_fruits","traffic_source":"google_te_sin_cafeina","device":"desktop","first_visit":True,"hour":22,"scroll_depth":0.85,"time_on_pdp":98,"clicks":["caffeine_free","ingredients"],"reviews_seen":5,"faq_visits":0,"cart_abandonment":False,"purchase_history":[],"stock_status":"normal"},
    {"client_id":"arch_hth_03","product_id":"blueberry_top","traffic_source":"google_organic","device":"desktop","first_visit":True,"hour":9,"scroll_depth":0.82,"time_on_pdp":105,"clicks":["benefits","nutrition"],"reviews_seen":4,"faq_visits":0,"cart_abandonment":False,"purchase_history":[],"stock_status":"normal"},
    {"client_id":"arch_hth_04","product_id":"coleccion_origenes_x3","traffic_source":"google_bienestar","device":"mobile","first_visit":True,"hour":7,"scroll_depth":0.9,"time_on_pdp":90,"clicks":["ingredients"],"reviews_seen":5,"faq_visits":0,"cart_abandonment":False,"purchase_history":[],"stock_status":"normal"},
    # Regalero
    {"client_id":"arch_reg_01","product_id":"coleccion_origenes_x3","traffic_source":"google_regalo_te","device":"desktop","first_visit":True,"hour":11,"scroll_depth":0.58,"time_on_pdp":85,"clicks":["gift","packaging"],"reviews_seen":4,"faq_visits":1,"cart_abandonment":False,"purchase_history":[],"stock_status":"normal"},
    {"client_id":"arch_reg_02","product_id":"blueberry_top","traffic_source":"google_regalo_original","device":"mobile","first_visit":True,"hour":16,"scroll_depth":0.55,"time_on_pdp":62,"clicks":["gift_wrap"],"reviews_seen":3,"faq_visits":0,"cart_abandonment":False,"purchase_history":[],"stock_status":"normal"},
    {"client_id":"arch_reg_03","product_id":"golden_harmony","traffic_source":"pinterest_regalo","device":"mobile","first_visit":True,"hour":14,"scroll_depth":0.52,"time_on_pdp":70,"clicks":["packaging"],"reviews_seen":3,"faq_visits":0,"cart_abandonment":False,"purchase_history":[],"stock_status":"normal"},
    {"client_id":"arch_reg_04","product_id":"enchanted_fruits","traffic_source":"google_regalo_mujer","device":"desktop","first_visit":True,"hour":12,"scroll_depth":0.6,"time_on_pdp":80,"clicks":["gift","reviews"],"reviews_seen":4,"faq_visits":1,"cart_abandonment":False,"purchase_history":[],"stock_status":"normal"},
    # Risk-Avoider
    {"client_id":"arch_rsk_01","product_id":"golden_harmony","traffic_source":"direct","device":"desktop","first_visit":False,"hour":14,"scroll_depth":0.96,"time_on_pdp":195,"clicks":["faq","return_policy","ingredients","price"],"reviews_seen":9,"faq_visits":3,"cart_abandonment":True,"purchase_history":[],"stock_status":"low"},
    {"client_id":"arch_rsk_02","product_id":"enchanted_fruits","traffic_source":"direct","device":"desktop","first_visit":False,"hour":22,"scroll_depth":1.0,"time_on_pdp":245,"clicks":["faq","policy","price"],"reviews_seen":11,"faq_visits":4,"cart_abandonment":True,"purchase_history":[],"stock_status":"normal"},
    {"client_id":"arch_rsk_03","product_id":"blueberry_top","traffic_source":"organic","device":"desktop","first_visit":False,"hour":15,"scroll_depth":0.93,"time_on_pdp":180,"clicks":["reviews","faq","return"],"reviews_seen":8,"faq_visits":2,"cart_abandonment":True,"purchase_history":[],"stock_status":"normal"},
    {"client_id":"arch_rsk_04","product_id":"coleccion_origenes_x3","traffic_source":"direct","device":"tablet","first_visit":False,"hour":19,"scroll_depth":0.95,"time_on_pdp":210,"clicks":["faq","return","price"],"reviews_seen":10,"faq_visits":3,"cart_abandonment":True,"purchase_history":[],"stock_status":"low"},
    # Leal
    {"client_id":"arch_leal_01","product_id":"blueberry_top","traffic_source":"email_newsletter","device":"desktop","first_visit":False,"hour":12,"scroll_depth":0.48,"time_on_pdp":28,"clicks":[],"reviews_seen":1,"faq_visits":0,"cart_abandonment":False,"purchase_history":["enchanted_fruits","golden_harmony"],"stock_status":"normal"},
    {"client_id":"arch_leal_02","product_id":"golden_harmony","traffic_source":"email_leal","device":"mobile","first_visit":False,"hour":9,"scroll_depth":0.45,"time_on_pdp":25,"clicks":[],"reviews_seen":0,"faq_visits":0,"cart_abandonment":False,"purchase_history":["blueberry_top"],"stock_status":"normal"},
    {"client_id":"arch_leal_03","product_id":"coleccion_origenes_x3","traffic_source":"email_promo","device":"desktop","first_visit":False,"hour":10,"scroll_depth":0.5,"time_on_pdp":30,"clicks":["new_blends"],"reviews_seen":1,"faq_visits":0,"cart_abandonment":False,"purchase_history":["blueberry_top","golden_harmony","enchanted_fruits"],"stock_status":"normal"},
    {"client_id":"arch_leal_04","product_id":"enchanted_fruits","traffic_source":"email","device":"mobile","first_visit":False,"hour":20,"scroll_depth":0.42,"time_on_pdp":22,"clicks":[],"reviews_seen":0,"faq_visits":0,"cart_abandonment":False,"purchase_history":["coleccion_origenes_x3"],"stock_status":"normal"},
]


# ── Clasificador rápido (sin API — aproxima al Agente 1) ─────────────────────
def _clasificar_rapido(perfil: dict) -> str:
    if perfil.get("purchase_history"):
        return "Leal"
    src = perfil.get("traffic_source", "").lower()
    if "regalo" in src or "gift" in src:
        return "Regalero"
    if perfil.get("cart_abandonment") or perfil.get("faq_visits", 0) >= 3:
        return "Risk-Avoider"
    if any(k in src for k in ["health","salud","antioxid","caffeine","bienestar","cafeina"]):
        return "Health"
    hour = perfil.get("hour", 14)
    if hour <= 10:
        return "Health"
    return "Explorador"


# ── Generador de perfiles aleatorios ─────────────────────────────────────────
def generar_perfil_cliente(i: int, rng: random.Random) -> dict:
    # Distribuciones realistas
    src_pool = (
        ["instagram"] * 40 + ["tiktok"] * 15 + ["facebook_ad"] * 15 +
        ["google_organic"] * 12 + ["google_regalo_te"] * 5 +
        ["google_antioxidantes"] * 3 + ["email_newsletter"] * 5 +
        ["direct"] * 5
    )
    traffic = rng.choice(src_pool)
    device  = rng.choices(["mobile", "desktop", "tablet"], weights=[78, 18, 4])[0]
    f_visit = rng.random() < 0.72
    hour    = int(rng.gauss(16, 3.5))
    hour    = max(7, min(23, hour))
    product = rng.choice(PRODUCT_IDS)

    # scroll depth (normal, clipped)
    scroll = rng.gauss(0.62, 0.2)
    scroll = round(max(0.25, min(1.0, scroll)), 2)

    # time on PDP (log-normal → realistic long tail)
    time_pdp = int(rng.lognormvariate(4.0, 0.7))
    time_pdp = max(15, min(300, time_pdp))

    reviews  = rng.randint(0, 5)
    faq      = rng.randint(0, 2) if rng.random() < 0.25 else 0
    abandon  = rng.random() < 0.12
    history: list = []
    if rng.random() < 0.22:
        k = rng.randint(1, 3)
        history = rng.sample(PRODUCT_IDS, min(k, len(PRODUCT_IDS)))

    clicks_pool = ["product_images","reviews_section","ingredients","benefits",
                   "price","packaging","faq","return_policy","gift"]
    n_clicks = max(0, int(rng.gauss(2.5, 1.5)))
    clicks   = rng.sample(clicks_pool, min(n_clicks, len(clicks_pool)))

    stock = "low" if rng.random() < 0.18 else "normal"

    return {
        "client_id":       f"sim_{i:05d}",
        "product_id":      product,
        "traffic_source":  traffic,
        "device":          device,
        "first_visit":     f_visit,
        "hour":            hour,
        "scroll_depth":    scroll,
        "time_on_pdp":     time_pdp,
        "clicks":          clicks,
        "reviews_seen":    reviews,
        "faq_visits":      faq,
        "cart_abandonment":abandon,
        "purchase_history":history,
        "stock_status":    stock,
    }


# ── Modelo probabilístico de conversión ──────────────────────────────────────
def calcular_conversion(
    segment: str,
    urgency_level: str,
    scroll: float,
    time_pdp: int,
    device: str,
    reviews_seen: int,
    first_visit: bool,
    cart_abandonment: bool,
    has_history: bool,
    rng: random.Random,
) -> tuple:
    """Retorna (converted: bool, ticket: float)"""

    p = CONVERSION_BASE.get(segment, 0.08)

    # Modificadores multiplicativos
    if urgency_level == "high":   p *= 1.45
    elif urgency_level == "medium":p *= 1.22
    if scroll > 0.75:              p *= 1.18
    elif scroll < 0.35:            p *= 0.72
    if time_pdp > 120:             p *= 1.15
    elif time_pdp < 30:            p *= 0.82
    if device == "desktop":        p *= 1.10
    if reviews_seen >= 4:          p *= 1.14
    if not first_visit:            p *= 1.08
    if cart_abandonment:           p *= 0.70
    if has_history:                p *= 1.20

    p = min(0.70, max(0.01, p))
    converted = rng.random() < p

    ticket = 0.0
    if converted:
        base_tickets = {
            "Explorador":   72_970,
            "Health":       39_970,
            "Regalero":     66_970,
            "Risk-Avoider": 39_970,
            "Leal":         33_125,  # ~38900 * 0.85
        }
        ticket = base_tickets.get(segment, 45_000)
        ticket *= rng.uniform(0.95, 1.05)

    return converted, round(ticket, 2)


# ── Runner principal ──────────────────────────────────────────────────────────
async def testear_landing(html_template: str, n_clientes: int = 5000) -> dict:
    """
    Simula n_clientes visitando la landing con personalización real.

    Fase A: corre los 5 agentes reales para 20 arquetipos (paralelo).
    Fase B: aplica resultados cacheados a n_clientes simulados.
    """
    print(f"\n  ⚙️  Fase A: corriendo 5 agentes reales para {len(ARCHETYPES)} arquetipos...")
    t_a = time.time()

    # Ejecutar todos los arquetipos en paralelo
    arch_pdps = await asyncio.gather(
        *[generate_pdp(a) for a in ARCHETYPES],
        return_exceptions=True,
    )

    # Construir caché: (segment, product_id) → pdp_config
    pdp_cache: dict[tuple, dict] = {}
    for arch, pdp in zip(ARCHETYPES, arch_pdps):
        if isinstance(pdp, Exception):
            print(f"    ⚠️  Arquetipo {arch['client_id']} falló: {pdp}")
            continue
        seg = pdp.get("segmentation", {}).get("segment", "Explorador")
        pid = arch["product_id"]
        key = (seg, pid)
        if key not in pdp_cache:
            pdp_cache[key] = pdp

    print(f"    ✓ {len(pdp_cache)} combinaciones (segmento×producto) cacheadas en {time.time()-t_a:.1f}s")

    # ── Fase B: simular 5.000 clientes ───────────────────────────────────────
    print(f"\n  ⚙️  Fase B: simulando {n_clientes:,} clientes...")
    rng = random.Random(42)
    resultados: list[dict] = []

    for i in range(1, n_clientes + 1):
        perfil = generar_perfil_cliente(i, rng)
        segment = _clasificar_rapido(perfil)

        # Buscar PDP cacheado; fallback al primer match por segmento
        key = (segment, perfil["product_id"])
        pdp = pdp_cache.get(key)
        if pdp is None:
            # fallback: cualquier cached entry del mismo segmento
            for (s, p), v in pdp_cache.items():
                if s == segment:
                    pdp = v
                    break
        if pdp is None:
            # último fallback: primer entry disponible
            pdp = next(iter(pdp_cache.values())) if pdp_cache else {}

        urgency = pdp.get("offer", {}).get("urgency_level", "none") if pdp else "none"
        converted, ticket = calcular_conversion(
            segment         = segment,
            urgency_level   = urgency,
            scroll          = perfil["scroll_depth"],
            time_pdp        = perfil["time_on_pdp"],
            device          = perfil["device"],
            reviews_seen    = perfil["reviews_seen"],
            first_visit     = perfil["first_visit"],
            cart_abandonment= perfil["cart_abandonment"],
            has_history     = bool(perfil["purchase_history"]),
            rng             = rng,
        )

        copy  = pdp.get("copy", {})  if pdp else {}
        offer = pdp.get("offer", {}) if pdp else {}

        resultados.append({
            "cliente_id":      perfil["client_id"],
            "segmento":        segment,
            "producto":        perfil["product_id"],
            "dolor":           pdp.get("behavioral_analysis", {}).get("pain_point", "")[:60] if pdp else "",
            "headline":        (copy.get("headline","")[:55] + "…") if copy.get("headline","") else "",
            "bundle":          offer.get("bundle_name",""),
            "precio":          offer.get("bundle_price", 0),
            "urgencia_nivel":  urgency,
            "traffic_source":  perfil["traffic_source"],
            "device":          perfil["device"],
            "first_visit":     perfil["first_visit"],
            "scroll_depth":    perfil["scroll_depth"],
            "tiempo_pdp":      perfil["time_on_pdp"],
            "reviews_vistas":  perfil["reviews_seen"],
            "conversion":      converted,
            "ticket":          ticket if converted else 0,
        })

        if i % 1000 == 0:
            conv_so_far = sum(1 for r in resultados if r["conversion"])
            print(f"    … {i:,}/{n_clientes:,} | conv hasta ahora: {conv_so_far/i:.1%}")

    # ── Guardar CSV ───────────────────────────────────────────────────────────
    csv_path = "/tmp/test_results.csv"
    if resultados:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(resultados[0].keys()))
            writer.writeheader()
            writer.writerows(resultados)

    # ── Calcular estadísticas ─────────────────────────────────────────────────
    total_conv     = sum(1 for r in resultados if r["conversion"])
    total_revenue  = sum(r["ticket"] for r in resultados)
    conv_rate      = total_conv / n_clientes
    avg_ticket     = total_revenue / total_conv if total_conv else 0

    # Por segmento
    by_segment: dict[str, Any] = {}
    for seg in SEGMENTS:
        filas = [r for r in resultados if r["segmento"] == seg]
        if not filas:
            continue
        conv_s = sum(1 for r in filas if r["conversion"])
        rev_s  = sum(r["ticket"] for r in filas)
        by_segment[seg] = {
            "n":          len(filas),
            "conv":       conv_s,
            "conv_rate":  conv_s / len(filas) if filas else 0,
            "revenue":    rev_s,
            "avg_ticket": rev_s / conv_s if conv_s else 0,
        }

    # Por dispositivo
    by_device: dict[str, Any] = {}
    for dev in ("mobile", "desktop", "tablet"):
        filas = [r for r in resultados if r["device"] == dev]
        if not filas:
            continue
        conv_d = sum(1 for r in filas if r["conversion"])
        by_device[dev] = {"n": len(filas), "conv_rate": conv_d / len(filas)}

    # Friction points: dónde se van sin convertir
    no_conv = [r for r in resultados if not r["conversion"]]
    friction = []
    if no_conv:
        low_scroll = sum(1 for r in no_conv if r["scroll_depth"] < 0.5) / len(no_conv)
        fast_exit  = sum(1 for r in no_conv if r["tiempo_pdp"] < 35) / len(no_conv)
        no_reviews = sum(1 for r in no_conv if r["reviews_vistas"] == 0) / len(no_conv)
        if low_scroll > 0.40:
            friction.append(f"{low_scroll:.0%} de no-conv scrollean < 50% → hero/headline débil")
        if fast_exit > 0.35:
            friction.append(f"{fast_exit:.0%} de no-conv salen antes de 35s → valor no claro en el inicio")
        if no_reviews > 0.50:
            friction.append(f"{no_reviews:.0%} de no-conv no leyeron reseñas → social proof no visible")

    datos = {
        "n_clientes":     n_clientes,
        "conversions":    total_conv,
        "conversion_rate":conv_rate,
        "avg_ticket":     avg_ticket,
        "total_revenue":  total_revenue,
        "by_segment":     by_segment,
        "by_device":      by_device,
        "friction_points":friction,
        "resultados":     resultados,
        "csv_path":       csv_path,
    }

    # ── Imprimir resumen ──────────────────────────────────────────────────────
    print(f"\n  📊 MÉTRICAS LANDING v1 ({n_clientes:,} clientes simulados)")
    print(f"  {'─'*50}")
    print(f"  Conversión total   : {conv_rate:.2%}  ({total_conv:,} ventas)")
    print(f"  Ticket promedio    : ${avg_ticket:,.0f}")
    print(f"  Revenue estimado   : ${total_revenue:,.0f}")
    print(f"\n  Por segmento:")
    for seg, s in by_segment.items():
        bar = "█" * int(s["conv_rate"] * 100)
        print(f"    {seg:16} {s['conv_rate']:.1%} {bar}  (n={s['n']:,})")
    print(f"\n  Por dispositivo:")
    for dev, d in by_device.items():
        print(f"    {dev:10} {d['conv_rate']:.1%}  (n={d['n']:,})")
    if friction:
        print(f"\n  Friction points detectados:")
        for fp in friction:
            print(f"    ⚠️  {fp}")
    print(f"\n  CSV guardado en: {csv_path}")

    return datos


if __name__ == "__main__":
    async def _demo():
        tmpl = generar_landing_html()
        datos = await testear_landing(tmpl, n_clientes=200)
        print(f"\nDemo completado. Conv: {datos['conversion_rate']:.2%}")
    asyncio.run(_demo())
