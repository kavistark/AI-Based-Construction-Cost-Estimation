"""
ConstructAI — Views
Upgraded with: real ML model, full auth.
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

        if estimation['total_cost'] > 0:
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
                'inputs': {
                    'area': plot_area, 'rooms': rooms, 'material': material,
                    'paint': paint, 'house_type': house_type, 'room_type': room_type,
                    'theme': theme, 'budget_range': budget_range,
                }
            })

    return render(request, 'home.html')


# ──────────────────────────────────────────────────────────────────────────────
# AJAX live estimate (no DB save)
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
                
            stability_url = "https://api.stability.ai/v2beta/stable-image/generate/sd3"
            
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
                files={
                    "image": ("image.png", image_bytes, "image/png")
                },
                data={
                    "prompt": full_prompt,
                    "mode": "image-to-image",
                    "strength": strength,
                    "output_format": "webp",
                },
                timeout=120,
            )
            
            if response.status_code != 200:
                # Fallback: Simulate realistic image-to-image using free Pollinations API + PIL structural blending
                print(f"API Error {response.status_code}: {response.text[:300]}")
                from PIL import ImageEnhance, ImageOps, ImageFilter, ImageChops
                import urllib.parse
                
                FALLBACK_COLORS = {
                    "Warm White": ("#2a2a2a", "#fffff0"),
                    "Sage Green": ("#1c2e22", "#9dc183"),
                    "Navy Blue": ("#051024", "#203a66"),
                    "Terracotta": ("#3d1c10", "#cc664d"),
                    "Charcoal Grey": ("#101010", "#444444"),
                    "Blush Pink": ("#38202b", "#e09ebb"),
                    "Emerald Green": ("#082414", "#3d9e60"),
                    "Cream / Beige": ("#2a251a", "#e8dec3"),
                    "Sky Blue": ("#102436", "#87bde0"),
                    "Midnight Black": ("#000000", "#222222"),
                }
                
                try:
                    # Apply a structural PIL filter to style the original image
                    gray = ImageOps.grayscale(pil_image)
                    dark, light = FALLBACK_COLORS.get(paint_color, ("#0a192f", "#64ffda"))
                    tinted = ImageOps.colorize(gray, black=dark, white=light)
                    
                    # Add contrast
                    enhancer = ImageEnhance.Contrast(tinted)
                    tinted = enhancer.enhance(1.2)
                    
                    # Blend with the original image based on strength
                    mock_image = Image.blend(pil_image, tinted.convert('RGB'), alpha=min(strength, 1.0))
                except Exception as e:
                    print(f"Fallback filter failed: {e}")
                    mock_image = pil_image
                
                buffer = BytesIO()
                mock_image.save(buffer, format="PNG")
                img_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                output_image = f"data:image/png;base64,{img_b64}"
                
                if request.GET.get('ajax'):
                    error_msg = f"API Error {response.status_code}. (Check your credits). Showing basic color filter fallback."
                    return JsonResponse({'output_image': output_image, 'mock': True, 'api_error': error_msg})
                
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
