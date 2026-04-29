#!/usr/bin/env python3
"""
Sistema de 5 Agentes IA para Personalización de PDPs - Essent Tea
Aumenta conversión de 0% a 15% personalizando en tiempo real

Arquitectura:
  Fase 1 (paralela): Agente Clasificador + Agente Detector
  Fase 2 (paralela): Agente Headlines + Agente Reseñas + Agente Experiencia

Requiere: ANTHROPIC_API_KEY en el entorno
"""

import asyncio
import json
import re
import time
from typing import Optional
import anthropic


# ============================================================
# DATOS DE ESSENT TEA
# ============================================================

PRODUCTS = {
    "coleccion_origenes_x3": {
        "name": "Colección Orígenes x3",
        "price": 62970,
        "price_formatted": "$62.970",
        "type": "Kit Degustación",
        "profile": "Mix frutal/cítrico/floral",
        "target": "Exploradores",
        "benefits": ["variedad", "descubrimiento", "3 blends distintos"],
    },
    "blueberry_top": {
        "name": "Blueberry Top",
        "price": 38900,
        "price_formatted": "$38.900",
        "type": "Té Negro Frutal",
        "profile": "Frutal con toque dulce natural",
        "target": "Energía suave",
        "benefits": ["energía", "sabor frutal", "té negro premium"],
    },
    "golden_harmony": {
        "name": "Golden Harmony",
        "price": 39970,
        "price_formatted": "$39.970",
        "type": "Té Verde Cítrico",
        "profile": "Cítrico refrescante",
        "target": "Antioxidantes",
        "benefits": ["antioxidantes", "frescura", "equilibrio"],
    },
    "enchanted_fruits": {
        "name": "Enchanted Fruits",
        "price": 30970,
        "price_formatted": "$30.970",
        "type": "Frutal Herbal",
        "profile": "Frutal sin cafeína",
        "target": "Relajación nocturna",
        "benefits": ["relajación", "sin cafeína", "ritual de noche"],
    },
}

SEGMENTS = {
    "Explorador": {
        "motivation": "Busca variedad y descubrimiento de nuevos sabores",
        "fears": "Aburrirse con siempre lo mismo",
        "hook": "Nuevo mundo de sabores para explorar",
        "cta": "Descubrí",
    },
    "Health": {
        "motivation": "Busca beneficios concretos para la salud",
        "fears": "Comprar algo sin valor real o con ingredientes dudosos",
        "hook": "Beneficios comprobados, ingredientes de calidad",
        "cta": "Comenzá tu ritual",
    },
    "Regalero": {
        "motivation": "Busca sorprender con buena presentación",
        "fears": "Que el regalo no impresione o parezca genérico",
        "hook": "Un regalo que se recuerda",
        "cta": "Regalá experiencia",
    },
    "Risk-Avoider": {
        "motivation": "Busca certeza y garantía antes de comprar",
        "fears": "Arrepentirse de la compra o perder el dinero",
        "hook": "Sin riesgo, con garantía total",
        "cta": "Probá sin riesgo",
    },
    "Leal": {
        "motivation": "Compró antes y busca novedad dentro de lo que le gusta",
        "fears": "Encontrar siempre lo mismo sin sorpresas",
        "hook": "Algo nuevo especialmente para vos",
        "cta": "Volvé a descubrir",
    },
}

REVIEWS = [
    {"id": 1, "text": "El Blueberry Top es lo más: el toque dulce natural resalta y con almendras tostadas queda increíble", "product": "blueberry_top", "themes": ["sabor", "maridaje", "dulce", "favorito"]},
    {"id": 2, "text": "Golden Harmony es increíblemente refrescante; equilibra cualquier mate amargo", "product": "golden_harmony", "themes": ["frescura", "mate", "equilibrio", "sabor"]},
    {"id": 3, "text": "La infusión Enchanted Fruits me ayuda a relajarme de noche: no tiene cafeína", "product": "enchanted_fruits", "themes": ["relajación", "noche", "sin cafeína", "ritual"]},
    {"id": 4, "text": "El kit Colección Orígenes x3 me permitió probar varios sabores y repito cada mes", "product": "coleccion_origenes_x3", "themes": ["variedad", "descubrimiento", "repetición", "kit"]},
    {"id": 5, "text": "La descripción del perfil de cada blend es muy acertada; me ayudó a elegir sin adivinar", "product": "any", "themes": ["información", "confianza", "elección", "certeza"]},
    {"id": 6, "text": "Compré el kit con taza y cuchara y la experiencia es maravillosa, ideal para regalar", "product": "any", "themes": ["regalo", "experiencia", "kit", "presentación"]},
    {"id": 7, "text": "Me sorprendió lo aromático que es el té en hebras; se nota la calidad premium", "product": "any", "themes": ["calidad", "aroma", "premium", "sorpresa"]},
    {"id": 8, "text": "Amo mezclar Golden Harmony con el mate: aporta frescura sin restarle intensidad", "product": "golden_harmony", "themes": ["mate", "frescura", "mezcla", "ritual"]},
    {"id": 9, "text": "El envío fue rápido y la presentación muy cuidada; se nota que trabajan con amor", "product": "any", "themes": ["envío", "presentación", "cuidado", "regalo"]},
    {"id": 10, "text": "El pack de degustación me permitió descubrir nuevos sabores sin arriesgar", "product": "coleccion_origenes_x3", "themes": ["descubrimiento", "sin riesgo", "degustación", "variedad"]},
    {"id": 11, "text": "La calidad de los ingredientes se nota; desde que los pruebo mi ritual cambió", "product": "any", "themes": ["calidad", "ritual", "cambio", "ingredientes"]},
    {"id": 12, "text": "El té en hebras rinde más de lo que pensaba; con una cucharadita preparo varias tazas", "product": "any", "themes": ["rendimiento", "economía", "valor", "calidad"]},
    {"id": 13, "text": "Es genial poder elegir un blend según mi estado de ánimo: energía, relax, digestión", "product": "any", "themes": ["variedad", "estados de ánimo", "elección", "personalización"]},
    {"id": 14, "text": "Compré Blueberry Top y mis tardes cambiaron; se volvió mi favorito", "product": "blueberry_top", "themes": ["favorito", "ritual", "tardes", "fidelización"]},
    {"id": 15, "text": "Combiné las hebras con yerba mate; ¡una explosión de sabores!", "product": "any", "themes": ["mate", "mezcla", "explosión", "descubrimiento"]},
]

BUNDLES = {
    "Explorador": {
        "name": "Kit Explorador",
        "add": "Infusor Premium incluido",
        "extra_price": 10000,
        "description": "Explorá todos los sabores con el accesorio perfecto para preparar tu té",
    },
    "Health": {
        "name": "Plan Salud Mensual",
        "add": "Suscripción mensual recurrente",
        "extra_price": 0,
        "description": "Recibí tu té cada mes automáticamente, con precio preferencial de suscriptor",
    },
    "Regalero": {
        "name": "Kit Regalo Premium",
        "add": "Tarjeta personalizada + Empaque especial",
        "extra_price": 4000,
        "description": "Presentación impecable lista para regalar, con tarjeta manuscrita incluida",
    },
    "Risk-Avoider": {
        "name": "Compra Sin Riesgo",
        "add": "Garantía de devolución 30 días gratis",
        "extra_price": 0,
        "description": "Si no te enamora en 30 días, te devolvemos el dinero. Sin preguntas, sin vueltas.",
    },
    "Leal": {
        "name": "Descuento Fidelidad",
        "add": "15% OFF exclusivo para clientes frecuentes",
        "extra_price": 0,
        "description": "Tu beneficio exclusivo por confiar en nosotros. Solo para clientes como vos.",
    },
}

PAIRINGS = {
    "blueberry_top": ["Chocolate amargo", "Almendras tostadas", "Frutos rojos frescos", "Granola"],
    "golden_harmony": ["Mate", "Scones de limón", "Ensaladas frescas", "Sushi", "Queso crema"],
    "enchanted_fruits": ["Tartas de manzana", "Frutos secos", "Yogurt natural", "Budín de pan"],
    "coleccion_origenes_x3": ["Varía según el blend elegido", "Chocolate negro", "Frutas de estación", "Medialunas"],
}

# Contexto estable para prompt caching (no cambia entre requests)
STABLE_CONTEXT = f"""
# ESSENT TEA — Sistema de Personalización PDP Argentina

## Productos del Catálogo
{json.dumps(PRODUCTS, ensure_ascii=False, indent=2)}

## Segmentos de Clientes (5 perfiles)
{json.dumps(SEGMENTS, ensure_ascii=False, indent=2)}

## Banco de Reseñas Reales (15 comentarios verificados)
{json.dumps(REVIEWS, ensure_ascii=False, indent=2)}

## Bundles por Segmento
{json.dumps(BUNDLES, ensure_ascii=False, indent=2)}

## Maridajes por Producto
{json.dumps(PAIRINGS, ensure_ascii=False, indent=2)}

## Contexto de Negocio
- Plataforma: Tienda Nube
- Mercado: Argentina
- Objetivo: Aumentar conversión del 0% al 15% con personalización en tiempo real
- Tono: Argentino cercano (usar "vos", "sos", "te", lenguaje natural)
- Propuesta de valor: Tés premium en hebras, calidad artesanal, ritual de bienestar
"""


# ============================================================
# UTILIDADES
# ============================================================

def parse_json_response(text: str) -> dict:
    """Extrae JSON válido de la respuesta de Claude (maneja markdown code blocks)."""
    # Eliminar bloques de código markdown si existen
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    text = re.sub(r"```\s*$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Intentar encontrar el primer objeto JSON en el texto
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise


# ============================================================
# AGENTE 1: CLASIFICADOR DE SEGMENTO
# ============================================================

async def agent_classifier(client: anthropic.AsyncAnthropic, visitor_data: dict) -> dict:
    """
    Clasifica al visitante en uno de los 5 segmentos.

    Input:  fuente de tráfico, dispositivo, primera visita, hora, producto, historial
    Output: segmento (Explorador/Health/Regalero/Risk-Avoider/Leal), urgencia, confianza
    """
    prompt = f"""Sos el Agente Clasificador de Essent Tea. Analizá los datos del visitante y determiná su segmento.

DATOS DEL VISITANTE:
{json.dumps(visitor_data, ensure_ascii=False, indent=2)}

REGLAS DE CLASIFICACIÓN:
- Explorador: Llega de redes sociales/ads, primera visita, clicks en variedad/imágenes
- Health: Viene de búsquedas de salud en Google, lee ingredientes/beneficios, hora matutina
- Regalero: Fuente contiene "regalo", mira packaging/kits, hora laboral o fin de semana
- Risk-Avoider: Múltiples visitas sin comprar, mucho tiempo en FAQ/políticas, abandono de carrito
- Leal: Tiene historial de compras previas en Essent Tea

SEÑALES ADICIONALES:
- Hora 6-10: posiblemente Health seeker (ritual mañanero)
- Hora 19-23: posiblemente relajación (Enchanted Fruits target)
- Búsqueda "regalo" en fuente: Regalero casi seguro
- 3+ visitas sin compra: Risk-Avoider
- historial con productos = Leal

Respondé ÚNICAMENTE con JSON válido, sin texto adicional antes ni después:
{{
  "segment": "nombre_exacto_del_segmento",
  "urgency": "low|medium|high",
  "confidence": 0.85,
  "reasoning": "explicación de 1-2 frases en español sobre por qué este segmento"
}}"""

    response = await client.messages.create(
        model="claude-opus-4-7",
        max_tokens=512,
        thinking={"type": "adaptive"},
        system=[{
            "type": "text",
            "text": STABLE_CONTEXT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": prompt}],
    )

    text = next(b.text for b in response.content if b.type == "text")
    return parse_json_response(text)


# ============================================================
# AGENTE 2: DETECTOR DE COMPORTAMIENTO
# ============================================================

async def agent_detector(client: anthropic.AsyncAnthropic, behavior_data: dict) -> dict:
    """
    Detecta el punto de dolor del visitante según su comportamiento en la PDP.

    Input:  scroll depth, clicks, tiempo en página, reseñas vistas, visitas a FAQ
    Output: punto de dolor detectado, elemento a priorizar, intervención recomendada
    """
    prompt = f"""Sos el Agente Detector de Comportamiento de Essent Tea. Analizá el comportamiento en la PDP.

COMPORTAMIENTO DEL VISITANTE:
{json.dumps(behavior_data, ensure_ascii=False, indent=2)}

PATRONES DE INTERPRETACIÓN:
- Scroll rápido (< 30s) + poco tiempo = no encuentra el valor, priorizan HEADLINE
- Tiempo > 120s sin acción = indecisión, necesita URGENCIA o GARANTÍA
- Clicks en precio repetidos = sensibilidad al precio, ofrecer BUNDLE/VALOR
- Muchas reseñas vistas = necesita validación social, destacar REVIEWS
- Clicks en ingredientes/beneficios = interés en salud, ampliar BENEFICIOS
- Abandono en carrito previo = fricción final, necesita GARANTÍA
- Visitas a FAQ/devoluciones = Risk-Avoider, necesita CERTEZA

Respondé ÚNICAMENTE con JSON válido:
{{
  "pain_point": "descripción concisa del problema principal detectado",
  "element_to_prioritize": "reviews|price|benefits|guarantee|urgency|bundle|headline",
  "confidence": 0.80,
  "behavioral_signals": ["señal1 observada", "señal2 observada"],
  "recommended_intervention": "qué cambiar o destacar en el PDP para este visitante"
}}"""

    response = await client.messages.create(
        model="claude-opus-4-7",
        max_tokens=512,
        system=[{
            "type": "text",
            "text": STABLE_CONTEXT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": prompt}],
    )

    text = next(b.text for b in response.content if b.type == "text")
    return parse_json_response(text)


# ============================================================
# AGENTE 3: GENERADOR DE HEADLINES
# ============================================================

async def agent_headlines(
    client: anthropic.AsyncAnthropic,
    segment: str,
    product_id: str,
    pain_point: str,
) -> dict:
    """
    Genera el headline dinámico perfecto para el segmento y producto.

    Input:  segmento, producto, punto de dolor
    Output: headline (max 12 palabras), subheader, trigger emocional
    """
    product = PRODUCTS.get(product_id, {})
    segment_data = SEGMENTS.get(segment, {})

    prompt = f"""Sos el Agente de Copy de Essent Tea. Generá el headline que convierte para este visitante.

SEGMENTO: {segment}
MOTIVACIÓN: {segment_data.get("motivation", "")}
MIEDO: {segment_data.get("fears", "")}
PRODUCTO: {json.dumps(product, ensure_ascii=False)}
PUNTO DE DOLOR DETECTADO: {pain_point}

REGLAS DE COPY:
- Headline: MÁXIMO 12 palabras, impacto inmediato, SIN punto final
- Hablarle directamente a la motivación del segmento, no al producto
- Subheader: 1-2 frases que amplían la propuesta de valor
- Lenguaje argentino natural (vos, sos, te, etc.)
- Evitar clichés de marketing genérico

REFERENCIAS DE TONO POR SEGMENTO:
- Explorador: "Tres mundos de sabor en un solo pack" / "Un té diferente para cada estado de ánimo"
- Health: "El antioxidante que tu cuerpo esperaba" / "Ritual de bienestar desde la primera taza"
- Regalero: "El regalo que no van a olvidar" / "Porque algunos regalos se prueban, se sienten y se recuerdan"
- Risk-Avoider: "Probalo 30 días. Si no te copa, te devolvemos todo" / "Sin riesgo, con garantía total"
- Leal: "Volviste. Tenemos algo nuevo esperándote" / "Porque los que saben, siempre vuelven por más"

Respondé ÚNICAMENTE con JSON válido:
{{
  "headline": "headline aquí (máximo 12 palabras, sin punto final)",
  "subheader": "1-2 frases que amplían la propuesta de valor para este segmento",
  "explanation": "por qué este headline funciona para este segmento+producto+dolor específico",
  "emotional_trigger": "curiosidad|confianza|urgencia|exclusividad|pertenencia|descubrimiento"
}}"""

    response = await client.messages.create(
        model="claude-opus-4-7",
        max_tokens=512,
        system=[{
            "type": "text",
            "text": STABLE_CONTEXT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": prompt}],
    )

    text = next(b.text for b in response.content if b.type == "text")
    return parse_json_response(text)


# ============================================================
# AGENTE 4: SELECTOR DE RESEÑAS
# ============================================================

async def agent_reviews(
    client: anthropic.AsyncAnthropic,
    segment: str,
    product_id: str,
) -> dict:
    """
    Selecciona la reseña óptima del banco de 15 para el segmento y producto.

    Input:  segmento, producto
    Output: reseña óptima seleccionada, ID, frase clave, por qué resuena
    """
    segment_data = SEGMENTS.get(segment, {})

    prompt = f"""Sos el Agente de Reseñas de Essent Tea. Elegí la reseña del banco que más convierte para este perfil.

SEGMENTO: {segment}
MOTIVACIÓN DEL SEGMENTO: {segment_data.get("motivation", "")}
MIEDO PRINCIPAL: {segment_data.get("fears", "")}
PRODUCTO VISTO: {product_id}

CRITERIOS DE SELECCIÓN POR SEGMENTO:
- Explorador → reseñas sobre descubrimiento, variedad, "probar nuevos sabores"
- Health → reseñas sobre calidad de ingredientes, ritual, beneficios reales
- Regalero → reseñas sobre presentación, experiencia de regalo, "ideal para regalar"
- Risk-Avoider → reseñas que transmiten certeza: "me ayudó a elegir", "sin arriesgar"
- Leal → reseñas sobre ritual establecido, favorito, volver a comprar

PRIORIDAD: primero elegir reseñas del producto específico ({product_id}),
si no hay suficientes, elegir reseñas universales (product: "any").

Respondé ÚNICAMENTE con JSON válido:
{{
  "review_id": 4,
  "review_text": "texto exacto y completo de la reseña elegida",
  "why_it_resonates": "explicación de 1-2 frases de por qué esta reseña conecta con este segmento",
  "secondary_review_id": 10,
  "key_phrase": "la frase más poderosa de la reseña (máximo 8 palabras)"
}}"""

    response = await client.messages.create(
        model="claude-opus-4-7",
        max_tokens=512,
        system=[{
            "type": "text",
            "text": STABLE_CONTEXT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": prompt}],
    )

    text = next(b.text for b in response.content if b.type == "text")
    return parse_json_response(text)


# ============================================================
# AGENTE 5: DISEÑADOR DE EXPERIENCIA
# ============================================================

async def agent_experience(
    client: anthropic.AsyncAnthropic,
    segment: str,
    product_id: str,
    time_on_pdp: int,
    stock_status: str,
) -> dict:
    """
    Diseña la experiencia completa de compra: bundle, urgencia, elementos a mostrar.

    Input:  segmento, producto, tiempo en PDP, estado de stock
    Output: bundle recomendado, precio, copy de urgencia, CTA, elementos UI
    """
    product = PRODUCTS.get(product_id, {})
    bundle = BUNDLES.get(segment, {})
    pairing = PAIRINGS.get(product_id, [])

    # Calcular precio del bundle
    base_price = product.get("price", 0)
    extra_price = bundle.get("extra_price", 0)
    if segment == "Leal":
        bundle_price = int(base_price * 0.85)  # 15% descuento
    else:
        bundle_price = base_price + extra_price

    prompt = f"""Sos el Agente de Experiencia de Essent Tea. Configurá el PDP perfecto para maximizar conversión.

SEGMENTO: {segment}
PRODUCTO: {json.dumps(product, ensure_ascii=False)}
BUNDLE DISPONIBLE: {json.dumps(bundle, ensure_ascii=False)}
PRECIO BASE: ${base_price:,}
PRECIO BUNDLE CALCULADO: ${bundle_price:,}
MARIDAJES: {pairing}
TIEMPO EN PDP: {time_on_pdp} segundos
ESTADO DE STOCK: {stock_status} (normal|low|last_units)

REGLAS DE URGENCIA:
- Si tiempo > 60s sin comprar: activar urgencia media o alta
- Si tiempo > 120s: urgencia alta
- Si stock = "low": mencionar escasez
- Si stock = "last_units": urgencia máxima por escasez
- Si segmento = Risk-Avoider: NO usar urgencia agresiva, usar certeza

ELEMENTOS UI POSIBLES: reviews, pairing, guarantee, bundle_offer, stock_alert,
                        benefits, ingredients, gift_wrap, subscription_offer

Respondé ÚNICAMENTE con JSON válido:
{{
  "bundle_name": "nombre del bundle para mostrar",
  "bundle_description": "descripción persuasiva de 1 frase del bundle",
  "bundle_price": {bundle_price},
  "bundle_price_formatted": "${bundle_price:,}",
  "urgency_copy": "texto de urgencia (ej: 'Solo quedan 3 unidades' o vacío si no aplica)",
  "urgency_level": "none|low|medium|high",
  "show_elements": ["elemento1", "elemento2", "elemento3"],
  "cta_primary": "texto del botón principal de compra (máximo 4 palabras)",
  "cta_secondary": "texto del botón secundario (máximo 4 palabras)",
  "pairing_suggestion": "el maridaje más atractivo para mostrar bajo el producto",
  "trust_badge": "elemento de confianza principal a destacar para este segmento"
}}"""

    response = await client.messages.create(
        model="claude-opus-4-7",
        max_tokens=768,
        system=[{
            "type": "text",
            "text": STABLE_CONTEXT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": prompt}],
    )

    text = next(b.text for b in response.content if b.type == "text")
    return parse_json_response(text)


# ============================================================
# ORQUESTADOR PRINCIPAL
# ============================================================

async def generate_pdp(client_data: dict) -> dict:
    """
    Función principal. Recibe datos del cliente y ejecuta los 5 agentes.

    Arquitectura de paralelismo:
      Fase 1 (paralela): Clasificador + Detector  — sin dependencias entre sí
      Fase 2 (paralela): Headlines + Reseñas + Experiencia — usan output de Fase 1

    Returns: dict con configuración completa del PDP personalizado
    """
    client = anthropic.AsyncAnthropic()

    product_id = client_data.get("product_id", "golden_harmony")
    time_on_pdp = client_data.get("time_on_pdp", 30)
    stock_status = client_data.get("stock_status", "normal")

    behavior_data = {
        "scroll_depth_pct": client_data.get("scroll_depth", 0.5),
        "time_on_page_seconds": time_on_pdp,
        "section_clicks": client_data.get("clicks", []),
        "reviews_read": client_data.get("reviews_seen", 0),
        "faq_page_visits": client_data.get("faq_visits", 0),
        "previous_cart_abandonment": client_data.get("cart_abandonment", False),
    }

    visitor_data = {
        "traffic_source": client_data.get("traffic_source", "organic"),
        "device": client_data.get("device", "mobile"),
        "first_visit": client_data.get("first_visit", True),
        "hour_of_day": client_data.get("hour", 14),
        "product_id": product_id,
        "purchase_history": client_data.get("purchase_history", []),
    }

    start_time = time.time()

    # FASE 1: Clasificador + Detector en paralelo
    classifier_result, detector_result = await asyncio.gather(
        agent_classifier(client, visitor_data),
        agent_detector(client, behavior_data),
    )

    segment = classifier_result.get("segment", "Explorador")
    pain_point = detector_result.get("pain_point", "No encuentra el valor rápidamente")

    # FASE 2: Headlines + Reseñas + Experiencia en paralelo
    headlines_result, reviews_result, experience_result = await asyncio.gather(
        agent_headlines(client, segment, product_id, pain_point),
        agent_reviews(client, segment, product_id),
        agent_experience(client, segment, product_id, time_on_pdp, stock_status),
    )

    elapsed = round(time.time() - start_time, 2)

    return {
        "metadata": {
            "client_id": client_data.get("client_id", "anonymous"),
            "product_id": product_id,
            "product_name": PRODUCTS.get(product_id, {}).get("name", product_id),
            "processing_time_seconds": elapsed,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "agents_run": 5,
        },
        "segmentation": {
            "segment": segment,
            "urgency": classifier_result.get("urgency"),
            "confidence": classifier_result.get("confidence"),
            "reasoning": classifier_result.get("reasoning"),
        },
        "behavioral_analysis": {
            "pain_point": pain_point,
            "element_to_prioritize": detector_result.get("element_to_prioritize"),
            "behavioral_signals": detector_result.get("behavioral_signals", []),
            "recommended_intervention": detector_result.get("recommended_intervention"),
        },
        "copy": {
            "headline": headlines_result.get("headline"),
            "subheader": headlines_result.get("subheader"),
            "emotional_trigger": headlines_result.get("emotional_trigger"),
            "cta_primary": experience_result.get("cta_primary"),
            "cta_secondary": experience_result.get("cta_secondary"),
            "urgency_copy": experience_result.get("urgency_copy"),
            "trust_badge": experience_result.get("trust_badge"),
        },
        "social_proof": {
            "featured_review": reviews_result.get("review_text"),
            "review_id": reviews_result.get("review_id"),
            "key_phrase": reviews_result.get("key_phrase"),
            "why_it_resonates": reviews_result.get("why_it_resonates"),
            "secondary_review_id": reviews_result.get("secondary_review_id"),
        },
        "offer": {
            "bundle_name": experience_result.get("bundle_name"),
            "bundle_description": experience_result.get("bundle_description"),
            "bundle_price": experience_result.get("bundle_price"),
            "bundle_price_formatted": experience_result.get("bundle_price_formatted"),
            "urgency_level": experience_result.get("urgency_level"),
            "pairing_suggestion": experience_result.get("pairing_suggestion"),
        },
        "ui_config": {
            "show_elements": experience_result.get("show_elements", []),
        },
    }


# ============================================================
# EJEMPLOS DE USO
# ============================================================

EXAMPLES = {
    "explorador_viendo_origenes": {
        "client_id": "visitor_explorador_001",
        "product_id": "coleccion_origenes_x3",
        "traffic_source": "instagram_reels_ad",
        "device": "mobile",
        "first_visit": True,
        "hour": 19,
        "scroll_depth": 0.7,
        "time_on_pdp": 45,
        "clicks": ["product_images", "reviews_section", "flavors_tab"],
        "reviews_seen": 3,
        "faq_visits": 0,
        "cart_abandonment": False,
        "purchase_history": [],
        "stock_status": "normal",
    },
    "regalero_viendo_blueberry": {
        "client_id": "visitor_regalero_002",
        "product_id": "blueberry_top",
        "traffic_source": "google_regalo_amante_te",
        "device": "desktop",
        "first_visit": True,
        "hour": 11,
        "scroll_depth": 0.55,
        "time_on_pdp": 90,
        "clicks": ["gift_wrapping_section", "packaging_photos", "price_tag"],
        "reviews_seen": 5,
        "faq_visits": 1,
        "cart_abandonment": False,
        "purchase_history": [],
        "stock_status": "normal",
    },
    "risk_avoider_viendo_golden": {
        "client_id": "visitor_riskavoider_003",
        "product_id": "golden_harmony",
        "traffic_source": "direct_return_visit",
        "device": "desktop",
        "first_visit": False,
        "hour": 14,
        "scroll_depth": 0.95,
        "time_on_pdp": 195,
        "clicks": ["faq_link", "return_policy", "ingredients_detail", "price", "reviews_all"],
        "reviews_seen": 9,
        "faq_visits": 3,
        "cart_abandonment": True,
        "purchase_history": [],
        "stock_status": "low",
    },
}


async def run_examples():
    """Ejecuta los 3 ejemplos principales con output formateado."""
    print("\n" + "═" * 62)
    print("  ESSENT TEA — Ejemplos de PDPs Personalizados")
    print("═" * 62)

    for name, data in EXAMPLES.items():
        print(f"\n🍃 ESCENARIO: {name.replace('_', ' ').upper()}")
        print(f"   Cliente: {data['client_id']}")
        print(f"   Producto: {PRODUCTS.get(data['product_id'], {}).get('name', data['product_id'])}")
        print(f"   Fuente: {data['traffic_source']} | Dispositivo: {data['device']}")
        print("─" * 62)

        pdp = await generate_pdp(data)

        seg = pdp["segmentation"]
        copy = pdp["copy"]
        proof = pdp["social_proof"]
        offer = pdp["offer"]
        behavior = pdp["behavioral_analysis"]

        print(f"🎯 Segmento detectado : {seg['segment']} (confianza: {seg['confidence']})")
        print(f"🔍 Razón              : {seg['reasoning']}")
        print(f"⚡ Dolor detectado    : {behavior['pain_point']}")
        print(f"🎨 Priorizar elemento : {behavior['element_to_prioritize']}")
        print()
        print(f"📣 HEADLINE          : {copy['headline']}")
        print(f"   Subheader         : {copy['subheader']}")
        print(f"   Trigger emocional : {copy['emotional_trigger']}")
        print()
        print(f"⭐ RESEÑA ELEGIDA     : \"{proof['featured_review'][:90]}...\"")
        print(f"   Frase clave       : {proof['key_phrase']}")
        print(f"   Por qué resuena   : {proof['why_it_resonates']}")
        print()
        print(f"🛒 BUNDLE             : {offer['bundle_name']} — {offer['bundle_price_formatted']}")
        print(f"   Descripción       : {offer['bundle_description']}")
        print(f"   Maridaje          : {offer['pairing_suggestion']}")
        print(f"🔥 Urgencia           : {copy['urgency_copy'] or '(sin urgencia)'} [{offer['urgency_level']}]")
        print(f"✅ CTA Principal      : {copy['cta_primary']}")
        print(f"   CTA Secundario    : {copy['cta_secondary']}")
        print(f"🏅 Trust badge        : {copy['trust_badge']}")
        print(f"   Elementos UI      : {', '.join(pdp['ui_config']['show_elements'])}")
        print(f"\n⏱️  Tiempo de proceso : {pdp['metadata']['processing_time_seconds']}s (5 agentes paralelos)")
        print()


# ============================================================
# FUNCIÓN DE TESTING (10 CLIENTES)
# ============================================================

TEST_CLIENTS = [
    # 1. Explorador mobile Instagram
    {"client_id": "test_01", "product_id": "coleccion_origenes_x3", "traffic_source": "instagram", "device": "mobile", "first_visit": True, "hour": 20, "scroll_depth": 0.8, "time_on_pdp": 40, "clicks": ["images"], "reviews_seen": 2, "faq_visits": 0, "cart_abandonment": False, "purchase_history": [], "stock_status": "normal"},
    # 2. Health seeker matutino
    {"client_id": "test_02", "product_id": "golden_harmony", "traffic_source": "google_organic_antioxidantes", "device": "desktop", "first_visit": True, "hour": 8, "scroll_depth": 0.9, "time_on_pdp": 120, "clicks": ["ingredients", "benefits", "nutrition"], "reviews_seen": 6, "faq_visits": 0, "cart_abandonment": False, "purchase_history": [], "stock_status": "normal"},
    # 3. Regalero navideño
    {"client_id": "test_03", "product_id": "coleccion_origenes_x3", "traffic_source": "google_regalo_original", "device": "mobile", "first_visit": True, "hour": 15, "scroll_depth": 0.6, "time_on_pdp": 75, "clicks": ["packaging", "gift_section"], "reviews_seen": 4, "faq_visits": 1, "cart_abandonment": False, "purchase_history": [], "stock_status": "normal"},
    # 4. Risk-Avoider clásico con abandono
    {"client_id": "test_04", "product_id": "enchanted_fruits", "traffic_source": "direct", "device": "desktop", "first_visit": False, "hour": 22, "scroll_depth": 1.0, "time_on_pdp": 240, "clicks": ["faq", "return_policy", "price", "reviews_all"], "reviews_seen": 10, "faq_visits": 4, "cart_abandonment": True, "purchase_history": [], "stock_status": "low"},
    # 5. Cliente leal volviendo por email
    {"client_id": "test_05", "product_id": "blueberry_top", "traffic_source": "email_newsletter", "device": "desktop", "first_visit": False, "hour": 12, "scroll_depth": 0.5, "time_on_pdp": 30, "clicks": [], "reviews_seen": 1, "faq_visits": 0, "cart_abandonment": False, "purchase_history": ["enchanted_fruits", "golden_harmony"], "stock_status": "normal"},
    # 6. Explorador desde TikTok
    {"client_id": "test_06", "product_id": "coleccion_origenes_x3", "traffic_source": "tiktok_video", "device": "mobile", "first_visit": True, "hour": 21, "scroll_depth": 0.6, "time_on_pdp": 35, "clicks": ["images", "reviews"], "reviews_seen": 2, "faq_visits": 0, "cart_abandonment": False, "purchase_history": [], "stock_status": "normal"},
    # 7. Health seeker nocturno en Enchanted
    {"client_id": "test_07", "product_id": "enchanted_fruits", "traffic_source": "google_te_sin_cafeina", "device": "desktop", "first_visit": True, "hour": 23, "scroll_depth": 0.85, "time_on_pdp": 95, "clicks": ["caffeine_free_badge", "ingredients"], "reviews_seen": 5, "faq_visits": 0, "cart_abandonment": False, "purchase_history": [], "stock_status": "normal"},
    # 8. Regalero en Blueberry Top
    {"client_id": "test_08", "product_id": "blueberry_top", "traffic_source": "pinterest_regalo_te", "device": "mobile", "first_visit": True, "hour": 16, "scroll_depth": 0.55, "time_on_pdp": 60, "clicks": ["gift_wrap_option"], "reviews_seen": 3, "faq_visits": 0, "cart_abandonment": False, "purchase_history": [], "stock_status": "normal"},
    # 9. Risk-Avoider en Golden Harmony
    {"client_id": "test_09", "product_id": "golden_harmony", "traffic_source": "direct", "device": "tablet", "first_visit": False, "hour": 19, "scroll_depth": 0.95, "time_on_pdp": 200, "clicks": ["reviews", "faq", "return_policy", "price"], "reviews_seen": 12, "faq_visits": 3, "cart_abandonment": True, "purchase_history": [], "stock_status": "normal"},
    # 10. Leal comprando Colección Orígenes
    {"client_id": "test_10", "product_id": "coleccion_origenes_x3", "traffic_source": "email_leal_promo", "device": "desktop", "first_visit": False, "hour": 10, "scroll_depth": 0.4, "time_on_pdp": 25, "clicks": [], "reviews_seen": 0, "faq_visits": 0, "cart_abandonment": False, "purchase_history": ["blueberry_top", "golden_harmony", "enchanted_fruits"], "stock_status": "normal"},
]


async def run_test_suite() -> list:
    """Simula 10 clientes distintos y mide el rendimiento del sistema."""
    print("\n" + "═" * 62)
    print("  TESTING SUITE — Simulación de 10 Clientes")
    print("═" * 62)
    print(f"  {'ID':10} {'Segmento':16} {'Producto':26} {'Tiempo':8} {'Headline'}")
    print("─" * 62)

    results = []
    total_start = time.time()

    for client_data in TEST_CLIENTS:
        start = time.time()
        pdp = await generate_pdp(client_data)
        elapsed = round(time.time() - start, 2)

        result = {
            "client_id": client_data["client_id"],
            "product": client_data["product_id"],
            "segment": pdp["segmentation"]["segment"],
            "headline": pdp["copy"]["headline"],
            "bundle": pdp["offer"]["bundle_name"],
            "cta": pdp["copy"]["cta_primary"],
            "time_seconds": elapsed,
        }
        results.append(result)

        print(f"  {result['client_id']:10} {result['segment']:16} {client_data['product_id']:26} {elapsed:.1f}s")
        print(f"  {'':10} → {result['headline']}")

    total_time = round(time.time() - total_start, 2)
    avg_time = round(sum(r["time_seconds"] for r in results) / len(results), 2)

    print("\n" + "─" * 62)
    print(f"  📊 MÉTRICAS DE RENDIMIENTO")
    print(f"     Clientes procesados : {len(results)}")
    print(f"     Tiempo total        : {total_time}s")
    print(f"     Tiempo promedio/PDP : {avg_time}s")
    print(f"     Agentes por PDP     : 5 (paralelos)")

    segment_dist: dict = {}
    for r in results:
        segment_dist[r["segment"]] = segment_dist.get(r["segment"], 0) + 1
    print(f"\n  📊 DISTRIBUCIÓN DE SEGMENTOS")
    for seg, count in sorted(segment_dist.items(), key=lambda x: -x[1]):
        bar = "█" * count
        print(f"     {seg:16} {bar} ({count})")

    return results


# ============================================================
# GUARDAR MATRICES JSON
# ============================================================

def save_data_matrices():
    """Guarda las matrices de datos de Essent Tea en archivos JSON."""

    # Matriz de reseñas clasificadas por segmento
    theme_map = {
        "Explorador": ["variedad", "descubrimiento", "degustación", "estados de ánimo", "personalización"],
        "Health": ["calidad", "ritual", "ingredientes", "beneficios"],
        "Regalero": ["regalo", "experiencia", "presentación", "kit"],
        "Risk-Avoider": ["sin riesgo", "confianza", "información", "certeza"],
        "Leal": ["favorito", "ritual", "repetición", "fidelización"],
    }

    reviews_matrix = {}
    for seg, themes in theme_map.items():
        reviews_matrix[seg] = [r for r in REVIEWS if any(t in r["themes"] for t in themes)]

    with open("reviews_matrix.json", "w", encoding="utf-8") as f:
        json.dump(reviews_matrix, f, ensure_ascii=False, indent=2)

    with open("bundles_matrix.json", "w", encoding="utf-8") as f:
        json.dump(BUNDLES, f, ensure_ascii=False, indent=2)

    # Matriz de precios de bundle por segmento y producto
    headlines_matrix = {
        seg: {
            prod: {
                "base_price": data["price"],
                "bundle_extra": BUNDLES[seg]["extra_price"],
                "bundle_total": int(data["price"] * 0.85) if seg == "Leal" else data["price"] + BUNDLES[seg]["extra_price"],
                "bundle_name": BUNDLES[seg]["name"],
            }
            for prod, data in PRODUCTS.items()
        }
        for seg in SEGMENTS
    }

    with open("headlines_matrix.json", "w", encoding="utf-8") as f:
        json.dump(headlines_matrix, f, ensure_ascii=False, indent=2)

    print("\n  ✅ Matrices guardadas:")
    print("     - reviews_matrix.json  (reseñas por segmento)")
    print("     - bundles_matrix.json  (bundles y extras)")
    print("     - headlines_matrix.json (precios de bundle)")


# ============================================================
# ENTRY POINT
# ============================================================

async def main():
    print("\n🍃 ESSENT TEA — Sistema de Personalización de PDPs con IA")
    print("   5 Agentes Claude ejecutándose en paralelo (2 fases)")
    print("   Objetivo: Conversión 0% → 15% | Plataforma: Tienda Nube")

    save_data_matrices()
    await run_examples()
    await run_test_suite()

    print("\n✅ Sistema ejecutado exitosamente.\n")


if __name__ == "__main__":
    asyncio.run(main())
