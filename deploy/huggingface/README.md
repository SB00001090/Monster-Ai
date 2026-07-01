---
title: Monster AI Demo
emoji: 🦖
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
license: mit
---

# Monster AI — Hugging Face Space Demo

Developed by Suckbob | Monster AI

Public demo proxying your **Cloudflare Tunnel** backend.

## Secrets (Space Settings)

| Secret | Value |
|--------|-------|
| `MONSTER_API_URL` | `https://your-tunnel.trycloudflare.com` |
| `MIN_QUALITY_SCORE` | `0.70` |

## Deploy

1. Create Space from this folder
2. Set secrets above
3. Ensure local `python main.py` + Tunnel running

## Features

- Text-to-image via Mini Monster AI
- 70% quality gate display
- Links to full UI: https://monster-ai.pages.dev