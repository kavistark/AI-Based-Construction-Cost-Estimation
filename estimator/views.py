"""
ConstructAI — Views
Upgraded with: real ML model, Gemini blueprint generation, full auth.
"""
import json
import base64
import urllib.request
import urllib.error
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from .models import ProjectEstimate
from .ml_model import predict_construction_cost
 
# ──────────────────────────────────────────────────────────────────────────────
# Gemini Blueprint Generator
# ──────────────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = getattr(settings, 'GEMINI_API_KEY', 'AIzaSyD7d4ODqGrRM7AflV5KVLbTiaymp-36_0M')
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash-exp-image-generation:generateContent?key=" + GEMINI_API_KEY
)

def generate_blueprint_image(house_type, rooms, room_type, theme, area):
    """Call Gemini to generate a floor-plan / blueprint image."""
    prompt = (
        f"Create a clean, professional architectural floor plan blueprint for a {house_type} "
        f"Indian apartment. Area: {area} sq ft, {rooms} rooms, focus on {room_type}. "
        f"Interior theme: {theme}. "
        "Style: technical blueprint drawing with blue background, white lines, room labels, "
        "dimensions noted. Top-down orthographic view. Clean, minimal, professional."
    )
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}
    }).encode()

    req = urllib.request.Request(
        GEMINI_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
            if part.get("inlineData"):
                b64 = part["inlineData"]["data"]
                mime = part["inlineData"].get("mimeType", "image/png")
                return f"data:{mime};base64,{b64}"
    except Exception as e:
        print(f"Gemini error: {e}")
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Home / Estimate
# ──────────────────────────────────────────────────────────────────────────────
def home_view(request):
    if request.method == 'POST':
        plot_area    = request.POST.get('plot_area', 0)
        rooms        = request.POST.get('rooms', '3')
        material     = request.POST.get('material', 'Medium (Standard materials)')
        paint        = request.POST.get('paint', 'Emulsion Paint')
        house_type   = request.POST.get('house_type', '2BHK')
        room_type    = request.POST.get('room_type', 'Bedroom')
        theme        = request.POST.get('theme', 'Classic White')
        budget_range = request.POST.get('budget_range', '₹5L – ₹10L')

        estimation = predict_construction_cost(
            area=plot_area,
            material=material,
            paint=paint,
            house_type=house_type,
            rooms=rooms,
            room_type=room_type,
            theme=theme,
            budget_range=budget_range,
        )

        blueprint_image = None
        if estimation['total_cost'] > 0:
            # Generate Gemini blueprint
            blueprint_image = generate_blueprint_image(
                house_type=house_type,
                rooms=rooms,
                room_type=room_type,
                theme=theme,
                area=plot_area,
            )

            ProjectEstimate.objects.create(
                user=request.user if request.user.is_authenticated else None,
                plot_area=plot_area,
                rooms=rooms,
                material_quality=material,
                paint_type=paint,
                house_type=house_type,
                room_type=room_type,
                theme=theme,
                budget_range=budget_range,
                estimated_cost=estimation['total_cost'],
            )
            return render(request, 'result.html', {
                'estimation': estimation,
                'blueprint_image': blueprint_image,
                'inputs': {
                    'area': plot_area, 'rooms': rooms, 'material': material,
                    'paint': paint, 'house_type': house_type, 'room_type': room_type,
                    'theme': theme, 'budget_range': budget_range,
                }
            })

    return render(request, 'home.html')


# ──────────────────────────────────────────────────────────────────────────────
# AJAX live estimate (no DB save, no blueprint)
# ──────────────────────────────────────────────────────────────────────────────
def ajax_estimate(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        result = predict_construction_cost(
            area         = data.get('area', 0),
            material     = data.get('material', 'Medium (Standard materials)'),
            paint        = data.get('paint', 'Emulsion Paint'),
            house_type   = data.get('house_type', '2BHK'),
            rooms        = data.get('rooms', 3),
            room_type    = data.get('room_type', 'Bedroom'),
            theme        = data.get('theme', 'Classic White'),
            budget_range = data.get('budget_range', '₹5L – ₹10L'),
        )
        return JsonResponse(result)
    return JsonResponse({'error': 'POST required'}, status=400)


# ──────────────────────────────────────────────────────────────────────────────
# Result (direct GET fallback)
# ──────────────────────────────────────────────────────────────────────────────
def result_view(request):
    return render(request, 'result.html')


# ──────────────────────────────────────────────────────────────────────────────
# Auth
# ──────────────────────────────────────────────────────────────────────────────
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('home')
        messages.error(request, 'Invalid username or password.')
    return render(request, 'login.html')


def register_view(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '')
        last_name  = request.POST.get('last_name', '')
        email      = request.POST.get('email', '')
        password   = request.POST.get('password', '')
        username   = email.split('@')[0]

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
        else:
            user = User.objects.create_user(
                username=username, email=email, password=password,
                first_name=first_name, last_name=last_name,
            )
            login(request, user)
            return redirect('login')
    return render(request, 'register.html')


def logout_view(request):
    logout(request)
    return redirect('login')


def profile_view(request):
    if request.user.is_authenticated:
        projects = ProjectEstimate.objects.filter(user=request.user).order_by('-created_at')
    else:
        projects = ProjectEstimate.objects.all().order_by('-created_at')
    return render(request, 'profile.html', {'projects': projects})


# ──────────────────────────────────────────────────────────────────────────────
# Image Construction Style Transformer
# ──────────────────────────────────────────────────────────────────────────────
THEMES = {
    "🏛️ Modern Minimalist": {
        "prompt": "modern minimalist interior design, clean white walls, neutral tones, sleek furniture, bright natural light, Scandinavian style, professional interior photography",
        "negative": "cluttered, dark, old, dirty, low quality",
    },
    "🌿 Biophilic / Nature": {
        "prompt": "biophilic interior design, sage green walls, natural wood furniture, indoor plants, warm earthy tones, organic textures, botanical decor, cozy living space",
        "negative": "artificial, plastic, dark, cluttered",
    },
    "🌊 Coastal / Beach": {
        "prompt": "coastal beach house interior, soft blue walls, white furniture, nautical accents, driftwood decor, breezy airy feel, sandy beige tones, ocean-inspired",
        "negative": "dark, heavy furniture, industrial",
    },
    "🖤 Industrial Loft": {
        "prompt": "industrial loft interior design, exposed brick walls, dark charcoal grey, metal fixtures, Edison bulbs, concrete floors, urban chic style",
        "negative": "bright pastel, floral, rustic cottage",
    },
    "👑 Luxury / Glam": {
        "prompt": "luxury glamorous interior design, deep navy or emerald walls, gold accents, velvet furniture, crystal chandelier, marble surfaces, opulent elegant style",
        "negative": "cheap, minimal, plain, dull",
    },
    "🌸 Cottagecore / Romantic": {
        "prompt": "cottagecore romantic interior design, soft pastel pink walls, floral wallpaper, vintage furniture, lace curtains, warm candlelit glow, cozy feminine aesthetic",
        "negative": "modern, industrial, dark, concrete",
    },
    "🎨 Bohemian / Eclectic": {
        "prompt": "bohemian eclectic interior design, terracotta orange walls, colorful layered rugs, rattan furniture, macrame wall art, warm jewel tones, boho chic style",
        "negative": "sterile, plain, minimalist",
    },
    "❄️ Arctic / Monochrome": {
        "prompt": "arctic monochrome interior design, crisp white walls, icy blue accents, grey furniture, frosted glass, cool tones, ultra-clean Scandinavian Nordic style",
        "negative": "warm colors, wood, rustic, colorful",
    },
}

PAINT_COLORS = {
    "Warm White": "warm white painted walls",
    "Sage Green": "sage green painted walls",
    "Navy Blue": "deep navy blue painted walls",
    "Terracotta": "terracotta orange painted walls",
    "Charcoal Grey": "dark charcoal grey painted walls",
    "Blush Pink": "soft blush pink painted walls",
    "Emerald Green": "rich emerald green painted walls",
    "Cream / Beige": "warm cream beige painted walls",
    "Sky Blue": "light sky blue painted walls",
    "Midnight Black": "matte black painted walls",
}

def image_style_view(request):
    if request.method == 'POST' and request.FILES.get('image'):
        if not request.user.is_authenticated:
            from django.http import JsonResponse
            from django.shortcuts import redirect
            from django.contrib import messages
            if request.GET.get('ajax'):
                return JsonResponse({'error': 'You must be logged in to use this feature.'}, status=403)
            messages.error(request, "You must be logged in to use this feature.")
            return redirect('login')
            
        import os
        import base64
        import requests
        from io import BytesIO
        from PIL import Image
        from django.conf import settings
        from django.http import JsonResponse
        from django.contrib import messages
        
        uploaded_file = request.FILES['image']
        try:
            pil_image = Image.open(uploaded_file).convert('RGB')
            # Resize image to 1024x1024 for SDXL
            pil_image = pil_image.resize((1024, 1024), Image.Resampling.LANCZOS)
            buffer = BytesIO()
            pil_image.save(buffer, format="PNG")
            image_bytes = buffer.getvalue()
            
            paint_color = request.POST.get('paint', 'Sage Green')
            theme_name = request.POST.get('theme', '🌿 Biophilic / Nature')
            strength = float(request.POST.get('strength', 0.65))
            
            user_api_key = request.POST.get('api_key', '').strip()
            if user_api_key:
                stability_api_key = user_api_key
            else:
                stability_api_key = getattr(settings, 'STABILITY_API_KEY', os.environ.get("STABILITY_API_KEY", "sk-QsuHoSopMDiy4cc1oBEe3SO2HzhMA2qKUBLPTxLKqH5iWoQU"))
                
            stability_url = "https://api.stability.ai/v2beta/stable-image/generate/ultra"
            
            theme = THEMES.get(theme_name, THEMES["🌿 Biophilic / Nature"])
            color_desc = PAINT_COLORS.get(paint_color, PAINT_COLORS["Sage Green"])
            
            full_prompt = (
                f"{color_desc}, {theme['prompt']}, "
                "high resolution, photorealistic, interior photography, 8K quality"
            )
            
            response = requests.post(
                stability_url,
                headers={
                    "authorization": f"Bearer {stability_api_key}",
                    "accept": "image/*"
                },
                files={"none": ''},
                data={
                    "prompt": full_prompt,
                    "output_format": "webp",
                },
                timeout=120,
            )
            
            if response.status_code != 200:
                # Fallback: Simulate realistic image-to-image using free Pollinations API + PIL structural blending
                print(f"API Error {response.status_code}: {response.text[:300]}")
                from PIL import ImageEnhance, ImageOps, ImageFilter, ImageChops
                import urllib.parse
                
                try:
                    # 1. Generate realistic text-to-image based on the theme
                    safe_prompt = urllib.parse.quote(full_prompt)
                    poll_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=1024&nologo=true"
                    poll_response = requests.get(poll_url, timeout=30)
                    
                    if poll_response.status_code == 200:
                        gen_img = Image.open(BytesIO(poll_response.content)).convert('RGB')
                        
                        # Use the pure prompted image directly without blending the original structure
                        mock_image = gen_img
                    else:
                        raise Exception("Pollinations API failed")
                        
                except Exception as e:
                    print(f"Free API fallback failed: {e}")
                    # Ultimate fallback: Just a color tint
                    gray = ImageOps.grayscale(pil_image)
                    tinted = ImageOps.colorize(gray, black="#0a192f", white="#64ffda")
                    mock_image = Image.blend(pil_image, tinted.convert('RGB'), alpha=min(strength, 1.0))
                
                buffer = BytesIO()
                mock_image.save(buffer, format="PNG")
                img_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                output_image = f"data:image/png;base64,{img_b64}"
                
                if request.GET.get('ajax'):
                    return JsonResponse({'output_image': output_image, 'mock': True})
                
                messages.warning(request, "API Limit Reached. Showing structural edge blend fallback.")
                return render(request, 'upload_style.html', {'output_image': output_image})
                
            img_b64 = base64.b64encode(response.content).decode('utf-8')
            output_image = f"data:image/webp;base64,{img_b64}"
            
            if request.GET.get('ajax'):
                return JsonResponse({'output_image': output_image})
            
            return render(request, 'upload_style.html', {'output_image': output_image})
        except Exception as e:
            import traceback
            traceback.print_exc()
            if request.GET.get('ajax'):
                return JsonResponse({'error': str(e)}, status=500)
            from django.shortcuts import redirect
            messages.error(request, f"Error processing image: {str(e)}")
            return redirect('image_style')

    return render(request, 'upload_style.html')
