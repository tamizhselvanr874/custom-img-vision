import streamlit as st  
import requests  
from PIL import Image  
from io import BytesIO  
import base64  
import logging  
import time  
  
# Configure logging  
logging.basicConfig(level=logging.INFO)  
  
# Azure OpenAI Configuration  
azure_endpoint = "https://theswedes.openai.azure.com/"  
api_key = "783973291a7c4a74a1120133309860c0"  
api_version = "2024-02-01"  
model = "GPT-4o-mini"  
  
# AzureOpenAI Client Setup  
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
                logging.error(f"Attempt {attempt+1} failed: {str(e)}")  
                if attempt < max_attempts - 1:  
                    delay = min(base_delay * 2 ** attempt, max_delay)  
                    logging.info(f"Retrying in {delay} seconds...")  
                    time.sleep(delay)  
                else:  
                    raise  
  
client = AzureOpenAI(  
    azure_endpoint=azure_endpoint,  
    api_key=api_key,  
    api_version=api_version,  
)  
  
IMAGE_GENERATION_URL = "https://afsimage.azurewebsites.net/api/httpTriggerts"  
  
# Initialize session state variables  
if 'messages' not in st.session_state:  
    st.session_state.messages = []  
if 'selected_prompt' not in st.session_state:  
    st.session_state.selected_prompt = None  
if 'prompt_library' not in st.session_state:  
    st.session_state.prompt_library = []  
if 'generated_image_url' not in st.session_state:  
    st.session_state.generated_image_url = None  
if 'awaiting_followup_response' not in st.session_state:  
    st.session_state.awaiting_followup_response = False  
if 'refined_prompt' not in st.session_state:  
    st.session_state.refined_prompt = None  
if 'refined_explanation' not in st.session_state:  
    st.session_state.refined_explanation = None  
  
# Define prompt categories and options  
PROMPT_CATEGORIES = {  
    "Nature and Landscapes": [  
        ("Forests", "A mystical forest during twilight, dense fog weaving through towering ancient trees, glowing mushrooms scattered across the forest floor, ethereal light beams breaking through the canopy."),  
        ("Mountains", "A breathtaking snow-capped mountain range at sunrise, with golden light illuminating the peaks and a serene blue lake reflecting the view below."),  
        ("Beaches", "A tranquil tropical beach at sunset, with vibrant orange and pink hues painting the sky, crystal-clear turquoise water, and a wooden pier extending into the ocean.")  
    ],  
    "Architecture": [  
        ("Futuristic Cities", "A sprawling cyberpunk city at night, with neon-lit skyscrapers, flying cars, bustling streets filled with holographic signs, and a vibrant nightlife."),  
        ("Historical Monuments", "A beautifully detailed Roman colosseum at dusk, surrounded by lush greenery and tourists admiring the historic grandeur."),  
        ("Fantasy Castles", "An enormous floating castle in the sky, surrounded by fluffy white clouds, glowing waterfalls cascading from its edges, and magical birds flying around.")  
    ],  
    # Add more categories as needed  
}  
  
st.title("Interactive Image Chat Generation")  
  
def encode_image(image):  
    buffered = BytesIO()  
    image.save(buffered, format="PNG")  
    return base64.b64encode(buffered.getvalue()).decode("utf-8")  
  
def get_image_explanation(base64_image):  
    headers = {  
        "Content-Type": "application/json",  
        "api-key": api_key  
    }  
    data = {  
        "model": model,  
        "messages": [  
            {"role": "system", "content": "You are a helpful assistant that describes images."},  
            {"role": "user", "content": [  
                {"type": "text", "text": "Explain the content of this image in a single, coherent paragraph. The explanation should be concise and semantically meaningful, summarizing all major points from the image in one paragraph. Avoid using bullet points or separate lists."},  
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}  
            ]}  
        ],  
        "temperature": 0.7  
    }  
  
    try:  
        response = requests.post(  
            f"{azure_endpoint}/openai/deployments/{model}/chat/completions?api-version={api_version}",  
            headers=headers,  
            json=data  
        )  
        response.raise_for_status()  
        result = response.json()  
        return result["choices"][0]["message"]["content"]  
    except requests.exceptions.HTTPError as http_err:  
        logging.error(f"HTTP error occurred: {http_err}")  
    except Exception as e:  
        logging.error(f"An error occurred: {e}")  
    return "Failed to get image explanation."  
  
def call_azure_openai(messages, max_tokens, temperature):  
    try:  
        response = client.chat_completion(  
            model=model,  
            messages=messages,  
            temperature=temperature,  
            max_tokens=max_tokens  
        )  
        return response['choices'][0]['message']['content'].strip()  
    except Exception as e:  
        return f"Error: {str(e)}"  
  
def refine_explanation_with_feedback(explanation, feedback):  
    prompt = f"""  
    Based on the original explanation: "{explanation}", incorporate the following user feedback to refine the description: "{feedback}".  
    """  
    messages = [  
        {"role": "system", "content": "You are a helpful AI assistant who refines descriptions based on user feedback."},  
        {"role": "user", "content": prompt}  
    ]  
    return call_azure_openai(messages, 500, 0.7)  
  
def refine_prompt(selected_prompt):  
    prompt = f"How would you like to enhance this prompt: \"{selected_prompt}\" while keeping its original essence?"  
    messages = [  
        {"role": "system", "content": "You are a helpful AI assistant focused on enhancing prompts."},  
        {"role": "user", "content": prompt}  
    ]  
    return call_azure_openai(messages, 150, 0.7)  
  
def generate_prompt_library(user_input):  
    prompt = f"""  
    Based on the user's input: "{user_input}", generate three concise and imaginative image prompt suggestions.  
    Ensure each suggestion is relevant to the input and encourages creativity.  
    """  
    messages = [  
        {"role": "system", "content": "You are a creative assistant who generates concise image prompt suggestions."},  
        {"role": "user", "content": prompt}  
    ]  
    response_content = call_azure_openai(messages, 750, 0.8)  
    return response_content.split('\n')  
  
def get_follow_up(input_text):  
    prompt = f"""  
    Based on the user's initial input: \"{input_text}\", ask the following questions exactly as written,   
    without altering or adding any additional context:   
    What colors do you envision? (e.g., vibrant and bold colors or a muted, monochrome palette)  
    What textures should be highlighted? (e.g., smooth and shiny or rough and matte)  
    What shapes should stand out? (e.g., geometric and angular or soft and organic)  
    How should the lighting set the mood? (e.g., bright and cheerful or dim and moody)  
    How should depth be portrayed? (e.g., a deep perspective or a flat, stylized look)  
    What style should the image have? (e.g., realistic or abstract)  
    """  
    messages = [  
        {"role": "system", "content": "You are a helpful AI assistant focused on providing precise suggestions."},  
        {"role": "user", "content": prompt}  
    ]  
    return call_azure_openai(messages, 500, 0.7)  
  
def display_prompt_library():  
    with st.sidebar:  
        st.write("**Prompt Library:**")  
        for category, prompts in PROMPT_CATEGORIES.items():  
            st.write(f"### {category}")  
            for title, prompt in prompts:  
                if st.button(title):  
                    st.session_state.selected_prompt = prompt  
                    follow_up_question = refine_prompt(prompt)  
                    st.session_state.messages.append({"role": "assistant", "content": follow_up_question})  
                    st.session_state.awaiting_followup_response = True  
                    return  
  
def finalize_prompt(conversation):  
    prompt = "Craft a concise and comprehensive image prompt using the specific details provided by the user in the conversation. "  
    prompt += "Incorporate all relevant graphical elements discussed, such as colors, textures, shapes, lighting, depth, and style, without making assumptions or adding speculative details. "  
  
    # Collect user and assistant messages specifically  
    for turn in conversation:  
        if turn['role'] == 'user':  
            prompt += f"User: {turn['content']}. "  
        elif turn['role'] == 'assistant':  
            prompt += f"Assistant: {turn['content']}. "  
  
    messages = [  
        {"role": "system", "content": "You are a helpful AI assistant."},  
        {"role": "user", "content": prompt}  
    ]  
    return call_azure_openai(messages, 750, 0.7)  
  
def generate_image(prompt):  
    try:  
        response = requests.post(  
            IMAGE_GENERATION_URL,  
            json={"prompt": prompt},  
            headers={"Content-Type": "application/json"}  
        )  
        if response.status_code == 200:  
            data = response.json()  
            if "imageUrls" in data and data['imageUrls']:  
                return data['imageUrls'][0]  
        return "Failed to generate image."  
    except Exception as e:  
        return f"Error: {str(e)}"  
  
def display_image_options(image_url, image_caption):  
    if image_url:  
        st.sidebar.image(image_url, caption=image_caption, use_column_width=True)  
        image_data = requests.get(image_url).content  
        st.sidebar.download_button(  
            label=f"Download {image_caption}",  
            data=image_data,  
            file_name=f"{image_caption.lower().replace(' ', '_')}.png",  
            mime="image/png"  
        )  
  
def handle_image_input(image_file):  
    if image_file:  
        image = Image.open(image_file)  
        encoded_image = encode_image(image)  
        explanation = get_image_explanation(encoded_image)  
        st.session_state.messages.append({"role": "assistant", "content": explanation})  
        st.session_state.refined_explanation = explanation  
  
def chat_interface():  
    image_file = st.sidebar.file_uploader("Upload an image for explanation and refinement:", type=["png", "jpg", "jpeg"])  
    if image_file is not None:  
        handle_image_input(image_file)  
  
    user_input = st.chat_input("Your message:")  
  
    if user_input:  
        if st.session_state.awaiting_followup_response:  
            # Handle feedback for image explanation  
            refined_explanation = refine_explanation_with_feedback(st.session_state.refined_explanation, user_input)  
            st.session_state.messages.append({"role": "assistant", "content": refined_explanation})  
            st.session_state.refined_explanation = refined_explanation  
            st.session_state.awaiting_followup_response = False  
        else:  
            st.session_state.messages.append({"role": "user", "content": user_input})  
            st.session_state.prompt_library = generate_prompt_library(user_input)  
            follow_up = get_follow_up(user_input)  
            if follow_up:  
                st.session_state.messages.append({"role": "assistant", "content": follow_up})  
                st.session_state.awaiting_followup_response = True  
  
    display_prompt_library()  
  
    for message in st.session_state.messages:  
        with st.chat_message(message["role"]):  
            st.markdown(message["content"])  
  
    if st.session_state.refined_explanation and not st.session_state.awaiting_followup_response:  
        # Finalize prompt from conversation  
        final_prompt = finalize_prompt(st.session_state.messages)  
        st.write(f"**Final Prompt:** {final_prompt}")  
        if st.button("Generate Image"):  
            image_url = generate_image(final_prompt)  
            if image_url and "Error" not in image_url:  
                st.session_state.generated_image_url = image_url  
                display_image_options(image_url, "Refined Explanation Image")  
            else:  
                st.write("Failed to generate image.")  
  
chat_interface()  
