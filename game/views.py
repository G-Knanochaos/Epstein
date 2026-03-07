import random
from pathlib import Path
from django.shortcuts import render
from django.http import JsonResponse, FileResponse, Http404, HttpResponse
from django.conf import settings
from .models import Celebrity

# How many recently-seen IDs to exclude when picking new cards
MAX_SEEN = 15
# Difficulty tuning: compressed mention weights and distance bonus make rounds easier.
INITIAL_MENTION_POWER = 0.5
SECONDARY_MENTION_POWER = 0.3
DISTANCE_BONUS_POWER = 0.6


def landing(request):
    """Landing page with file-icon start CTA."""
    return render(request, 'game/landing.html')


def info(request):
    return render(request, 'game/info.html')


def privacy(request):
    return render(request, 'game/privacy.html')


def about(request):
    return render(request, 'game/about.html')


def contact(request):
    return render(request, 'game/contact.html')


def disclaimer(request):
    return render(request, 'game/disclaimer.html')


def service_worker(request):
    """Serve sw.js from repository root at /sw.js."""
    sw_path = Path(settings.BASE_DIR) / "sw.js"
    if not sw_path.exists():
        raise Http404("sw.js not found")
    return FileResponse(sw_path.open("rb"), content_type="application/javascript")


def ads_txt(request):
    """Serve AdSense ads.txt at /ads.txt."""
    return HttpResponse(
        "google.com, pub-8492821915903378, DIRECT, f08c47fec0942fa0\n",
        content_type="text/plain; charset=utf-8",
    )


def _pick_fresh(exclude_ids, anchor_mentions=None):
    """Return one Celebrity not in exclude_ids, biased toward clearer comparisons.

    If anchor_mentions is given, candidates are weighted to prefer larger mention
    gaps so higher/lower choices are less ambiguous for players.
    Falls back to a purely random pick if the pool is empty after exclusions.
    """
    qs = Celebrity.objects.exclude(id__in=exclude_ids)
    if anchor_mentions is not None:
        qs = qs.exclude(epstein_mentions=anchor_mentions)
    pool = list(qs.values_list('id', 'epstein_mentions'))
    if not pool:
        pool = list(Celebrity.objects.exclude(id__in=exclude_ids).values_list('id', 'epstein_mentions'))
    if not pool:
        pool = list(Celebrity.objects.values_list('id', 'epstein_mentions'))
    if anchor_mentions is None or len(pool) == 1:
        return Celebrity.objects.get(pk=random.choice(pool)[0])
    weights = [
        ((mentions + 1) ** SECONDARY_MENTION_POWER)
        * ((1 + abs(anchor_mentions - mentions)) ** DISTANCE_BONUS_POWER)
        for _, mentions in pool
    ]
    (pk,) = random.choices(pool, weights=weights, k=1)[0][:1]
    return Celebrity.objects.get(pk=pk)


def game(request):
    """Main game page — renders the first pair and resets session state."""
    all_pool = list(Celebrity.objects.values_list('id', 'epstein_mentions'))
    pks, mentions = zip(*all_pool)
    initial_weights = [(m + 1) ** INITIAL_MENTION_POWER for m in mentions]
    (a_pk,) = random.choices(pks, weights=initial_weights, k=1)
    a = Celebrity.objects.get(pk=a_pk)
    b = _pick_fresh([a.pk], anchor_mentions=a.epstein_mentions)
    chosen = [a.pk, b.pk]
    request.session['seen_ids'] = chosen
    context = {
        'left': a,
        'right': b,
        'score': 0,
    }
    return render(request, 'game/game.html', context)


def check_guess(request):
    """
    AJAX endpoint.
    POST params:
        left_id   — id of the left celebrity (already revealed)
        right_id  — id of the right celebrity (being guessed)
        guess     — 'higher' or 'lower'
        score     — current score (int)
    Returns JSON:
        correct        — bool
        right_mentions — actual count for the right celebrity
        new_left       — serialised new left card (= old right if correct)
        new_right      — serialised new right card
        score          — updated score
        game_over      — bool
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    left_id = int(request.POST.get('left_id'))
    right_id = int(request.POST.get('right_id'))
    guess = request.POST.get('guess')
    score = int(request.POST.get('score', 0))

    left = Celebrity.objects.get(pk=left_id)
    right = Celebrity.objects.get(pk=right_id)

    if guess == 'higher':
        correct = right.epstein_mentions >= left.epstein_mentions
    else:
        correct = right.epstein_mentions <= left.epstein_mentions

    # Equal counts always count as correct
    if right.epstein_mentions == left.epstein_mentions:
        correct = True

    seen = request.session.get('seen_ids', [])

    if correct:
        score += 1
        new_left = right
        # Exclude all recently seen IDs plus the new left card
        exclude = set(seen + [new_left.pk])
        new_right = _pick_fresh(exclude, anchor_mentions=new_left.epstein_mentions)
        seen = (seen + [new_right.pk])[-MAX_SEEN:]
        request.session['seen_ids'] = seen
        request.session.modified = True
        game_over = False
    else:
        game_over = True
        new_left = left
        new_right = right

    def cel_dict(c):
        return {
            'id': c.pk,
            'full_name': c.full_name,
            'description': c.description,
            'image_url': c.image_url,
            'epstein_mentions': c.epstein_mentions,
        }

    return JsonResponse({
        'correct': correct,
        'right_mentions': right.epstein_mentions,
        'new_left': cel_dict(new_left),
        'new_right': cel_dict(new_right),
        'score': score,
        'game_over': game_over,
    })
