import io
import random
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from core.models import Artisan, Product


try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False


# Color palettes for placeholder images (warm Indian craft tones)
PALETTES = [
    [(230, 81, 0), (255, 143, 0)],     # Deep orange → amber
    [(183, 28, 28), (255, 82, 82)],     # Deep red → coral
    [(27, 94, 32), (129, 199, 132)],    # Forest → sage
    [(13, 71, 161), (100, 181, 246)],   # Navy → sky
    [(74, 20, 140), (186, 104, 200)],   # Purple → lavender
    [(62, 39, 35), (188, 170, 164)],    # Earth brown → beige
    [(0, 96, 100), (128, 203, 196)],    # Teal → mint
    [(230, 74, 25), (255, 183, 77)],    # Burnt orange → gold
]


def make_placeholder(width, height, text, palette_idx=0):
    """Generate a gradient placeholder image with text overlay."""
    if not HAS_PILLOW:
        # Return a minimal valid JPEG if Pillow is not installed
        return _minimal_jpeg()

    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)
    c1, c2 = PALETTES[palette_idx % len(PALETTES)]

    for y in range(height):
        r = int(c1[0] + (c2[0] - c1[0]) * y / height)
        g = int(c1[1] + (c2[1] - c1[1]) * y / height)
        b = int(c1[2] + (c2[2] - c1[2]) * y / height)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Add pattern dots
    for _ in range(30):
        x = random.randint(0, width)
        y = random.randint(0, height)
        r = random.randint(3, 12)
        draw.ellipse([x - r, y - r, x + r, y + r],
                     fill=(255, 255, 255, 40), outline=None)

    # Add text
    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((width - tw) // 2, (height - th) // 2), text,
              fill=(255, 255, 255), font=font)

    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=85)
    return buf.getvalue()


def _minimal_jpeg():
    """Return a 1x1 white JPEG as fallback."""
    import struct
    # Minimal valid JPEG binary
    return (
        b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
        b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
        b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
        b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342'
        b'\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00'
        b'\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b'
        b'\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04'
        b'\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa'
        b'\x07"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n'
        b'\x16\x17\x18\x19\x1a%&\'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz'
        b'\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99'
        b'\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7'
        b'\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5'
        b'\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1'
        b'\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa'
        b'\xff\xda\x00\x08\x01\x01\x00\x00?\x00T\xdb\x9e\xa7\xa3@\x1f\xff\xd9'
    )


ARTISANS = [
    {
        'name': 'Priya Devi',
        'location': 'Madhubani, Bihar',
        'state': 'Bihar',
        'language': 'Hindi',
        'craft_type': 'Madhubani Painting',
        'story': 'I learned Madhubani art from my grandmother when I was just 8 years old. Every painting I create carries forward the tradition of five generations of women in my family. My art depicts stories from the Ramayana and everyday village life using natural dyes made from flowers and tree bark.',
        'bio': 'Priya Devi is a master Madhubani artist from Bihar whose work has been celebrated for its intricate geometric patterns and vibrant natural dyes. With over 20 years of practice, she creates stunning pieces that bridge ancient Mithila traditions with contemporary aesthetics.',
    },
    {
        'name': 'Ramesh Joshi',
        'location': 'Jaipur, Rajasthan',
        'state': 'Rajasthan',
        'language': 'Hindi',
        'craft_type': 'Blue Pottery',
        'story': 'My family has been making blue pottery in Jaipur for four generations. The technique originally came from Persia and Central Asia. We use quartz stone powder instead of clay, which gives our pottery its unique translucent quality. Each piece is hand-painted with Persian-inspired floral motifs.',
        'bio': 'Ramesh Joshi is a fourth-generation blue pottery artisan from Jaipur. His work is distinguished by intricate turquoise and cobalt patterns inspired by Persian traditions that have been absorbed into Rajasthani culture over centuries.',
    },
    {
        'name': 'Lakshmi Naidu',
        'location': 'Srikalahasti, Andhra Pradesh',
        'state': 'Andhra Pradesh',
        'language': 'Telugu',
        'craft_type': 'Kalamkari Art',
        'story': 'Kalamkari means "pen work" — I use a bamboo pen dipped in natural dyes to paint mythological scenes on cotton cloth. The process involves 17 steps and uses only vegetable dyes from indigo, pomegranate, and myrobalan. My art tells the stories of Lord Krishna and the Mahabharata.',
        'bio': 'Lakshmi Naidu is a celebrated Kalamkari artist from Srikalahasti, Andhra Pradesh. Her hand-drawn textile art uses ancient 17-step natural dyeing processes to create stunning mythological narratives on cotton fabric.',
    },
    {
        'name': 'Suresh Warli',
        'location': 'Dahanu, Maharashtra',
        'state': 'Maharashtra',
        'language': 'Marathi',
        'craft_type': 'Warli Art',
        'story': 'I belong to the Warli tribe in the Sahyadri mountains. Our art is over 2,500 years old — we paint with rice paste on mud walls during festivals and weddings. Now I create Warli art on canvas and paper to share our tribal stories with the world. Every figure represents our daily life — farming, dancing, and celebrating nature.',
        'bio': 'Suresh Warli is a tribal artist from Maharashtra who brings the ancient 2,500-year-old Warli art tradition to modern canvases. His minimalist compositions of geometric figures capture the rhythm of tribal life in the Western Ghats.',
    },
    {
        'name': 'Meena Kumari',
        'location': 'Lucknow, Uttar Pradesh',
        'state': 'Uttar Pradesh',
        'language': 'Hindi',
        'craft_type': 'Chikankari Embroidery',
        'story': 'Chikankari is Lucknow\'s gift to the world of textiles. I embroider delicate white-on-white patterns on muslin cloth using 36 traditional stitches. The craft was patronized by the Mughal court and every piece I create takes weeks of patient hand-stitching. My embroidery tells stories through flowers, paisleys, and geometric patterns.',
        'bio': 'Meena Kumari is a master Chikankari artisan from the heart of Lucknow. Her exquisite white-on-white embroidery on fine muslin upholds a Mughal-era tradition that transforms simple cloth into wearable art.',
    },
    {
        'name': 'Arjun Dhokra',
        'location': 'Bastar, Chhattisgarh',
        'state': 'Chhattisgarh',
        'language': 'Hindi',
        'craft_type': 'Dhokra Metalwork',
        'story': 'Dhokra is one of the oldest metal casting techniques in the world — over 4,000 years old. I use the lost-wax method to create brass figurines of tribal gods, animals, and everyday life. Every piece is unique because the wax mold is destroyed during casting. My art connects the ancient Indus Valley civilization to the modern world.',
        'bio': 'Arjun Dhokra is a Bastar tribal metalworker who practices the 4,000-year-old lost-wax Dhokra casting technique. His brass figurines are one-of-a-kind pieces that carry the artistic DNA of the Indus Valley civilization.',
    },
]


PRODUCTS = [
    # Priya Devi's products
    {
        'artisan_idx': 0,
        'title': 'Madhubani Tree of Life — Natural Dyes on Handmade Paper',
        'description': 'A stunning depiction of the sacred Tree of Life in traditional Madhubani style. Painted using natural dyes extracted from marigold flowers, indigo leaves, and turmeric root on handmade Nepali lokta paper. The intricate geometric patterns represent the interconnectedness of all living beings.',
        'cultural_story': 'The Tree of Life is a central motif in Mithila art, symbolizing the cosmic connection between heaven and earth. In the Madhubani tradition, this motif has been painted on the walls of homes during weddings and festivals for centuries, representing fertility, prosperity, and the eternal cycle of life.',
        'category': 'painting',
        'art_form': 'Madhubani',
        'materials': 'Handmade lokta paper, natural dyes (indigo, turmeric, marigold)',
        'techniques': 'Fine-line Kachni style, natural pigment preparation, hand-painting',
        'price': 3500,
        'suggested_price': 3500,
        'tags': 'madhubani,tree of life,bihar art,natural dyes,indian painting,wall art,traditional',
    },
    {
        'artisan_idx': 0,
        'title': 'Madhubani Fish Motif — Wedding Blessing Panel',
        'description': 'A vibrant Madhubani painting featuring the sacred fish motif, traditionally created for wedding ceremonies. The fish represents fertility, good luck, and the flowing nature of life. Painted with bold geometric borders and floral patterns in the Bharni (filled) style.',
        'cultural_story': 'In Mithila culture, the fish is considered the most auspicious symbol. Brides paint fish motifs on their kohbar (bridal chamber) walls to invoke blessings for a prosperous married life. This tradition has been unbroken for over a thousand years.',
        'category': 'painting',
        'art_form': 'Madhubani',
        'materials': 'Cotton canvas, acrylic paint, natural pigments',
        'techniques': 'Bharni (filled) style, double-line border technique',
        'price': 2800,
        'suggested_price': 2800,
        'tags': 'madhubani,fish motif,wedding art,bihar,indian painting,auspicious',
    },
    # Ramesh Joshi's products
    {
        'artisan_idx': 1,
        'title': 'Jaipur Blue Pottery Vase — Persian Floral Design',
        'description': 'An exquisite hand-painted blue pottery vase featuring intricate Persian-inspired floral patterns in cobalt blue and turquoise on a pristine white base. Made using the traditional quartz stone powder technique unique to Jaipur blue pottery.',
        'cultural_story': 'Blue pottery arrived in Jaipur from Persia via Mughal trade routes in the 14th century. Unlike traditional Indian pottery made from clay, blue pottery uses quartz stone powder, powdered glass, and multani mitti. This makes each piece remarkably lightweight and gives it a distinctive translucent quality.',
        'category': 'pottery',
        'art_form': 'Blue Pottery',
        'materials': 'Quartz stone powder, powdered glass, multani mitti, cobalt oxide',
        'techniques': 'Slab-building, hand-painting, low-fire glazing',
        'price': 1800,
        'suggested_price': 1800,
        'tags': 'blue pottery,jaipur,rajasthan,persian design,home decor,vase,handmade',
    },
    {
        'artisan_idx': 1,
        'title': 'Blue Pottery Decorative Plate Set — Lotus Garden',
        'description': 'A set of three hand-painted decorative plates featuring lotus flowers and intertwining vines in the classic Jaipur blue pottery style. Perfect for wall display or as serving pieces for special occasions.',
        'cultural_story': 'The lotus is one of the most sacred symbols in Indian art, representing purity and divine beauty. In blue pottery tradition, the lotus is painted with flowing vine patterns that represent the infinite garden of paradise — a motif that has traveled from Persian royal courts to Rajasthani workshops.',
        'category': 'pottery',
        'art_form': 'Blue Pottery',
        'materials': 'Quartz powder composite, food-safe glaze, cobalt and turquoise pigments',
        'techniques': 'Press-molding, freehand painting, double-fired glaze',
        'price': 4200,
        'suggested_price': 4200,
        'tags': 'blue pottery,plate set,jaipur,lotus,wall decor,serving,rajasthan',
    },
    # Lakshmi Naidu's products
    {
        'artisan_idx': 2,
        'title': 'Kalamkari Wall Hanging — Krishna Leela',
        'description': 'A magnificent hand-painted Kalamkari wall hanging depicting scenes from Krishna Leela — the divine play of Lord Krishna. Created using a bamboo pen (kalam) and natural vegetable dyes through the traditional 17-step process including bleaching, dyeing, and hand-painting.',
        'cultural_story': 'Srikalahasti Kalamkari has been practiced for over 3,000 years. Temple scrolls depicting Hindu mythology were used to narrate stories to devotees. This particular piece follows the ancient tradition of "vritchi" — a narrative scroll that unfolds the story of Krishna from his birth to the Ras Leela.',
        'category': 'textile',
        'art_form': 'Kalamkari',
        'materials': 'Handspun cotton, natural dyes (indigo, pomegranate, iron rust, myrobalan)',
        'techniques': 'Hand-drawing with bamboo pen, 17-step natural dyeing, mordant printing',
        'price': 8500,
        'suggested_price': 8500,
        'tags': 'kalamkari,wall hanging,krishna,andhra pradesh,textile art,natural dyes',
    },
    # Suresh Warli's products
    {
        'artisan_idx': 3,
        'title': 'Warli Art — Village Harvest Festival',
        'description': 'A large Warli painting on canvas depicting a vibrant harvest festival scene. The characteristic white-on-brown composition shows villagers dancing the tarpa dance in a circle, surrounded by rice paddy fields, bullocks, and the sacred banyan tree.',
        'cultural_story': 'Warli art is one of the oldest art forms in India, dating back to 2500 BCE. The Warli tribe paints these scenes using rice paste on mud walls during festivals like Diwali and wedding ceremonies. The circular tarpa dance motif is central to Warli art — it represents the unity of the community moving in harmony with nature.',
        'category': 'painting',
        'art_form': 'Warli',
        'materials': 'Canvas, rice paste paint, natural earth pigments',
        'techniques': 'Traditional Warli line-drawing, rice paste preparation, geometric composition',
        'price': 4500,
        'suggested_price': 4500,
        'tags': 'warli,tribal art,maharashtra,harvest festival,canvas painting,folk art',
    },
    {
        'artisan_idx': 3,
        'title': 'Warli Art Coaster Set — Daily Life Motifs',
        'description': 'A charming set of four hand-painted wooden coasters featuring Warli motifs of daily tribal life — farming, cooking, dancing, and fishing. Each coaster tells a different story of the Warli community\'s connection to nature.',
        'cultural_story': 'Every Warli motif is a visual language: the triangle represents mountains and trees, the circle is the sun and moon, and the square is the sacred enclosure. These simple shapes combine to tell complex stories of a community living in deep harmony with their environment.',
        'category': 'woodwork',
        'art_form': 'Warli',
        'materials': 'Seasoned teak wood, acrylic paint, food-safe varnish',
        'techniques': 'Wood cutting, hand-painting, protective coating',
        'price': 650,
        'suggested_price': 650,
        'tags': 'warli,coasters,woodwork,home decor,gift,tribal art,maharashtra',
    },
    # Meena Kumari's products
    {
        'artisan_idx': 4,
        'title': 'Chikankari Hand-Embroidered Cotton Kurta — Floral Jaal',
        'description': 'An exquisite white-on-white Chikankari kurta featuring the intricate "jaal" (net) pattern with delicate floral motifs. Hand-embroidered on fine cotton muslin using traditional shadow-work and satin stitches that create a beautiful play of light and texture.',
        'cultural_story': 'Chikankari was introduced to Lucknow by Noor Jahan, the Mughal empress, in the 17th century. The craft involves 36 different types of stitches, each with its own name and technique. The "jaal" pattern used here creates an all-over net of flowers that appears to float above the fabric — a testament to the extraordinary skill of Lucknawi artisans.',
        'category': 'embroidery',
        'art_form': 'Chikankari',
        'materials': 'Fine cotton muslin, cotton embroidery thread',
        'techniques': 'Shadow work (tepchi), satin stitch (murri), jaal pattern, hand-washing',
        'price': 3200,
        'suggested_price': 3200,
        'tags': 'chikankari,lucknow,embroidery,kurta,white,cotton,mughal,handmade',
    },
    # Arjun Dhokra's products
    {
        'artisan_idx': 5,
        'title': 'Dhokra Brass Elephant — Tribal Lost-Wax Casting',
        'description': 'A majestic brass elephant figurine created using the ancient Dhokra lost-wax casting technique. The elephant is adorned with traditional tribal patterns and geometric designs that are characteristic of Bastar metalwork. Each piece is truly one-of-a-kind as the wax mold is destroyed during casting.',
        'cultural_story': 'The Dhokra technique is over 4,000 years old — the famous Dancing Girl of Mohenjo-daro was made using the same lost-wax method. Bastar tribals believe that metal figurines house spirits of their ancestors. The elephant, revered as Ganesha\'s form, symbolizes wisdom, strength, and the removal of obstacles.',
        'category': 'metalwork',
        'art_form': 'Dhokra',
        'materials': 'Brass (copper and zinc alloy), beeswax, clay, rice husk ash',
        'techniques': 'Lost-wax casting (cire perdue), hand-sculpting, patina finishing',
        'price': 5500,
        'suggested_price': 5500,
        'tags': 'dhokra,brass,elephant,tribal art,bastar,chhattisgarh,metalwork,figurine',
    },
    {
        'artisan_idx': 5,
        'title': 'Dhokra Tribal Musician Set — Three Figurines',
        'description': 'A captivating set of three Dhokra brass figurines depicting tribal musicians playing the dhol, bansuri (flute), and mandar drum. The wire-textured surface and dynamic poses capture the energy and rhythm of Bastar tribal music and dance celebrations.',
        'cultural_story': 'Music and dance are the heartbeat of Bastar tribal life. During festivals like Madai and Dussehra, the air fills with the sound of drums and flutes as the entire community comes together. These figurines celebrate that living tradition — each musician frozen in a moment of pure creative expression.',
        'category': 'metalwork',
        'art_form': 'Dhokra',
        'materials': 'Brass alloy, beeswax wire work, clay core',
        'techniques': 'Lost-wax casting, wire-wrapping texture, acid patina',
        'price': 7800,
        'suggested_price': 7800,
        'tags': 'dhokra,brass,musicians,figurine set,tribal,bastar,gift,home decor',
    },
]


class Command(BaseCommand):
    help = 'Seed the database with sample artisans and products for demo'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Clear existing data before seeding')

    def handle(self, *args, **options):
        if options['clear']:
            Product.objects.all().delete()
            Artisan.objects.all().delete()
            self.stdout.write(self.style.WARNING('Cleared existing data.'))

        # Check for existing data
        if Artisan.objects.exists():
            self.stdout.write(self.style.NOTICE('Data already exists. Use --clear to reset.'))
            return

        self.stdout.write('Seeding artisans...')
        artisan_objs = []
        for i, data in enumerate(ARTISANS):
            artisan = Artisan(
                name=data['name'],
                location=data['location'],
                state=data['state'],
                language=data['language'],
                craft_type=data['craft_type'],
                story=data['story'],
                bio=data['bio'],
            )
            # Generate artisan photo placeholder
            img_bytes = make_placeholder(400, 400, data['name'], i)
            artisan.photo.save(
                f"artisan_{i}.jpg",
                ContentFile(img_bytes),
                save=False,
            )
            artisan.save()
            artisan_objs.append(artisan)
            self.stdout.write(f'  + {artisan.name} ({artisan.craft_type})')

        self.stdout.write('Seeding products...')
        for j, data in enumerate(PRODUCTS):
            artisan = artisan_objs[data['artisan_idx']]
            product = Product(
                artisan=artisan,
                title=data['title'],
                description=data['description'],
                cultural_story=data['cultural_story'],
                category=data['category'],
                art_form=data['art_form'],
                materials=data['materials'],
                techniques=data['techniques'],
                price=data['price'],
                suggested_price=data['suggested_price'],
                tags=data['tags'],
                is_published=True,
            )
            img_bytes = make_placeholder(800, 600, data['art_form'], j)
            product.image.save(
                f"product_{j}.jpg",
                ContentFile(img_bytes),
                save=False,
            )
            product.save()
            self.stdout.write(f'  + {product.title[:60]}...')

        self.stdout.write(self.style.SUCCESS(
            f'\nDone! Created {len(artisan_objs)} artisans and {len(PRODUCTS)} products.'
        ))
