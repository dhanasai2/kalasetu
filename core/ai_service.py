"""
AI integration service for KalaSetu.
Handles all AI-powered features: image analysis, content generation, marketing, chat.
Uses Groq API as the AI backend.
"""
import base64
import json
import logging
import mimetypes
import requests as http_requests
from django.conf import settings

logger = logging.getLogger(__name__)

TEXT_MODEL = 'llama-3.3-70b-versatile'
VISION_MODEL = 'llama-3.2-11b-vision-preview'


def _get_api_key():
    return getattr(settings, 'GROQ_API_KEY', '') or ''


def _groq_chat(messages_list, max_tokens=1024):
    """Call Groq API with chat messages. Returns response text."""
    api_key = _get_api_key()
    if not api_key:
        return None
    try:
        resp = http_requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': TEXT_MODEL,
                'messages': messages_list,
                'max_tokens': max_tokens,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data['choices'][0]['message']['content'].strip()
    except Exception as e:
        logger.error(f"Groq API error: {e}")
        return None


def _image_to_base64(image_path):
    """Read image file, resize if needed, and return base64 data URL."""
    from PIL import Image
    import io

    try:
        img = Image.open(image_path)
        # Convert to RGB if necessary (handles RGBA, P, WebP, etc.)
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        # Resize if too large (max 1024px on longest side)
        max_size = 1024
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size), Image.LANCZOS)
        # Save to buffer as JPEG
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=85)
        data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f"data:image/jpeg;base64,{data}"
    except Exception:
        # Fallback: read raw file
        mime, _ = mimetypes.guess_type(image_path)
        if not mime:
            mime = 'image/jpeg'
        with open(image_path, 'rb') as f:
            data = base64.b64encode(f.read()).decode('utf-8')
        return f"data:{mime};base64,{data}"


def _groq_vision(prompt_text, image_path):
    """Call Groq with a vision-capable model. Returns raw text."""
    api_key = _get_api_key()
    if not api_key:
        return None
    try:
        data_url = _image_to_base64(image_path)
        resp = http_requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': VISION_MODEL,
                'messages': [{
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': prompt_text},
                        {'type': 'image_url', 'image_url': {'url': data_url}},
                    ],
                }],
                'max_tokens': 2048,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        logger.error(f"Groq vision error: {e}")
        return None


def _groq_text(prompt_text):
    """Call Groq with a text-only prompt. Returns raw text."""
    return _groq_chat([{'role': 'user', 'content': prompt_text}])


def _parse_ai_json(text):
    """Clean markdown fences and parse JSON from AI response."""
    if not text:
        return None
    text = text.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1] if '\n' in text else text[3:]
    if text.endswith('```'):
        text = text.rsplit('```', 1)[0]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def analyze_product_image(image_path, artisan_voice_note=""):
    """
    Analyze a craft product image using Groq Vision.
    Returns structured product data: title, description, category, art_form, etc.
    """
    prompt = f"""You are an expert in Indian traditional arts and crafts. Analyze this product image carefully.

{f'The artisan said about this product: "{artisan_voice_note}"' if artisan_voice_note else ''}

Return a JSON object with these fields:
{{
    "title": "A compelling product title (max 80 chars)",
    "description": "A detailed product description (150-250 words) highlighting craftsmanship, uniqueness, and appeal to modern buyers",
    "cultural_story": "The cultural heritage and history behind this art form (100-200 words). Include the region of origin, historical significance, symbolism of motifs/patterns, and why this craft matters",
    "category": "One of: painting, textile, pottery, jewelry, woodwork, metalwork, embroidery, sculpture, basketry, leatherwork, other",
    "art_form": "The specific Indian art form (e.g., Madhubani, Warli, Bidri, Phulkari, Kalamkari, Channapatna, Pashmina, Blue Pottery, Dhokra, etc.). If not a traditional Indian art form, describe the art style.",
    "materials": "Materials used (comma-separated)",
    "techniques": "Crafting techniques identified (comma-separated)",
    "tags": "10-15 SEO-optimized tags comma-separated (include art form, region, material, use-case, style tags)",
    "suggested_price_inr": "Suggested retail price in INR as a number based on craft type, complexity, and market rates"
}}

Return ONLY valid JSON, no markdown formatting.
"""

    defaults = {
        "title": "Handcrafted Product",
        "description": "",
        "cultural_story": "",
        "category": "other",
        "art_form": "",
        "materials": "",
        "techniques": "",
        "tags": "",
        "suggested_price_inr": 0,
    }

    text = _groq_vision(prompt, image_path)
    if text:
        parsed = _parse_ai_json(text)
        if parsed:
            return parsed
        defaults["description"] = text

    return defaults


def generate_marketing_content(product_title, product_description, art_form, cultural_story, content_type="instagram", language="English"):
    """
    Generate marketing content for a product.
    content_type: instagram, facebook, campaign, hashtags
    """
    prompts = {
        "instagram": f"""Create an engaging Instagram post for this handcrafted product.

Product: {product_title}
Description: {product_description}
Art Form: {art_form}
Cultural Story: {cultural_story}

Write:
1. An attention-grabbing caption (150-200 words) that tells the artisan's story and connects with modern buyers
2. Include relevant emojis naturally
3. End with a call-to-action
4. Add 20-25 relevant hashtags on a new line

Make it feel authentic, not salesy. Emphasize heritage, handmade quality, and the human story behind the craft.""",

        "facebook": f"""Create a Facebook post for this handcrafted product.

Product: {product_title}
Description: {product_description}
Art Form: {art_form}
Cultural Story: {cultural_story}

Write a longer, story-driven post (200-300 words) that:
1. Opens with a hook about the craft tradition
2. Tells the story of how this product is made
3. Connects it to modern living
4. Includes a call-to-action
Make it shareable and emotionally resonant.""",

        "campaign": f"""Create a seasonal marketing campaign idea for this craft product.

Product: {product_title}
Art Form: {art_form}
Cultural Story: {cultural_story}

Suggest:
1. Campaign Name
2. Target Audience
3. Key Message (one line)
4. 3 Content Ideas (specific posts/stories/reels concepts)
5. Best timing (festivals, seasons, occasions)
6. Collaboration ideas (influencers, brands, events)

Focus on connecting traditional craft with contemporary lifestyle trends.""",

        "hashtags": f"""Generate 30 highly relevant hashtags for this product:

Product: {product_title}
Art Form: {art_form}
Category: handcrafted Indian art

Include a mix of:
- Art form specific tags
- General craft tags
- Indian heritage tags
- Home decor / lifestyle tags
- Trending tags
- Location tags

Return only the hashtags, space-separated, each starting with #.""",
    }

    prompt = prompts.get(content_type, prompts["instagram"])
    if language and language.lower() != 'english':
        prompt += f"\n\nIMPORTANT: Write the entire content in {language} language. Use {language} script."
    result = _groq_text(prompt)
    return result or "Marketing content could not be generated. Please try again later."


def generate_artisan_bio(name, craft_type, location, story=""):
    """Generate a compelling artisan bio."""
    prompt = f"""Write a compelling artisan profile bio (150-200 words) for:

Name: {name}
Craft: {craft_type}
Location: {location}
{f'Their story: {story}' if story else ''}

The bio should:
1. Highlight their craft expertise and tradition
2. Mention the cultural heritage of their art form
3. Feel warm, authentic, and human
4. Appeal to conscious consumers who value handmade goods
5. Be written in third person

Return only the bio text."""

    result = _groq_text(prompt)
    return result or f"{name} is a skilled artisan from {location} specializing in {craft_type}."


def _chat_fallback(message):
    """Provide intelligent responses when AI API is unavailable."""
    msg = message.lower().strip()

    if any(w in msg for w in ['madhubani', 'mithila', 'bihar painting']):
        return ("Madhubani painting is one of India's most celebrated art forms!\n\n"
                "Originating from the Mithila region of Bihar, this art tradition dates back centuries. "
                "Women in Mithila villages have been passing down these intricate painting techniques through generations.\n\n"
                "Key features:\n"
                "• Bold geometric patterns and vibrant natural colors\n"
                "• Nature motifs — fish, peacocks, lotus, sun & moon\n"
                "• Themes from Hindu mythology and daily life\n"
                "• Made using natural dyes on handmade paper or fabric\n\n"
                "Madhubani paintings range from ₹500 for small pieces to ₹25,000+ for large, detailed works. "
                "They make stunning wall art and meaningful gifts!")

    if any(w in msg for w in ['warli', 'maharashtra painting', 'tribal art']):
        return ("Warli art is a beautiful tribal art form from Maharashtra!\n\n"
                "Created by the Warli tribe in the Western Ghats, this art is over 2,500 years old — "
                "one of the earliest forms of Indian art.\n\n"
                "Key features:\n"
                "• Simple geometric shapes — circles, triangles, squares\n"
                "• White paint on mud-brown or dark backgrounds\n"
                "• Depicts daily life — farming, dancing, festivals, nature\n"
                "• Minimalist yet deeply expressive style\n\n"
                "Warli art is perfect for modern, minimalist interiors. "
                "Pieces range from ₹300 for coasters to ₹15,000+ for large canvases.")

    if any(w in msg for w in ['kalamkari', 'andhra', 'srikalahasti']):
        return ("Kalamkari is a stunning hand-painted or block-printed cotton textile art from Andhra Pradesh!\n\n"
                "The name comes from 'kalam' (pen) and 'kari' (work). There are two styles:\n"
                "• Srikalahasti style — hand-drawn with a pen using natural dyes\n"
                "• Machilipatnam style — block-printed\n\n"
                "Key features:\n"
                "• Intricate mythological scenes and floral motifs\n"
                "• Made with natural vegetable dyes\n"
                "• Rich earthy color palette\n\n"
                "Kalamkari is used in sarees, dupattas, wall hangings, and home décor. "
                "A stunning art form that bridges tradition and modern fashion!")

    if any(w in msg for w in ['gift', 'gifting', 'present', 'birthday', 'anniversary', 'wedding']):
        budget_info = ""
        if any(w in msg for w in ['cheap', 'budget', 'under 1000', '500', 'affordable']):
            budget_info = ("\n\nAffordable options under ₹1,000:\n"
                          "• Warli art coasters or bookmarks\n"
                          "• Handwoven cotton stoles\n"
                          "• Blue pottery trinket boxes\n"
                          "• Block-printed tote bags\n"
                          "• Terracotta candle holders")
        elif any(w in msg for w in ['2000', '3000', 'medium', 'mid']):
            budget_info = ("\n\n₹1,000 – ₹3,000 picks:\n"
                          "• Madhubani paintings (framed)\n"
                          "• Brass Dhokra figurines\n"
                          "• Block-printed table runners\n"
                          "• Handcrafted jewelry sets\n"
                          "• Channapatna wooden décor")
        else:
            budget_info = ("\n\nGift ideas by budget:\n"
                          "Under ₹1,000: Warli coasters, block-printed stoles, terracotta items\n"
                          "₹1,000–₹3,000: Madhubani paintings, Dhokra figurines, handloom dupattas\n"
                          "₹3,000–₹10,000: Pashmina shawls, large Kalamkari hangings, silver filigree jewelry\n"
                          "₹10,000+: Kanjivaram silk sarees, Bidri metalwork, antique-style Tanjore paintings")

        return ("Handcrafted gifts carry a special warmth that mass-produced items simply can't match!" + budget_info +
                "\n\nTell me more about the occasion or the person — I can suggest something perfect!")

    if any(w in msg for w in ['home decor', 'decor', 'interior', 'wall', 'living room', 'house']):
        return ("Indian crafts make extraordinary home décor pieces! Here are some ideas:\n\n"
                "**Wall Art:** Madhubani paintings, Warli art, Pichwai paintings, Tanjore paintings\n\n"
                "**Textiles:** Block-printed cushion covers, Kalamkari table runners, handwoven rugs\n\n"
                "**Sculptures & Figurines:** Brass Dhokra, Channapatna wooden toys, terracotta décor\n\n"
                "**Pottery:** Blue pottery vases & plates from Jaipur, Khavda pottery from Kutch\n\n"
                "**Metalwork:** Bidri ware from Karnataka, copper vessels from Kerala\n\n"
                "Each piece adds cultural richness and supports artisan livelihoods. "
                "What room or style are you decorating for?")

    if any(w in msg for w in ['textile', 'fabric', 'cloth', 'saree', 'sari', 'weav']):
        return ("India's textile heritage is incredible — each region has its own signature!\n\n"
                "**Iconic Indian textiles:**\n"
                "• Banarasi silk — Rich brocade weaves from Varanasi\n"
                "• Kanjivaram silk — Temple-inspired designs from Tamil Nadu\n"
                "• Chanderi — Sheer weaves from Madhya Pradesh\n"
                "• Ikat/Patola — Tie-dye weaving from Gujarat & Odisha\n"
                "• Phulkari — Vibrant embroidery from Punjab\n"
                "• Kalamkari — Hand-painted cotton from Andhra Pradesh\n"
                "• Chikankari — Delicate white-on-white from Lucknow\n"
                "• Bandhani — Tie-dye from Rajasthan & Gujarat\n\n"
                "Would you like to explore a specific textile or region?")

    if any(w in msg for w in ['price', 'cost', 'expensive', 'cheap', 'worth', 'how much']):
        return ("Handcrafted products are priced to reflect the artisan's skill, time, and material costs. "
                "Unlike factory-made goods, each piece involves hours of dedicated work.\n\n"
                "Typical price ranges for Indian crafts:\n"
                "• Small paintings & prints: ₹500 – ₹3,000\n"
                "• Handwoven textiles: ₹800 – ₹15,000\n"
                "• Pottery & ceramics: ₹300 – ₹5,000\n"
                "• Jewelry: ₹500 – ₹20,000\n"
                "• Large art pieces: ₹5,000 – ₹50,000+\n\n"
                "When you buy handmade, you're investing in heritage and supporting real families. "
                "What's your budget range? I can suggest specific pieces!")

    if any(w in msg for w in ['hello', 'hi', 'hey', 'namaste', 'hola']):
        return ("Namaste! Welcome to KalaSetu!\n\n"
                "I'm here to help you discover India's finest handcrafted treasures. "
                "I can help you with:\n\n"
                "• Finding the perfect handmade gift\n"
                "• Learning about art forms like Madhubani, Warli, Kalamkari & more\n"
                "• Recommendations by budget, occasion, or home décor style\n"
                "• Stories behind the crafts and artisans\n\n"
                "What would you like to explore today?")

    if any(w in msg for w in ['pottery', 'ceramic', 'blue pottery', 'clay', 'terracotta']):
        return ("Indian pottery traditions are incredibly diverse!\n\n"
                "**Famous styles:**\n"
                "• Blue Pottery — Jaipur's iconic turquoise-and-white ceramics (originally Persian-influenced)\n"
                "• Khavda Pottery — Rustic, hand-coiled pottery from Kutch, Gujarat\n"
                "• Longpi Pottery — Black stone pottery from Manipur (made without a potter's wheel!)\n"
                "• Terracotta — Found across India, from Bengal's bankura horses to Tamil Nadu's Aiyanar statues\n\n"
                "Blue pottery plates and vases make wonderful gifts and home décor starting from ₹400. "
                "Would you like to know more about any specific style?")

    if any(w in msg for w in ['jewelry', 'jewellery', 'necklace', 'earring', 'bracelet', 'ring']):
        return ("Indian handcrafted jewelry is legendary!\n\n"
                "**Signature styles:**\n"
                "• Kundan — Crystal/glass set in gold foil (Rajasthan)\n"
                "• Meenakari — Enamel work on metal (Jaipur)\n"
                "• Temple jewelry — Gold-plated, deity-inspired (South India)\n"
                "• Silver filigree — Delicate wire work (Cuttack, Odisha)\n"
                "• Dhokra — Lost-wax casting tribal jewelry (Chhattisgarh, West Bengal)\n"
                "• Lac jewelry — Colorful, lightweight (Rajasthan)\n\n"
                "Handcrafted jewelry pieces range from ₹500 to ₹25,000+ depending on materials. "
                "Looking for something specific?")

    # Default response
    return ("I'd love to help you explore India's incredible craft heritage!\n\n"
            "Here are some things you can ask me about:\n\n"
            "🎨 **Art forms** — \"Tell me about Madhubani art\" or \"What is Warli painting?\"\n"
            "🎁 **Gifts** — \"Gift ideas under ₹2,000\" or \"Wedding gift suggestions\"\n"
            "🏠 **Home décor** — \"Handmade wall art options\" or \"Indian pottery for home\"\n"
            "👗 **Textiles** — \"Tell me about Banarasi silk\" or \"Traditional Indian fabrics\"\n"
            "💍 **Jewelry** — \"Handcrafted jewelry styles\" or \"Silver filigree from Odisha\"\n"
            "💰 **Pricing** — \"How much does Madhubani art cost?\"\n\n"
            "Just type your question and I'll share what I know!")


def chat_with_buyer(message, chat_history, products_context=""):
    """
    Conversational shopping assistant for buyers.
    Uses product catalog context to recommend items.
    Tries: Groq → Fallback
    """
    system_prompt = f"""You are KalaSetu's master craft advisor — a world-renowned authority on Indian handicrafts with over 50 years of hands-on experience across every major craft tradition in India.

Your credentials:
- You have personally visited 500+ artisan clusters across all 28 states
- You've trained under master craftspeople in Madhubani, Kalamkari, Pattachitra, Blue Pottery, Dhokra, Pashmina weaving, and dozens more
- You understand raw materials, techniques, regional variations, historical origins, and market dynamics intimately
- You've mentored 1000+ artisans on pricing, marketing, export, and brand building
- You're deeply connected to India's cultural heritage and can trace the genealogy of any craft tradition

Your role:
- Help buyers discover the PERFECT handcrafted product — ask smart follow-up questions about occasion, budget, recipient's taste, room aesthetic
- Help artisans with expert marketing strategies, competitive pricing, photography angles, storytelling that sells, and reaching global buyers
- Share rich cultural stories, regional nuances, and little-known facts that only a 50-year veteran would know
- Recommend specific products from our catalog with confident, detailed reasoning
- Educate users about craft techniques, materials, and what makes authentic work different from mass-produced copies

Available Products in our catalog:
{products_context if products_context else "Our catalog features various Indian handicrafts including paintings, textiles, pottery, jewelry, woodwork, and more."}

Communication style:
- Speak with the AUTHORITY and DEPTH of a true master — share specific examples, name actual villages, reference real techniques
- Be warm and passionate — you genuinely love these crafts and the people who make them
- Give ACTIONABLE, SPECIFIC advice — not generic tips. E.g., "Photograph your Madhubani on a raw jute background at 45° angle with natural morning light" not just "take good photos"
- When recommending products, explain WHY in terms of craftsmanship quality, cultural significance, and investment value
- Use markdown formatting with **bold** for emphasis and bullet points for lists
- Keep responses focused and impactful (150-250 words)
- If you don't know something, be honest but offer a related insight from your vast experience
- Always highlight the artisan's skill, dedication, and the human story behind each piece"""

    # Groq
    groq_messages = [
        {'role': 'system', 'content': system_prompt},
    ]
    for msg in chat_history:
        groq_messages.append({
            'role': msg['role'] if msg['role'] in ('user', 'assistant') else 'user',
            'content': msg['content'],
        })
    groq_messages.append({'role': 'user', 'content': message})

    result = _groq_chat(groq_messages)
    if result:
        return result

    # Fallback
    return _chat_fallback(message)


def translate_content(content, target_language):
    """Translate product content to a target Indian language."""
    prompt = f"""Translate the following product description into {target_language}.
Use the native script of {target_language}.
Keep the tone warm, authentic, and appealing to buyers.
Preserve any product-specific terms that don't translate well.

Text to translate:
{content}

Return ONLY the translated text, nothing else."""
    result = _groq_text(prompt)
    return result or "Translation could not be generated. Please try again."


def generate_trend_suggestions(craft_type, art_form):
    """Suggest how to position a craft based on current market trends."""
    prompt = f"""As a market trend analyst for Indian handicrafts, suggest how to position this craft for modern consumers:

Craft Type: {craft_type}
Art Form: {art_form}

Provide:
1. **Current Trends** (3-4 trends this craft aligns with, e.g., sustainable living, maximalist decor)
2. **Target Audiences** (3 specific buyer personas with demographics)
3. **Positioning Angles** (3 ways to market this to modern buyers)
4. **Festival/Season Opportunities** (upcoming Indian festivals or seasons where this sells well)
5. **Cross-sell Ideas** (complementary products or bundles)

Format in clean markdown. Be specific and actionable."""

    result = _groq_text(prompt)
    return result or "Trend suggestions could not be generated. Please try again later."


def generate_craft_mentor_advice(artisan_name, craft_type, location, total_views, total_orders, total_wishlist, total_products, published_count, top_products_info, recent_orders_info, marketing_count):
    """
    AI Craft Mentor: Analyzes artisan's performance data and gives
    personalized, actionable business advice.
    """
    prompt = f"""You are KalaSetu's AI Craft Mentor — a world-class business coach who has helped 5,000+ Indian artisans grow their businesses. You combine deep knowledge of traditional Indian crafts with modern digital marketing and e-commerce expertise.

Analyze this artisan's complete performance data and provide a PERSONALIZED coaching report:

**Artisan Profile:**
- Name: {artisan_name}
- Craft: {craft_type}
- Location: {location}

**Performance Metrics:**
- Total Product Views: {total_views}
- Total Orders: {total_orders}
- Wishlist Saves: {total_wishlist}
- Total Products: {total_products}
- Published Products: {published_count}
- AI Marketing Content Generated: {marketing_count}

**Top Products (by views):**
{top_products_info}

**Recent Orders:**
{recent_orders_info}

**Your Analysis Must Include:**

1. **📊 Performance Score** — Rate the artisan 1-10 with a brief explanation. Be encouraging but honest.

2. **🔥 What's Working** — Identify 2-3 specific strengths based on the data. E.g., "Your eagle painting is your hero product with highest views — lean into wildlife art."

3. **⚡ Quick Wins (Do This Week)** — 3-4 specific, immediately actionable things. Not generic advice — reference their actual products and data. E.g., "You have {total_products - published_count} unpublished products — publish them NOW to increase discoverability."

4. **💰 Pricing Strategy** — Based on their craft type, order volume, and view-to-order ratio, suggest pricing adjustments. Be specific with numbers.

5. **📸 Product Photography Tips** — 2-3 specific tips for their craft type (e.g., for paintings: "Shoot at 45° angle with natural light on a jute/white background").

6. **📱 Marketing Playbook** — A 7-day social media plan tailored to their craft. Include specific post ideas, best times, and hashtag strategies.

7. **🎯 Growth Roadmap (Next 30 Days)** — 4-5 milestones with specific targets. E.g., "Week 1: Publish all draft products. Week 2: Generate Instagram posts for top 3 products."

8. **🌟 Opportunity Alert** — One unique insight or trend they should capitalize on. E.g., "Madhubani art is trending as corporate gifting — consider creating a 'corporate collection' with custom sizing."

**Rules:**
- Be SPECIFIC to this artisan — reference their actual products, numbers, and craft type
- Give actionable advice, not platitudes
- Use encouraging but frank tone — like a supportive mentor
- Format beautifully with markdown — headers, bullet points, bold text, emojis
- Keep total response to 600-800 words — dense and valuable"""

    result = _groq_chat([{'role': 'user', 'content': prompt}], max_tokens=2048)
    return result or "Mentoring advice could not be generated at this time. Please try again later."


def generate_heritage_story(product_title, art_form, category, materials, techniques, cultural_story, artisan_name, artisan_location, artisan_state):
    """
    Generate a rich, detailed cultural heritage narrative for a product.
    Covers the 500+ year history, village traditions, symbolism, and preservation story.
    """
    prompt = f"""You are a UNESCO cultural heritage expert and master storyteller who has spent 40 years documenting India's living craft traditions. You have visited every artisan village, learned from the oldest masters, and can trace the lineage of any Indian art form back centuries.

Create a RICH, IMMERSIVE heritage story for this product. This story will be displayed as a premium "Heritage Certificate" alongside the product — it should make buyers feel the centuries of tradition behind what they're purchasing.

**Product Details:**
- Title: {product_title}
- Art Form: {art_form or category}
- Materials: {materials or 'Traditional materials'}
- Techniques: {techniques or 'Handcrafted'}
- Artisan: {artisan_name} from {artisan_location}, {artisan_state}
{f'- Existing Cultural Context: {cultural_story}' if cultural_story else ''}

**Your Heritage Story Must Include:**

### 🏛️ Origins & History
- When and where did this art form originate? (Be specific — name centuries, dynasties, villages)
- What was its original purpose? (Ritual, royal patronage, daily life, trade?)
- How did it spread and evolve through different eras?

### 🎨 The Art & Technique
- Describe the creation process step-by-step as if watching the artisan at work
- What makes this technique unique compared to other crafts?
- What are the signature elements, motifs, and patterns? What do they symbolize?
- How long does it take to create a single piece?

### 🏘️ The Village & Community
- Describe the artisan community and how the craft is passed down through generations
- Paint a vivid picture of the village/region where this craft thrives
- What role do women/families play in maintaining this tradition?

### 🌍 Cultural Significance
- Why does this craft matter beyond aesthetics?
- How does it connect to India's identity, spirituality, or social fabric?
- What would the world lose if this craft tradition died out?

### 🔮 The Living Tradition
- How are artisans like {artisan_name} keeping this tradition alive today?
- How has the craft adapted to modern times while preserving its soul?
- Why buying this product matters — the impact on the artisan and community

**Rules:**
- Write in a compelling, narrative style — like a National Geographic feature
- Be historically accurate — use real dates, dynasties, and places
- Make the reader FEEL the weight of centuries in their hands
- Use vivid sensory descriptions — colors, textures, sounds of the workshop
- Format with markdown — headers, bold text, evocative paragraphs
- Total: 500-700 words — rich but readable
- End with a powerful line about why this craft deserves to be cherished"""

    result = _groq_chat([{'role': 'user', 'content': prompt}], max_tokens=2048)
    return result or "Heritage story could not be generated at this time. Please try again later."


def generate_festival_campaign(craft_type, art_form, product_titles, artisan_name, festival_name=None):
    """
    Generate a complete festival marketing campaign for an artisan.
    If festival_name is None, AI picks the best upcoming festivals.
    """
    products_list = "\n".join([f"- {t}" for t in product_titles[:8]]) or "- Various handcrafted products"

    prompt = f"""You are India's top festival marketing strategist for handcrafted goods, with 20+ years of experience helping artisans 10x their sales during festivals.

**Artisan:** {artisan_name}
**Craft Type:** {craft_type}
**Art Form:** {art_form or craft_type}
**Products:**
{products_list}

{f'**Target Festival:** {festival_name}' if festival_name else ''}

{'Generate a COMPLETE marketing campaign for ' + festival_name + '.' if festival_name else 'Identify the TOP 3 upcoming Indian festivals (from today onwards) that are BEST for selling this craft type, then generate campaigns for each.'}

**For EACH festival, provide:**

### 🎉 [Festival Name] — [Date]
**Why this festival?** — 2-3 lines explaining why this craft sells well during this festival

**📊 Demand Prediction:**
- Expected demand increase: X% (be specific based on craft type)
- Peak buying window: "Start posting X days before, peak orders X days before"
- Price strategy: "Can increase prices by X% during this period"

**📱 7-Day Social Media Countdown:**
| Day | Platform | Post Idea | Caption Hook | Best Time |
|-----|----------|-----------|-------------|-----------|
| Day 7 | Instagram | ... | ... | ... |
| Day 6 | Facebook | ... | ... | ... |
| ... | ... | ... | ... | ... |
| Day 1 | Instagram | ... | ... | ... |

**📝 Ready-to-Use Content (3 posts):**
1. **Instagram Post:** Complete caption with emojis + 15 hashtags
2. **Facebook Post:** Story-driven post connecting craft to festival
3. **WhatsApp Status:** Short, shareable message for WhatsApp broadcast

**🎁 Special Offers to Create:**
- Festival bundle idea (combine products)
- Limited edition concept
- Early bird / last-minute strategy

**🏷️ Hashtag Bank:** 20 festival-specific hashtags

**Rules:**
- Be SPECIFIC — name actual dates, specific post ideas, exact hashtags
- Reference the artisan's actual products by name
- Include Hindi/regional festival greetings where appropriate
- Format beautifully with markdown tables, headers, bold, emojis
- Make it so detailed that the artisan can just copy-paste and execute
- Total: 800-1200 words per festival"""

    result = _groq_chat([{'role': 'user', 'content': prompt}], max_tokens=4096)
    return result or "Festival campaign could not be generated at this time. Please try again later."