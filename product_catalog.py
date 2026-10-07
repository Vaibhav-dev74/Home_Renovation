"""Real-Time Product Catalog & Spatial Marketplace Engine.

Provides real-time product data with physical dimensions (W x D x H in inches/feet),
market pricing (INR and USD), retailer availability by city/country (IKEA, Kohler,
Pepperfry, Home Depot, etc.), and spatial clearance validation for 3D/VR layouts.
"""

from typing import List, Optional, Dict, Any, Tuple
import uuid
from models import Product, ProductDimension, PlacedItem, RoomLayout3D, Currency


def make_dim(w_in: float, d_in: float, h_in: float) -> ProductDimension:
    """Helper to construct ProductDimension with both inches and feet."""
    return ProductDimension(
        width_in=w_in,
        depth_in=d_in,
        height_in=h_in,
        width_ft=round(w_in / 12.0, 2),
        depth_ft=round(d_in / 12.0, 2),
        height_ft=round(h_in / 12.0, 2),
    )


# Catalog of real-world renovation products with authentic dimensions and retailer availability
PRODUCT_DATABASE: List[Product] = [
    # ------------------------------------------------------------------------
    # 1. Kitchen Cabinetry & Islands
    # ------------------------------------------------------------------------
    Product(
        product_id="prod-ikea-sektion-island",
        name="IKEA SEKTION Kitchen Island with Quartz Top",
        category="Cabinetry",
        room_types=["kitchen"],
        brand_or_retailer="IKEA",
        location_availability="India (Bengaluru, Mumbai, Hyderabad) & US Nationwide",
        country="Global",
        price=48500.0,
        currency=Currency.INR,
        dimensions=make_dim(w_in=72.0, d_in=36.0, h_in=36.0),
        material="MDF with Quartz Countertop",
        color="Matte Anthracite / White Oak",
        color_hex="#2d3748",
        product_url="https://www.ikea.com",
        in_stock=True,
        rating=4.7,
        image_icon="🏝️",
    ),
    Product(
        product_id="prod-livspace-base-cab",
        name="Livspace Modular 3-Drawer Base Cabinet Unit",
        category="Cabinetry",
        room_types=["kitchen"],
        brand_or_retailer="Livspace",
        location_availability="India (Bengaluru, Delhi NCR, Mumbai, Pune, Chennai)",
        country="India",
        price=18500.0,
        currency=Currency.INR,
        dimensions=make_dim(w_in=36.0, d_in=24.0, h_in=34.5),
        material="BWR Marine Plywood with Soft-Close Blum Runners",
        color="Sage Green Acrylic",
        color_hex="#87a987",
        product_url="https://www.livspace.com",
        in_stock=True,
        rating=4.6,
        image_icon="🗄️",
    ),
    Product(
        product_id="prod-hd-hampton-cab",
        name="Hampton Bay Shaker Assembled Base Cabinet",
        category="Cabinetry",
        room_types=["kitchen"],
        brand_or_retailer="The Home Depot",
        location_availability="Austin, TX & US Nationwide",
        country="US",
        price=319.0,
        currency=Currency.USD,
        dimensions=make_dim(w_in=36.0, d_in=24.0, h_in=34.5),
        material="Solid Hardwood Face Frame with Plywood Box",
        color="Satin White",
        color_hex="#f8fafc",
        product_url="https://www.homedepot.com",
        in_stock=True,
        rating=4.5,
        image_icon="🗄️",
    ),

    # ------------------------------------------------------------------------
    # 2. Kitchen Appliances
    # ------------------------------------------------------------------------
    Product(
        product_id="prod-samsung-french-fridge",
        name="Samsung 28 cu. ft. Smart French Door Refrigerator",
        category="Appliance",
        room_types=["kitchen"],
        brand_or_retailer="Samsung / Reliance Digital / Home Depot",
        location_availability="India (All Metros) & US Nationwide",
        country="Global",
        price=115000.0,
        currency=Currency.INR,
        dimensions=make_dim(w_in=35.75, d_in=34.0, h_in=70.0),
        material="Fingerprint Resistant Stainless Steel",
        color="Stainless Steel",
        color_hex="#cbd5e1",
        product_url="https://www.samsung.com",
        in_stock=True,
        rating=4.8,
        image_icon="🧊",
    ),
    Product(
        product_id="prod-bosch-induction-cooktop",
        name="Bosch Serie 6 80cm Built-in Induction Cooktop",
        category="Appliance",
        room_types=["kitchen"],
        brand_or_retailer="Bosch Home Appliances",
        location_availability="Bengaluru, Mumbai, Delhi & US Major Hubs",
        country="Global",
        price=62000.0,
        currency=Currency.INR,
        dimensions=make_dim(w_in=31.5, d_in=20.5, h_in=2.5),
        material="Schott Ceran Glass with Touch Controls",
        color="Black Glass",
        color_hex="#0f172a",
        product_url="https://www.bosch-home.in",
        in_stock=True,
        rating=4.9,
        image_icon="🍳",
    ),

    # ------------------------------------------------------------------------
    # 3. Sanitaryware, Sinks & Bathroom Fixtures
    # ------------------------------------------------------------------------
    Product(
        product_id="prod-kohler-prolific-sink",
        name="Kohler Prolific 33-inch Undermount Workstation Sink",
        category="Sanitaryware & Fixtures",
        room_types=["kitchen"],
        brand_or_retailer="Kohler Experience Center",
        location_availability="Mumbai, Delhi, Bengaluru & Austin, TX (US)",
        country="Global",
        price=42000.0,
        currency=Currency.INR,
        dimensions=make_dim(w_in=33.0, d_in=18.0, h_in=10.0),
        material="18-Gauge Premium Stainless Steel",
        color="Brushed Stainless",
        color_hex="#94a3b8",
        product_url="https://www.kohler.com",
        in_stock=True,
        rating=4.8,
        image_icon="🚰",
    ),
    Product(
        product_id="prod-kohler-veil-toilet",
        name="Kohler Veil Wall-Hung Intelligent Toilet with In-Wall Tank",
        category="Sanitaryware & Fixtures",
        room_types=["bathroom"],
        brand_or_retailer="Kohler India",
        location_availability="Bengaluru, Mumbai, Hyderabad, Delhi NCR",
        country="India",
        price=85000.0,
        currency=Currency.INR,
        dimensions=make_dim(w_in=15.5, d_in=26.5, h_in=16.0),
        material="Vitreous China with Dual-Flush Concealed Carrier",
        color="Gloss White",
        color_hex="#ffffff",
        product_url="https://www.kohler.co.in",
        in_stock=True,
        rating=4.9,
        image_icon="🚽",
    ),
    Product(
        product_id="prod-pepperfry-vanity",
        name="Pepperfry 48-inch Floating Teak Wood Bathroom Vanity",
        category="Sanitaryware & Fixtures",
        room_types=["bathroom"],
        brand_or_retailer="Pepperfry Studio",
        location_availability="Delhi, Mumbai, Bengaluru, Pune, Hyderabad",
        country="India",
        price=34999.0,
        currency=Currency.INR,
        dimensions=make_dim(w_in=48.0, d_in=21.0, h_in=22.0),
        material="Solid Teak Wood with Ceramic Basin & Soft-close Drawers",
        color="Natural Honey Teak",
        color_hex="#b45309",
        product_url="https://www.pepperfry.com",
        in_stock=True,
        rating=4.7,
        image_icon="🪞",
    ),
    Product(
        product_id="prod-hd-glacier-vanity",
        name="Glacier Bay 60-inch Double Sink Freestanding Vanity",
        category="Sanitaryware & Fixtures",
        room_types=["bathroom"],
        brand_or_retailer="The Home Depot",
        location_availability="Austin, TX & US Nationwide",
        country="US",
        price=899.0,
        currency=Currency.USD,
        dimensions=make_dim(w_in=60.0, d_in=22.0, h_in=34.5),
        material="Engineered Stone Top with Solid Wood Legs",
        color="Midnight Navy / Carrara Marble",
        color_hex="#1e3a8a",
        product_url="https://www.homedepot.com",
        in_stock=True,
        rating=4.6,
        image_icon="🪞",
    ),

    # ------------------------------------------------------------------------
    # 4. Furniture (Dining, Living & Bedroom)
    # ------------------------------------------------------------------------
    Product(
        product_id="prod-urban-ladder-dining",
        name="Urban Ladder 6-Seater Solid Sheesham Wood Dining Table",
        category="Furniture",
        room_types=["dining_room", "kitchen", "living_room"],
        brand_or_retailer="Urban Ladder",
        location_availability="India (Bengaluru, Mumbai, Delhi NCR, Chennai)",
        country="India",
        price=29999.0,
        currency=Currency.INR,
        dimensions=make_dim(w_in=68.0, d_in=36.0, h_in=30.0),
        material="100% Solid Sheesham Wood with Matte Lacquer",
        color="Warm Walnut",
        color_hex="#78350f",
        product_url="https://www.urbanladder.com",
        in_stock=True,
        rating=4.7,
        image_icon="🪑",
    ),
    Product(
        product_id="prod-ikea-kivik-sofa",
        name="IKEA KIVIK 3-Seat Deep Minimalist Lounge Sofa",
        category="Furniture",
        room_types=["living_room"],
        brand_or_retailer="IKEA",
        location_availability="Bengaluru, Hyderabad, Mumbai & US Nationwide",
        country="Global",
        price=42990.0,
        currency=Currency.INR,
        dimensions=make_dim(w_in=89.75, d_in=37.3, h_in=32.6),
        material="Pocket Spring Core with Washable Heavy Cotton Cover",
        color="Gunnared Medium Grey",
        color_hex="#475569",
        product_url="https://www.ikea.com",
        in_stock=True,
        rating=4.6,
        image_icon="🛋️",
    ),
    Product(
        product_id="prod-pepperfry-wardrobe",
        name="Woodsworth 4-Door Teak Finish Sliding Wardrobe with Mirror",
        category="Furniture",
        room_types=["bedroom", "master_bedroom"],
        brand_or_retailer="Pepperfry",
        location_availability="India Nationwide Delivery",
        country="India",
        price=54000.0,
        currency=Currency.INR,
        dimensions=make_dim(w_in=72.0, d_in=24.0, h_in=84.0),
        material="Engineered Wood with High-Grade Melamine Lamination",
        color="Columbian Walnut",
        color_hex="#5c3822",
        product_url="https://www.pepperfry.com",
        in_stock=True,
        rating=4.5,
        image_icon="🚪",
    ),

    # ------------------------------------------------------------------------
    # 5. Lighting
    # ------------------------------------------------------------------------
    Product(
        product_id="prod-philips-hue-recessed",
        name="Philips Hue White & Color Ambiance Slim LED Downlights (Pack of 4)",
        category="Lighting",
        room_types=["kitchen", "bathroom", "living_room", "bedroom"],
        brand_or_retailer="Philips Lighting / Amazon / Home Depot",
        location_availability="India Nationwide & US Nationwide",
        country="Global",
        price=14999.0,
        currency=Currency.INR,
        dimensions=make_dim(w_in=6.0, d_in=6.0, h_in=1.5),
        material="Die-cast Aluminum Housing with Wireless Zigbee Controller",
        color="Warm-to-Cool White & 16M Colors",
        color_hex="#fef08a",
        product_url="https://www.philips-hue.com",
        in_stock=True,
        rating=4.8,
        image_icon="💡",
    ),
    Product(
        product_id="prod-brass-pendant-light",
        name="Modern Architectural Cone Brass Island Pendant",
        category="Lighting",
        room_types=["kitchen", "dining_room"],
        brand_or_retailer="West Elm / Pepperfry",
        location_availability="Mumbai, Delhi, Bengaluru & Austin, TX",
        country="Global",
        price=8500.0,
        currency=Currency.INR,
        dimensions=make_dim(w_in=14.0, d_in=14.0, h_in=18.0),
        material="Spun Brass with Matte Black Canopy Cord",
        color="Brushed Satin Brass",
        color_hex="#eab308",
        product_url="https://www.westelm.com",
        in_stock=True,
        rating=4.7,
        image_icon="✨",
    ),
]


def get_all_products(
    category: Optional[str] = None,
    location: Optional[str] = None,
    country: Optional[str] = None,
    room_type: Optional[str] = None,
    search: Optional[str] = None,
) -> List[Product]:
    """Filters products by category, geographic location/country, room type, or search term."""
    results = []
    
    loc_lower = (location or "").lower()
    search_lower = (search or "").lower()
    cat_lower = (category or "").lower()
    room_lower = (room_type or "").lower()

    # Determine country filter from location string
    inferred_country = country
    if not inferred_country and location:
        if any(w in loc_lower for w in ["india", "bengaluru", "bangalore", "mumbai", "delhi", "pune", "hyderabad", "chennai"]):
            inferred_country = "India"
        elif any(w in loc_lower for w in ["us", "usa", "austin", "texas", "tx", "california", "ca", "ny", "york", "san francisco"]):
            inferred_country = "US"

    for p in PRODUCT_DATABASE:
        # Category filter
        if cat_lower and cat_lower != "all" and cat_lower not in p.category.lower():
            continue
        
        # Room type filter
        if room_lower and room_lower not in [r.lower() for r in p.room_types]:
            continue

        # Country filter
        if inferred_country:
            if p.country != "Global" and p.country.lower() != inferred_country.lower():
                continue

        # Keyword search filter
        if search_lower:
            text_haystack = f"{p.name} {p.brand_or_retailer} {p.category} {p.material} {p.color} {p.location_availability}".lower()
            if search_lower not in text_haystack:
                continue

        results.append(p)

    return results


def get_product_by_id(product_id: str) -> Optional[Product]:
    """Retrieves a product by exact ID."""
    for p in PRODUCT_DATABASE:
        if p.product_id == product_id:
            return p
    return None


def create_placed_item_from_product(
    product: Product,
    x: float = 0.0,
    z: float = 0.0,
    rotation_deg: float = 0.0,
    item_id: Optional[str] = None,
) -> PlacedItem:
    """Instantiates a product as a placed 3D room object with real physical dimensions."""
    return PlacedItem(
        item_id=item_id or f"item-{uuid.uuid4().hex[:6]}",
        product_id=product.product_id,
        name=product.name,
        category=product.category,
        x=round(x, 2),
        z=round(z, 2),
        y=0.0,
        rotation_deg=rotation_deg,
        width_ft=product.dimensions.width_ft,
        depth_ft=product.dimensions.depth_ft,
        height_ft=product.dimensions.height_ft,
        color_hex=product.color_hex,
        price=product.price,
        currency=product.currency,
        brand_or_retailer=product.brand_or_retailer,
        location_availability=product.location_availability,
    )


def validate_room_layout_clearance(layout: RoomLayout3D) -> Tuple[bool, List[str]]:
    """Calculates clearance distances and detects boundary or item collisions."""
    warnings = []
    half_w = layout.room_width_ft / 2.0
    half_l = layout.room_length_ft / 2.0

    items = layout.placed_items

    # 1. Check Wall Boundary Violations
    for it in items:
        # Approximate item footprint
        it_half_w = it.width_ft / 2.0
        it_half_d = it.depth_ft / 2.0

        if (abs(it.x) + it_half_w) > half_w + 0.1:
            warnings.append(f"⚠️ '{it.name}' extends beyond the room's width boundary ({layout.room_width_ft} ft wide).")
        if (abs(it.z) + it_half_d) > half_l + 0.1:
            warnings.append(f"⚠️ '{it.name}' extends beyond the room's length boundary ({layout.room_length_ft} ft long).")

    # 2. Check Inter-Item Collision / Clearance
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a = items[i]
            b = items[j]

            # Approximate center-to-center distance
            dx = abs(a.x - b.x)
            dz = abs(a.z - b.z)

            min_dist_x = (a.width_ft + b.width_ft) / 2.0
            min_dist_z = (a.depth_ft + b.depth_ft) / 2.0

            # Direct overlap collision
            if dx < (min_dist_x - 0.2) and dz < (min_dist_z - 0.2):
                warnings.append(f"🚨 CLASH: '{a.name}' physically overlaps with '{b.name}'!")
            # Walkway clearance warning (less than 3 feet walkway)
            elif dx < (min_dist_x + 2.5) and dz < (min_dist_z + 2.5):
                gap_x = max(0.0, dx - min_dist_x)
                gap_z = max(0.0, dz - min_dist_z)
                approx_aisle = round(min(gap_x, gap_z), 1)
                if 0.1 < approx_aisle < 2.5:
                    warnings.append(f"⚠️ Tight Walkway: Only ~{approx_aisle * 12:.0f} inches between '{a.name}' and '{b.name}'. (Recommended standard aisle: 36–42 inches).")

    is_valid = len([w for w in warnings if "CLASH" in w]) == 0
    return is_valid, warnings


def get_available_categories() -> List[str]:
    """Returns unique sorted list of product categories in catalog."""
    cats = {p.category for p in PRODUCT_DATABASE}
    return sorted(list(cats))


def get_available_locations() -> List[Dict[str, str]]:
    """Returns curated list of supported metropolitan locations with country and currency."""
    return [
        {"id": "bengaluru", "name": "Bengaluru, India", "country": "India", "currency": "INR"},
        {"id": "mumbai", "name": "Mumbai, India", "country": "India", "currency": "INR"},
        {"id": "delhi", "name": "Delhi NCR, India", "country": "India", "currency": "INR"},
        {"id": "hyderabad", "name": "Hyderabad, India", "country": "India", "currency": "INR"},
        {"id": "pune", "name": "Pune, India", "country": "India", "currency": "INR"},
        {"id": "austin", "name": "Austin, TX (USA)", "country": "US", "currency": "USD"},
        {"id": "sf", "name": "San Francisco, CA (USA)", "country": "US", "currency": "USD"},
        {"id": "nyc", "name": "New York, NY (USA)", "country": "US", "currency": "USD"},
        {"id": "seattle", "name": "Seattle, WA (USA)", "country": "US", "currency": "USD"},
    ]

