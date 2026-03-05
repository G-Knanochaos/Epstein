# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Django "Higher or Lower" guessing game where players compare how many times celebrities appear in Epstein-related DOJ documents. Players are shown two celebrity cards and guess whether the right celebrity has more or fewer document mentions than the left.

## Commands

```bash
# Run dev server
python manage.py runserver

# Apply migrations
python manage.py migrate

# Load celebrity data from celebrities.json into DB
python manage.py load_celebrities
python manage.py load_celebrities --clear   # wipe table first

# Run tests
python manage.py test game

# Refresh celebrity data (scrapes DOJ + Wikipedia, writes celebrities.json)
python scrape_celebrities.py            # full pipeline
python scrape_celebrities.py --doj      # only DOJ mention counts
python scrape_celebrities.py --wiki     # only Wikipedia data
```

## Architecture

**Django project:** `epstein_game/` (settings, URLs root)
**Game app:** `game/` — all game logic lives here

### Data flow

1. `scrape_celebrities.py` — standalone script that scrapes DOJ multimedia-search for Epstein mention counts and Wikipedia for bios/images, outputs `celebrities.json`
2. `python manage.py load_celebrities` — reads `celebrities.json` and upserts into the SQLite `Celebrity` model
3. The game serves from the DB at runtime

### Game logic

- `game/views.py`: Two endpoints — `game` (renders initial pair) and `check_guess` (AJAX POST)
- `check_guess` accepts `left_id`, `right_id`, `guess` (`higher`/`lower`), `score`; returns JSON with correctness, updated score, new card data
- Equal `epstein_mentions` counts always count as correct
- On a correct guess: old right card becomes new left; a fresh right card is randomly selected
- `game/templates/game/game.html` — single-page UI; all subsequent rounds handled via fetch/AJAX without page reload

### Model

`Celebrity` fields: `full_name`, `description`, `extract`, `image_url`, `wikipedia_url`, `wikipedia_slug`, `epstein_mentions`
Default ordering: `-epstein_mentions`

### Scraper notes

`scrape_celebrities.py` uses hardcoded DOJ session cookies (`DOJ_COOKIES`) that expire — if DOJ counts return errors, the cookies need to be refreshed from a browser session on `justice.gov/epstein`.

When running or modifying scraping tasks, always use Python directly (e.g. `python scrape_celebrities.py`). Do not use bash commands such as `curl`, `wget`, or shell one-liners to fetch data.
