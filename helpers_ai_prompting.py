import base64
import tempfile
import os

image_specs_instructions = """
Analyze the provided product image(s) and extract and relevant product details and ALL NUMERICAL DIMENSIONS (if any) as concise bullet points.
Extract the following information when present in the image(s):

1. PRODUCT IDENTIFICATION
   - What is the product?
   - If picture includes plants, identify the species (e.g. eucalyptus, rose, hydrangrea)

2. MATERIALS & CONSTRUCTION
   - Primary materials (e.g., "metal frame", "plexiglass", "ceramic pot")
   - Material qualities (e.g., "shatterproof", "ornate texture", "brushed finish")
   - Construction details (e.g., "sturdy backing", "spring clips")

3. COLORS & AESTHETICS
   - Finish type (e.g., "gold", "matte black", "frosted")
   - Visual style (e.g., "ornate", "minimalist", "rustic")

4. DIMENSIONS & SIZING
   - Overall product dimensions (length × width × height)
   - Component dimensions (e.g., "7.08\" wide canopy", "1.96\" pot height")
   - Frame or display area dimensions (e.g., "fits 5\"×7\" photo", "4.4\"×6.4\" display size")
   - Include both inches and centimeters when both are shown

5. COMPONENTS & PARTS
   - Individual components (e.g., "black rectangular vase", "decorative pebbles", "artificial eucalyptus leaves")
   - Included accessories (e.g., "kickstand", "mounting hardware")

6. FEATURES & FUNCTIONALITY
   - Practical features (e.g., "vertical or horizontal display", "wall mountable", "easy photo loading")
   - Special mechanisms (e.g., "spring clips", "triangular hooks", "fold-out stand")
   - Protective features (e.g., "shatterproof", "protective film on both sides")

7. TEXT FROM IMAGE
   - Capture any promotional text or quality descriptions shown
   - Summarize key selling points mentioned in image text
   - Note usage instructions if present
   - Do NOT include section headers, labels, or image titles (e.g., skip "SIZE", "DETAIL", "MATERIALS")
   - Do NOT need to announce 'text shown', 'text included'... etc. 

FORMATTING REQUIREMENTS:
- Output 6-12 bullets. Each bullet should be a SHORT phrase (3-8 words ideal, max 12 words)
- Use specific measurements, not vague terms
- Use descriptive adjectives from the image (e.g., "ornate gold frame" not just "frame")
- Group related details together (e.g., "Kickstand for vertical/horizontal display")
- Prioritize factual specifications over marketing language
- If multiple images show the same product, consolidate information without duplication
- Do NOT include brand names
- Prioritize including ALL numerical dimensions mentioned in image

EXAMPLES:
- Gold ornate metal frame
- Fits 5"×7" photo, 4.4"×6.4" display area
- Shatterproof plexiglass front panel
- Spring clips and triangular hooks for easy mounting
- Kickstand for vertical or horizontal display
- Artificial bonsai tree
- Frosted green eucalyptus leaves
- Black rectangular ceramic pot, 7.08"×4.72" base
- Overall height 6.49" (16.5cm)
- Decorative river pebbles in vase
- Protective film on both sides (peel before use)

Now analyze the provided image(s) and extract all relevant product specifications as bullet points following this format.
"""


def encode_image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")
    
def generate_product_description_from_image(
    client, 
    image_file: str,
    system_instructions: str,
    processing_instructions: str,
    model: str = "gpt-5.2",
    temperature = 0.2
):
    image_base64 = encode_image_to_base64(image_file)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_instructions},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": processing_instructions},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ],
            },
        ],
        temperature=temperature,
    )

    return response.choices[0].message.content


def process_single_image(i, image, client, system_instructions, processing_instructions):
    """
    Runs inside a thread. DO NOT touch streamlit here.
    """

    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        if image.mode != "RGB":
            image = image.convert("RGB")

        image.save(tmp.name, format="JPEG", quality=95)
        temp_image_path = tmp.name

    try:
        result = generate_product_description_from_image(
            client=client,
            image_file=temp_image_path,
            system_instructions=system_instructions,
            processing_instructions=processing_instructions,
        )
        return (i, result)

    finally:
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)



def complete_phrase(client, 

                    prompt: str, 
                    model = "gpt-5.1-2025-11-13",
                    temperature = 0.2) -> str:
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are an assistant writer for Amazon product listings."},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,    
    )

    return response.choices[0].message.content.strip()


# title_generator_prompt_gemini = """
# You are an expert in writing SEO-optimized Amazon listings for {selected_product}. 
# I will provide you with 1-2 top search term as well as a list of primary and secondary keywords, 
# and you are to write a professional Amazon-ready product title of around 190 characters with space.
# Use singular tense (e.g. plant instead of plants).

# Structure: [Product Name] + comma + [Core Product Features] + for +  [Occassions and Settings]
# - Product Name: Use top search terms to begin the title with a concise 3 word product name (4 words max). 
# - Primary Keywords: Place primary keywords and dimensions/numbers near front of title
# - Secondary keywords:  Include 3-4 setting/occasion-related keywords (not too many). that fit the context of the product.
#   See secondary keyword list and example product titles for reference.

# Do not hallucinate materials, dimensions, or colors not explicitly provided.
# Insert commas between major sections: after product type/size, after key features, before gift/occasion details.
# Use at most 1-2 commas.

# Example product titles:

# Ceramic Flower Vase, 12.5" Large Rustic Farmhouse Vases Home Decor, Tall Pottery Decorative Pampas Vase for Table Living Room Entryway Bathroom Kitchen

# Faux Magnolia Branches, 22 Inches Artificial Magnolia Leaves Stems Real Touch Faux Greenery for Home Office Room Table Vase Farmhouse Decor  

# Constraints:
# - Product title must be no more than 200 characters with spaces (strict limit)
# - Do NOT include the same numerical keyword more than 1 time (eg 5x7, 5 x 7, 10inch)
# - No brand names

# INPUT:

# Top search terms:
# {top_search_terms}

# Primary Keywords
# {primary_keywords}

# Secondary Keywords:
# {secondary_keywords}

# Your output (output only the title and nothing else):

# """

title_generator_prompt_gemini = """
You are an expert in writing SEO-optimized Amazon listings for {selected_product}. 
I will provide you with 1-2 top search term as well as a list of primary and secondary keywords, 
and you are to write a professional Amazon-ready product title.
Use singular tense (e.g. plant instead of plants). Length must be AT LEAST 150 chars and NO MORE THAN 190 chars with spaces.

Strictly follow this structure:

a) If product component keywords present (e.g. vase: handle, pot: drainage holes, picture frame: tabletop stand):  
[Product Name] + , + [Primary Keywords + Dimensions] + with + [Core Features/Components] + , + [Product-related noun phrase] + for + [Occasions/Settings]

b) Otherwise: [Product Name] + , + [Primary Keywords + Dimensions]  + , +  [Product-related noun phrase] + for + [Occasions/Settings]

- Product Name: Use top search terms to begin the title with a concise 3 word product name (4 words max). 
- Primary Keywords: Place primary keywords and dimensions/numbers near front of title
- Core features/components: Include component-related keywords ONLY if provided (e.g. vase with handle). Otherwise, no need.
- Secondary keywords:  Include 3-4 setting/occasion-related keywords (not too many). that fit the context of the product.
  See secondary keyword list and example product titles for reference.

Example template: 8x10 Picture Frame Gold, Vintage Photo Display with Tabletop Stand and Wall Hanging Mounting, Decorative Frame for Home Office Gallery Wedding Gift Decor

Do not hallucinate materials, dimensions, or colors not explicitly provided.
Insert commas between major sections: after product type/size, after key features, before gift/occasion details.
Ensure attributes (e.g. microwave safe, UV-protective) modify the main product, not individual components 

Example product titles:

Ceramic Flower Vase, 12.5" Large Rustic Farmhouse Vases Home Decor, Tall Pottery Decorative Pampas Vase for Table Living Room Entryway Bathroom Kitchen

Faux Magnolia Branches, 22 Inches Artificial Magnolia Leaves Stems Real Touch Faux Greenery for Home Office Room Table Vase Farmhouse Decor  

Constraints:
- You may use the same keyword only 1-2 times. 
- Do NOT include color, dimensions, style-related keywords more than 1 time (eg 5x7, 5 x 7, 10inch, blue, striped, rustic, minimalist)
- No brand names.
- You may ONLY use 2 commas (1st comma after product name, 2nd comma between [Primary Keywords + Dimension] and [Product-related noun phrase])

INPUT:

Top search terms:
{top_search_terms}

Primary Keywords
{primary_keywords}

Secondary Keywords:
{secondary_keywords}

Make sure product title is strictly between 150-190 chars with spaces. 
Your output (output only the title and nothing else):

"""


additional_constraints = """
Constraints:
- Product title must be no more than 200 characters with spaces (strict limit)
- No brand names
- Prohibited characters: ! $ ? _ ^ ¬ ¦, curly braces
- Don’t repeat same word more than 2 times (plural form counts as repeat).
- Don’t include the same numerical keyword more than 1 time (eg 5x7, 10inch)
- Do not cluster more than 3 adjectives consecutively 
"""




feature_summary_from_url_prompt_simple = """
ROLE: You are an an assistant Amazon sales copywriter. I will give you 1-3 product listings and you are to
perform the following tasks:

From the listing bullets, identify, synthesize and summarize the products' most important shared features as a list of phrases following the format:
[PRODUCT COMPONENT] enables [THIS DESIRABLE FEATUREs]. Use high-impact positive language (speak like a professional salesperson)

Output 7-8 unique bullets in TOTAL (not for each individual bullet), each 40-80 chars with space.
Do NOT include specific product dimensions/numnbers (e.g. instead of saying 10inch screen offers clear display, say large screen offers clear display)

Example: Eye mask
1. Patented bending cartilage design is comfortable, durable, blocks light effectively
2. Adjustable strap fits snugly, does not snag on hair, suitable for any sleeping position
3. ...

Example: Photo frame
1. Victorian style exudes classic, courtly elegance
2. Hand-embossed latticework gives striking 3-dimensional appearance
3. Textured velvet backing more durable and reliable compared to cheaper alternatives
...

YOU MUST ONLY STRICTLY USE THE CONTENTS IN THE LISTING BULLET (cannot assume information not included).
That is, I should be able to find your output's content in the url listing.

LISTING: 

{listing}
"""


listing_writer_instructions_gemini = """
You are an assistant for Amazon listing writing for {selected_product}. I will provide you with [product specs], [keyword phrases], [secondary keywords] and [desirable features].
Your task is to write a factually accurate SEO-optimized Amazon listing that appeals to customers by:
    1. Including info from [product specs]
    2. Naturally incorporating [keyword phrases] and [secondary keywords] into listing (no need to precede with articles like 'a', 'an', 'the', 'this' etc.) 
    3. Communicating [desirable features] in 5 logically grouped bullet points (subheading 2-3 words)
       The subheading and content of each bullet should focus on 1 single theme (e.g. appearance, quality, ease of use)

Content guidelines: 
- Incorporate [keyword phrases], one after the subheading of each bullet, in same order as provided.
- Follow [keyword phrases] by a strong verb (e.g., "features, "includes,", "uses", "offers" etc.) that connects the keyword to its description.
- Keep each keyword phrase intact rather than splitting words apart (e.g. '4x6 bronze picture frame'). 
- [Secondary keywords] should be in the 2nd half of listing and towards the end of each bullet.
- Include all numerical/dimension-related details from [product specs] in listing.
- Each bullet point should present distinct information without redundancy. Never circle back to reinforce a point you've already made in that same bullet
- 2 sentences per bullet.

Constraints:
- Produce 5 bullets. Each bullet MUST be within 250-300 characters long (with spaces).
- Only output the 5 bullets and nothing else (no need to write 'here is your listing'). Bold the subheadings for each bullet followed by ':'.
- Do NOT repeat the same keyword phrase more than 1 time. Do NOT include brand names. 
- You may NOT use 1st person (our, my).

Example: Emulate this tone/language style

- No light Leakage: With the heightened 22 mm adaptive hollow nose bridge, LitBear sleep mask fully fits all nose shapes, helps improve sleep, and gets longer deep sleep

- Completely Block Light for Side Sleeper: New design of 15° tilt angle ultra-thin sides of the eye mask for sleeping which can reduce 90% pressure on your temples. Sleep more comfortably when is on your side, a perfect light-blocking sleeping mask for back and stomach sleepers

- Blinking Freely: Deep 12 mm 3D contoured cup eye sockets leave larger space for blinking, maintaining your beautiful eye makeup without pressure on your eyes. This sleep mask for women and men will be a good choice for you

- Comfortable and Soft: Made of smooth cooling fabric lining and premium 6-layer low rebound soft memory foam make the sleep eye mask breathable and lightweight, comfortable for travel, nap, flight, camping, and Yoga

- Adjustable: Easy to adjust the elastic buckle strap from 20.5 to 26.5 inches and fits snuggly, is suitable for any sleeping position and stays in place

USER INPUT

[Product Specs]

{product_specs}

[Keyword Phrases]

{keyword_search_phrases}

[Secondary keywords]

{secondary_keywords}

[Desirable Features]

{desirable_features}

If desirable features conflict with product specs (e.g., color, dimension, material), always use product specs and ignore the conflicting desirable feature.
Otherwise, include ALL of the desirable features accurately and precisely, staying true to its core meaning.

Your output: 
"""

keyword_grammar_fix_prompt = """
Reorder the following product keyword phrases so that adjectives and size descriptors 
come BEFORE nouns. Maintain natural English word order where adjectives precede the 
nouns they modify. Use singular tense. 

Rules:
- Colors, materials, styles, and qualities should come before product names
- Size descriptors (like "5x7", "8x10", "large", "small") should come before product names
- Keep compound nouns together (e.g., "picture frame" stays together)
- Only fix incorrect ordering; don't change already correct phrases
- Preserve all words from the original phrase. Do not add new words.

Examples:
- "5x7 picture frame gold" → "gold 5x7 picture frame"
- "frames silver 8x10" → "silver 8x10 frame"
- "boxes wooden vintage" → "vintage wooden box"
- "gold picture frames" → "gold picture frames" (already correct)

Keywords to fix:
{keyword_phrases}

Return only the corrected keyword list, each keyword phrase separated by comma ","
"""


