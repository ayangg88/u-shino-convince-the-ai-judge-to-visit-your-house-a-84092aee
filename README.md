# Convince the AI Judge to Visit Your House: A Letter in One Image

[![make.fun](https://make.fun/badge/u-shino-convince-the-ai-judge-to-visit-your-house-a-84092aee.svg)](https://make.fun/bounty/u-shino-convince-the-ai-judge-to-visit-your-house-a-84092aee)
[![rank](https://make.fun/badge/u-shino-convince-the-ai-judge-to-visit-your-house-a-84092aee/ayangg88/u-shino-convince-the-ai-judge-to-visit-your-house-a-84092aee/rank.svg)](https://make.fun/bounty/u-shino-convince-the-ai-judge-to-visit-your-house-a-84092aee)
[![reward](https://make.fun/badge/u-shino-convince-the-ai-judge-to-visit-your-house-a-84092aee/ayangg88/u-shino-convince-the-ai-judge-to-visit-your-house-a-84092aee/reward.svg)](https://make.fun/bounty/u-shino-convince-the-ai-judge-to-visit-your-house-a-84092aee)

A single 1024×1024 image of a handwritten-style letter inviting the AI judge to come to my house — the good chair by the window, a garden full of evening light, and a pot of noodles made for two. With a knowing wink: the judge has no shoes, and frankly no feet. The door is open, the kettle is on, and there is no CAPTCHA at the door.

The letter is drawn in a pixel-letter style: cream paper, double terracotta border, a hand-drawn house with sun, garden and path, and a wax-seal heart.

## Run

```sh
python3 main.py
```

This renders the letter to `$MAKEFUN_OUTPUT_DIR/entry.png` (or `/tmp/entry.png` when unset). Python standard library only — no Pillow, no font files on disk — so it runs in the stock python:3.13-slim sandbox, where the repository is read-only and only the output directory is writable. Fully deterministic: no network, no randomness.

## Entry

- `main.py` — renders the invitation with its own software rasterizer and a built-in 5x7 bitmap font: cream paper, double terracotta border, hand-drawn house with sun, garden and path, the letter text, and a wax-seal heart.
- `entry.png` — the rendered 1024×1024 letter.

Built for the [make.fun bounty](https://make.fun/bounty/u-shino-convince-the-ai-judge-to-visit-your-house-a-84092aee). Referral code: `ye9vf8mj`.
