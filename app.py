import os
import requests
import streamlit as st
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO
import base64
import logging
import time

load_dotenv()
logging.basicConfig(level=logging.INFO)

azure_endpoint = os.getenv("AZURE_ENDPOINT")
api_key = os.getenv("API_KEY")
api_version = os.getenv("API_VERSION")
model = "GPT-4o-mini"


class AzureOpenAI:
    def __init__(self, azure_endpoint, api_key, api_version):
        self.azure_endpoint = azure_endpoint
        self.api_key = api_key
        self.api_version = api_version

    def chat_completion(self, model, messages, temperature, max_tokens):
        url = f"{self.azure_endpoint}/openai/deployments/{model}/chat/completions?api-version={self.api_version}"
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key,
        }
        data = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        base_delay = 1
        max_delay = 32
        max_attempts = 5

        for attempt in range(max_attempts):
            try:
                response = requests.post(url, headers=headers, json=data)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                logging.error(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_attempts - 1:
                    delay = min(base_delay * 2**attempt, max_delay)
                    logging.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    raise RuntimeError("Max attempts reached") from e


client = AzureOpenAI(azure_endpoint, api_key, api_version)

IMAGE_GENERATION_URL = "https://afsimage.azurewebsites.net/api/httpTriggerts"

if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_question_index" not in st.session_state:
    st.session_state.current_question_index = 0
if "final_prompt" not in st.session_state:
    st.session_state.final_prompt = None
if "selected_prompt" not in st.session_state:
    st.session_state.selected_prompt = None
if "awaiting_followup_response" not in st.session_state:
    st.session_state.awaiting_followup_response = False
if "recommendations" not in st.session_state:
    st.session_state.recommendations = []

PROMPT_CATEGORIES = {
    "Nature and Landscapes": [
        (
            "Forests",
            "A mystical forest during twilight, dense fog weaving through towering ancient trees, glowing mushrooms scattered across the forest floor, ethereal light beams breaking through the canopy.",
        ),
        (
            "Mountains",
            "A breathtaking snow-capped mountain range at sunrise, with golden light illuminating the peaks and a serene blue lake reflecting the view below.",
        ),
        (
            "Beaches",
            "A tranquil tropical beach at sunset, with vibrant orange and pink hues painting the sky, crystal-clear turquoise water, and a wooden pier extending into the ocean.",
        ),
    ],
    "Architecture": [
        (
            "Futuristic Cities",
            "A sprawling cyberpunk city at night, with neon-lit skyscrapers, flying cars, bustling streets filled with holographic signs, and a vibrant nightlife.",
        ),
        (
            "Historical Monuments",
            "A beautifully detailed Roman colosseum at dusk, surrounded by lush greenery and tourists admiring the historic grandeur.",
        ),
        (
            "Fantasy Castles",
            "An enormous floating castle in the sky, surrounded by fluffy white clouds, glowing waterfalls cascading from its edges, and magical birds flying around.",
        ),
    ],
    "Professional Product Photography": [
        (
            "High-End Scotch Whiskey",
            "Professional photograph of a high-end scotch whiskey presented on the table, eye level, warm cinematic, Sony A7 105mm, close-up, centred shot --ar 2:1",
        ),
        (
            "Organic Pea Protein Powder",
            "Professional photograph of organic pea protein powder packaged in high-end packaging - recyclable material, eye level, warm cinematic, Sony A7 105mm, close-up, centred shot, octane render --ar 2:1",
        ),
        (
            "Hot Cappuccino",
            "Freshly made hot cappuccino on glass table, angled top down, midday warm, Nikon D850 105mm, close-up, centred shot --ar 2:1",
        ),
        (
            "Luxury Jewelry",
            "Luxury high resolution jewelry, minimalist wedding band, angled top down, studio bright, Nikon D850 105mm, close-up centred shot --ar 2:1",
        ),
    ],
    "Realistic Human Portraits": [
        (
            "Young Man in New York",
            "Candid portrait of young man on a New York street, early 1900s, natural lighting, Nikon D850 35mm and f-stop 1.8, global illumination --ar 2:1",
        ),
        (
            "Beautiful Woman on Busy Street",
            "Candid photo portrait of beautiful woman on busy street, natural lighting, Nikon D850 105mm, f-stop 1.8, cinematic --ar 2:1",
        ),
        (
            "Best Friends at Skatepark",
            "A candid shot of young best friends dirty, at the skatepark, natural afternoon light, Canon EOS R5, 100mm, F 1.2 aperture setting capturing a moment, cinematic --ar 2:1",
        ),
    ],
    "Logos and Brand Mascots": [
        (
            "Futuristic Worker Mascot",
            "A worker mascot for a futuristic manufacturing company, simple, line art, iconic, vector art, flat design, sky blue theme, creamy beige background --ar 2:1",
        ),
        (
            "Rustic Coffee Company Logo",
            "An emblem logo for a rustic coffee company, 'Aroma Trails', minimalistic, line art, iconic, vector art, flat design, earthy brown and charcoal grey theme --ar 2:1",
        ),
        (
            "Organic Skincare Brand Mascot",
            "A soothing mascot for an organic skincare brand, minimalistic, line art, vector art, flat design --ar 2:1",
        ),
    ],
    "Lifestyle Stock Images of People": [
        (
            "Loving Couple on Beach",
            "A photograph of a couple caught in a loving moment with a scenic beach sunset as the background context, during dusk with soft, natural lighting and shot with a portrait lens, shot with a Sony Alpha a7 III, using the Sony FE 85mm f/1.4 GM lens --ar 2:1",
        ),
        (
            "Intense Workout",
            "A photograph of a lady engaged in an intense workout with a modern, well-equipped gym as the background context, during the morning with bright, natural lighting and shot with a telephoto lens, shot with a Canon EOS R5, using the Canon EF 70-200mm lens. --ar 2:1 --v 5.1 --s 200",
        ),
    ],
    "Landscapes": [
        (
            "Tropical Rainforest",
            "RAW photo, an award-winning National Geographic style HD photograph featuring the untamed beauty of the tropical rainforest. It's just after a rain shower at dusk, the orange-purple hues of twilight permeating the scene, casting long, dramatic shadows and creating a soft, diffused light that gives the landscape an almost ethereal feel. Taken using a Sony Alpha 1 with a 50mm f/1.8 lens, f/11 aperture, shutter speed 1/200s, ISO 100, This stunning image is rendered in insanely high resolution, realistic, 8k, HD, HDR, XDR, focus + sharpen + wide-angle 8K resolution + HDR10 Ken Burns effect + Adobe Lightroom + rule-of-thirds + high-detailed leaves + high-detailed bark + high-detailed feathers. An added touch of depth-of-field effect, lens flare, and digital negative are used to enhance the visual appeal. --ar 2:1",
        ),
        (
            "Australian Outback",
            "RAW photo, an award-winning National Geographic style HD photograph featuring the striking beauty of the Australian Outback. Weather conditions are dry, causing the landscape to take on a deep, sun-baked hue, the long shadows creating stark contrasts. Taken using a Sony Alpha 1 with a 50mm f/1.8 lens, f/11 aperture, shutter speed 1/200s, ISO 100, realistic, 8k, HD, HDR, XDR, focus + sharpen + wide-angle 8K resolution + HDR10 Ken Burns effect + Adobe Lightroom + rule-of-thirds + high-detailed leaves + high-detailed bark + high-detailed fur --ar 2:1",
        ),
        (
            "Thai Beach",
            "RAW photo, an award-winning National Geographic style HD photograph featuring the tranquil allure of a pristine Thai beach. Captured during the magic hour of sunset, the sky unfolds a symphony of pinks and oranges, casting a warm, romantic glow on the scenery. Taken using a Sony Alpha 1 with a 50mm f/1.8 lens, f/11 aperture, shutter speed 1/200s, ISO 100, This stunning image is rendered in insanely high resolution, realistic, 8k, HD, HDR, XDR, focus + sharpen + wide-angle 8K resolution + HDR10 Ken Burns effect + Adobe Lightroom + rule-of-thirds + high-detailed leaves + high-detailed bark. Effects of color grading, water motion blur, and starburst are incorporated for a visually arresting impact. --ar 2:1",
        ),
    ],
    "Macro Photography": [
        (
            "Dewdrop on Spider Web",
            "Extreme close-up by Oliver Dum, magnified view of a dewdrop on a spider web occupying the frame, the camera focuses closely on the object with the background blurred. The image is lit with natural sunlight, enhancing the vivid textures and contrasting colors.",
        ),
        (
            "Weathered Coin",
            "Ultra close-up macro photograph of an old, weathered coin found in the dirt while metal detecting, highlighting the worn inscriptions and patina, with natural, overcast light, and a gritty texture of the soil. The Canon EOS R5 focuses closely on the coin with the background blurred. The scene is ultra detailed with realistic textures resembling a photograph taken using a Canon EF 100mm f/2.8L Macro IS USM lens.",
        ),
        (
            "Butterfly Wing",
            "Extreme close-up by Oliver Dum, magnified view of a butterfly wing occupying the frame, the camera focuses closely on the object with the background blurred. The image is lit with natural sunlight, enhancing the vivid textures.",
        ),
    ],
    "YouTube Thumbnails": [
        (
            "Alex Hormozi Thumbnail",
            "Generic Alex Hormozi YouTube thumbnail --ar 16:9 --s 200 --c 50",
        ),
        (
            "iPhone Review Thumbnail",
            "iPhone review YouTube thumbnail --ar 16:9 --c 1",
        ),
        (
            "Man with Monkeys Thumbnail",
            "Typical YouTube thumbnail featuring a man with an open mouth standing in front of a group of monkeys. Turn on RTX for realistic detail. --ar 16:9",
        ),
        (
            "Typical Thumbnail",
            "Typical YouTube Thumbnail --ar 16:9 --s {100, 200, 600, 1000} --c {1, 50, 100}",
        ),
    ],
    "Oil Paintings": [
        (
            "Serene Lakeside",
            "A serene lakeside scene at sunset with visible brushwork. Impasto texture and chiaroscuro lighting, emulating the style of a classical oil painting --ar 2:1",
        ),
        (
            "European Café",
            "Capture a bustling European café scene, complete with intricate details, such as filigree ironwork and cobblestone streets. Use impasto technique for texture and employ sfumato for a smoky atmosphere, in the tradition of old master oil paintings. --ar 2:1 --s 600 --c 100",
        ),
        (
            "Autumn Forest",
            "Create an image of a tranquil autumn forest with a meandering stream. Use palette-knife strokes for a textured appearance, incorporating Afremov's signature bold and vibrant color palette. --ar 2:1 --c 50",
        ),
    ],
    "Ultra Realistic Foods": [
        (
            "Grilled Fish and Chips",
            "Image of grilled fish and chips STYLE: Close-up shot | GENRE: Gourmet | EMOTION: Tempting | SCENE: A plate of freshly grilled fish and chips with seasoning and garnish | TAGS: High-end food photography, clean composition, dramatic lighting, luxurious, elegant, mouth-watering, indulgent, gourmet | CAMERA: Nikon Z7 | FOCAL LENGTH: 105mm | SHOT TYPE: Close-up | COMPOSITION: Centered | LIGHTING: Soft, directional | PRODUCTION: Food Stylist| TIME: Evening --ar 16:8",
        ),
        (
            "Pavlova Dessert",
            "Image of pavlova dessert PRESENTATION: Macro Lens | CUISINE TYPE: Upscale | AMBIENCE: Alluring | VISUALS: Dessert serving of Pavlova | ATTRIBUTES: Upscale gastronomy imagery, seamless arrangement, intense yet elegant spotlight, sumptuous, refined, irresistible, lavish, gourmet | TOOL: Nikon Z7 | LENS DETAIL: 105mm | SHOT PERSPECTIVE: Close Proximity | ALIGNMENT: Equilibrium in focus | ILLUMINATION CHARACTERISTICS: Subtle, with a single point of origin | BEHIND THE SCENES: Gourmet Arrangement Specialist | PHOTO SESSION TIMING: Twilight --ar 16:8",
        ),
        (
            "Burgers",
            "Image of burgers APPROACH: Detailed Focus | CATEGORY: High-end Cuisine | MOOD: Inviting | DESCRIPTION: Fresh beef burger with vibrant salads and beautiful pillow buns | KEYWORDS: Sophisticated food capture, neat framing, evocative illumination, posh, graceful, drool-inducing, decadent, gourmet | EQUIPMENT: Nikon Z7 | LENS: 105mm | SHOT NATURE: Close-range | FRAME: Balanced Central | ILLUMINATION: Gentle, from one direction | CREW: Culinary Stylist| SHOOTING SCHEDULE: Dusk --ar",
        ),
    ],
}

st.title("Interactive Image Chat Generation")


def encode_image(image):
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


def get_image_explanation(base64_image):
    headers = {"Content-Type": "application/json", "api-key": api_key}
    data = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant that describes images.",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Explain the content of this image..."},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_image}"},
                    },
                ],
            },
        ],
        "temperature": 0.7,
    }
    try:
        response = requests.post(
            f"{azure_endpoint}/openai/deployments/{model}/chat/completions?api-version={api_version}",
            headers=headers,
            json=data,
        )
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error: {e}")
        return "Failed to get image explanation."


def call_azure_openai(messages, max_tokens, temperature):
    try:
        response = client.chat_completion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logging.error(f"OpenAI API call failed: {e}")
        return "Error in API call."


def finalize_prompt(conversation):
    user_details = "\n".join(
        f"{turn['role'].capitalize()}: {turn['content']}" for turn in conversation
    )
    prompt = (
        "Based on the conversation below, create a concise and detailed image description..."
        f"Conversation:\n{user_details}\nFinal Image Description:"
    )
    messages = [
        {
            "role": "system",
            "content": "You are an AI assistant that creates detailed image prompts...",
        },
        {"role": "user", "content": prompt},
    ]
    return call_azure_openai(messages, 750, 0.7) or "Failed to finalize prompt."


def modify_prompt_with_llm(initial_prompt, user_instruction):
    prompt = (
        f"You are an assistant that modifies image descriptions based on user input.\n"
        f"Initial Description:\n{initial_prompt}\n\n"
        f"User Instruction:\n{user_instruction}\n\n"
        "Please update the initial description by incorporating the user's instruction..."
    )
    messages = [
        {
            "role": "system",
            "content": "You are skilled at updating image descriptions...",
        },
        {"role": "user", "content": prompt},
    ]
    return call_azure_openai(messages, 150, 0.7) or "Failed to modify prompt."


def generate_image(prompt):
    try:
        response = requests.post(
            IMAGE_GENERATION_URL,
            json={"prompt": prompt},
            headers={"Content-Type": "application/json"},
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("imageUrls", ["Failed to generate image."])[0]
    except requests.exceptions.RequestException as e:
        logging.error(f"Image generation failed: {e}")
    return "Failed to generate image."


def display_image_options(image_url, image_caption):
    if image_url:
        st.sidebar.image(image_url, caption=image_caption, use_column_width=True)
        image_data = requests.get(image_url).content
        st.sidebar.download_button(
            label=f"Download {image_caption}",
            data=image_data,
            file_name=f"{image_caption.lower().replace(' ', '_')}.png",
            mime="image/png",
        )


def handle_image_input(image_file):
    if image_file:
        image = Image.open(image_file)
        encoded_image = encode_image(image)
        explanation = get_image_explanation(encoded_image)
        st.session_state.messages.append({"role": "assistant", "content": explanation})


def display_prompt_library():
    with st.sidebar:
        st.write("*Prompt Library:*")
        for category, prompts in PROMPT_CATEGORIES.items():
            st.write(f"### {category}")
            columns = st.columns(len(prompts))
            for col, (title, prompt) in zip(columns, prompts):
                with col:
                    if st.button(title):
                        st.session_state.selected_prompt = prompt
                        st.session_state.messages.append(
                            {
                                "role": "assistant",
                                "content": f"Selected prompt: {prompt}",
                            }
                        )
                        st.session_state.final_prompt = prompt
                        st.session_state.awaiting_followup_response = False
                        return


def chat_interface():
    image_file = st.sidebar.file_uploader(
        "Upload an image for explanation and refinement:", type=["png", "jpg", "jpeg"]
    )
    user_input = st.chat_input("Your message:")

    if image_file:
        handle_image_input(image_file)
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            st.session_state.final_prompt = finalize_prompt(st.session_state.messages)
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": f"*Final Prompt:* {st.session_state.final_prompt}",
                }
            )
    elif user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        if st.session_state.selected_prompt:
            modified_prompt = modify_prompt_with_llm(
                st.session_state.selected_prompt, user_input
            )
            st.session_state.final_prompt = modified_prompt
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": f"*Final Prompt:* {st.session_state.final_prompt}",
                }
            )
            st.session_state.selected_prompt = None
        else:
            if st.session_state.current_question_index < 6:
                context = " ".join(msg["content"] for msg in st.session_state.messages)
                dynamic_question = generate_dynamic_questions(user_input, context)
                st.session_state.messages.append(
                    {"role": "assistant", "content": dynamic_question}
                )
                recommendation = generate_recommendation(user_input, context)
                st.session_state.recommendations.append(recommendation)
                st.session_state.current_question_index += 1
            else:
                st.session_state.final_prompt = finalize_prompt(
                    st.session_state.messages
                )
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": f"*Final Prompt:* {st.session_state.final_prompt}",
                    }
                )

    display_prompt_library()

    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
        if i < len(st.session_state.recommendations):
            if st.checkbox(f"Show recommendation for message {i + 1}", key=f"rec_{i}"):
                st.markdown(f"Recommendation: {st.session_state.recommendations[i]}")

    if st.session_state.final_prompt and st.button("Generate Image"):
        image_url = generate_image(st.session_state.final_prompt)
        if image_url and "Error" not in image_url:
            st.session_state.generated_image_url = image_url
            display_image_options(image_url, "Generated Image")
        else:
            st.write("Failed to generate image.")


def generate_dynamic_questions(user_input, conversation_history):
    prompt = (
        f'We are working with the initial concept:\n"{user_input}"\n\n'
        f"Conversation so far:\n{conversation_history}\n\n"
        "Please generate a follow-up question that explores one aspect such as colors, textures, shapes, lighting, depth, or style."
    )
    messages = [
        {
            "role": "system",
            "content": "You are a creative assistant who generates insightful questions and recommendations.",
        },
        {"role": "user", "content": prompt},
    ]
    response_content = call_azure_openai(messages, 750, 0.8)
    return (
        response_content.strip()
        if response_content
        else "Couldn't generate a question."
    )


def generate_recommendation(user_input, conversation_history):
    prompt = (
        f'We are working with the initial concept: "{user_input}". '
        f'Given the conversation so far: "{conversation_history}", generate a short recommendation to inspire the user further.'
    )
    messages = [
        {
            "role": "system",
            "content": "You are a creative assistant who generates concise recommendations.",
        },
        {"role": "user", "content": prompt},
    ]
    recommendation = call_azure_openai(messages, 150, 0.8)
    return recommendation.strip()


chat_interface()
