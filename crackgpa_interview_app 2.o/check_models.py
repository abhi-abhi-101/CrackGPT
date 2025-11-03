# check_models.py
import google.generativeai as genai

# --- IMPORTANT: PASTE YOUR GEMINI API KEY HERE ---
GEMINI_API_KEY ="AIzaSyCD7Y5AOnjoY9-ia9i6_F9b1DcLLif3k7U"

# Configure the library with your key
try:
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"Configuration Error: {e}")
    exit()

print("✅ Finding models you can use for generating content...\n")

# List all available models
for model in genai.list_models():
    # Check if the model supports the 'generateContent' method
    if 'generateContent' in model.supported_generation_methods:
        print(f"➡️ {model.name}")

print("\n✅ Done! You can use any of the model names listed above.")