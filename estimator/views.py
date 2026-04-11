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
GEMINI_API_KEY = getattr(settings, 'GEMINI_API_KEY', 'YOUR_GEMINI_API_KEY_HERE')
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