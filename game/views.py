import random
from django.shortcuts import render
from django.http import JsonResponse
from .models import Celebrity

# How many recently-seen IDs to exclude when picking new cards
MAX_SEEN = 15


def landing(request):
    """Landing page with file-icon start CTA."""
    return render(request, 'game/landing.html')


def _pick_fresh(exclude_ids):
    """Return one Celebrity not in exclude_ids (falls back to full pool if needed)."""
    pool = list(Celebrity.objects.exclude(id__in=exclude_ids).values_list('id', flat=True))
    if not pool:
        pool = list(Celebrity.objects.values_list('id', flat=True))
    return Celebrity.objects.get(pk=random.choice(pool))


def game(request):
    """Main game page — renders the first pair and resets session state."""
    all_pks = list(Celebrity.objects.values_list('id', flat=True))
    chosen = random.sample(all_pks, 2)
    a = Celebrity.objects.get(pk=chosen[0])
    b = Celebrity.objects.get(pk=chosen[1])
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
        new_right = _pick_fresh(exclude)
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
