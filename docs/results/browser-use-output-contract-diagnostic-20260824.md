# browser-use output-contract diagnostic

This English-only diagnostic ran two repetitions of each of five public tasks with browser-use. It is a separate diagnostic stratum and is not pooled with the prior repeated sample. All trials used 600-second task timeouts, 48 actions, 24 requests, 150,000 cumulative tokens, 30,000 completion tokens per response, USD 0.07/trial and verified forced cleanup.

## Result

| Model | Success | JSON/schema diagnostics | Known cost (USD) |
|---|---:|---:|---:|
| `openai/gpt-5.6-luna` | 2/10 | 8/10 | 0.03114966 |
| `openai/gpt-4.1-mini` | 2/10 | 0/10 | 0.11049520 |

The original model emitted two JSON objects in one response for eight of ten trials, each with `finish_reason: "stop"`; this rejects the token-truncation explanation. `openai/gpt-4.1-mini` produced no JSON/schema diagnostic in ten trials, confirming the malformed-JSON issue is model-specific. Its remaining failures are framework/acceptance outcomes, including two OpenRouter HTTP 400 responses whose response bodies were not retained by the earlier adapter version.

## Per-trial evidence

| Model | Trial | Task | Outcome | Requests | Tokens | Cost (USD) | Adapter diagnostic | SHA-256 |
|---|---|---|---|---:|---:|---:|---|---|
| `openai/gpt-5.6-luna` | `browser_use-r4-2ccbc82d0016` | selenium-web-form-en | passed | 9 | 75,561 | 0.00543362 | — | `1fa98dea3dc1e402a92d01f4f8cb896d556b941934ffc70faad0915783ca4278` |
| `openai/gpt-5.6-luna` | `browser_use-r4-4cc7bb224097` | mdn-reference-en | failed | 3 | 28,401 | 0.00420659 | invalid_json / stop | `1966c7f43038378abd0bd24c3aa57fbec432852e96c08b5a503349a9de398d53` |
| `openai/gpt-5.6-luna` | `browser_use-r4-cc9eac8ed422` | selenium-ajax-labels-en | failed | 3 | 25,959 | 0.00466009 | invalid_json / stop | `dbfaa7dfd25fa66c3c9fe00085e0fba0f4b998895773fd6a35014948ee48acfc` |
| `openai/gpt-5.6-luna` | `browser_use-r4-e7b3beb8b2c0` | wikipedia-search-en | failed | 1 | 8,535 | 0.00076323 | invalid_json / stop | `57345f14294c2915b8efbc4e3dfdfe00bfcac6af6971f4ae277d399b33a71f54` |
| `openai/gpt-5.6-luna` | `browser_use-r4-fe9a3632ea8e` | selenium-key-events-en | failed | 1 | 9,077 | 0.00217268 | invalid_json / stop | `bd87cec52ad2d77338f8087a9fe7ac88c708ec31c86648a32c6d5f1b03e509cc` |
| `openai/gpt-5.6-luna` | `browser_use-r5-1263860414ad` | selenium-web-form-en | failed | 1 | 10,069 | 0.00286718 | invalid_json / stop | `63d9e7121738794b76cecc51575331b5a9be72f9e8d13f87b1a5805ce45a6fd9` |
| `openai/gpt-5.6-luna` | `browser_use-r5-2e1a53a597e5` | selenium-key-events-en | failed | 1 | 9,690 | 0.00290448 | invalid_json / stop | `4fb46b1f1b771c3dcd2e48ff053e922735efb96afd7ad0ade07b9916490501aa` |
| `openai/gpt-5.6-luna` | `browser_use-r5-a4e76ceafa75` | mdn-reference-en | failed | 1 | 11,072 | 0.00341148 | invalid_json / stop | `cf04719cae34aefd1bc0e3d1580fcceaebaf6d0524e04949cb2ca81ddc58ebfc` |
| `openai/gpt-5.6-luna` | `browser_use-r5-d775c18cc447` | wikipedia-search-en | passed | 3 | 28,165 | 0.00261144 | — | `5bea1c17bb12f8c8825a94f92dea0f3647ae6da60e44cd0f37968b2117e59736` |
| `openai/gpt-5.6-luna` | `browser_use-r5-da054ae961bc` | selenium-ajax-labels-en | failed | 4 | 31,293 | 0.00211887 | invalid_json / stop | `fc710be37738668f66b03dcac28a07c75b623de858c50d5a05de2e77ee5ec8bf` |
| `openai/gpt-4.1-mini` | `browser_use-r6-4b4827945376` | selenium-ajax-labels-en | failed | 4 | 31,190 | 0.00529520 | — | `d313780345cce328a0839d69fb2bfc08d97836376c6324b06727ba257b2698c8` |
| `openai/gpt-4.1-mini` | `browser_use-r6-674476294ec9` | mdn-reference-en | passed | 5 | 49,143 | 0.01050360 | — | `a2d9e8232a881e5b67d3fbfa165ee56a2ca0a40ffab493ff74c6c999ac692e6d` |
| `openai/gpt-4.1-mini` | `browser_use-r6-78198283e1a5` | selenium-web-form-en | failed | 11 | 96,264 | 0.01826760 | — | `5a8e8a0c5239211ede5aadf9eec17f69cb3be24415a6ac3f67a2af20d3a6f5d1` |
| `openai/gpt-4.1-mini` | `browser_use-r6-a01fd5a2ad61` | wikipedia-search-en | failed | 3 | 28,131 | 0.00576240 | — | `5cddfef8326cc5a16bd48c3962d47dd77b60338a7973c5934fb64b351d625455` |
| `openai/gpt-4.1-mini` | `browser_use-r6-a124c0f11f50` | selenium-key-events-en | failed | 8 | 63,050 | 0.01175720 | — | `37ff5bafac9768eb1ea233ee29d6afdc176db0a5abc194eca9525d94cf3432b2` |
| `openai/gpt-4.1-mini` | `browser_use-r7-291492553da3` | mdn-reference-en | failed | 7 | 74,697 | 0.01677720 | — | `432e484f1d1d7c0b49713989635a9dda02eb59811d70d6e0e74c99954d5bf5d5` |
| `openai/gpt-4.1-mini` | `browser_use-r7-3a180e2b7b86` | selenium-ajax-labels-en | passed | 9 | 72,578 | 0.01227200 | — | `3bf09b379a4f7c864c4cbec45b84558c91a7cda4405dfdeb7160f6f5c3d75bca` |
| `openai/gpt-4.1-mini` | `browser_use-r7-9d677f789260` | wikipedia-search-en | failed | 3 | 28,155 | 0.00549120 | — | `da95f8855a4279fd2e438ed6bd59a34fd06b0ff229698103a8bdd79155df7b33` |
| `openai/gpt-4.1-mini` | `browser_use-r7-a092701d1295` | selenium-web-form-en | failed | 8 | 67,696 | 0.01445800 | — | `58891abc1bbea23e69c1f59ae98fffd0962b200cda9d46e1bf40e90a9e847cb7` |
| `openai/gpt-4.1-mini` | `browser_use-r7-b198f18f075b` | selenium-key-events-en | failed | 8 | 63,111 | 0.00991080 | — | `bf2a7eed6fcad8866d17075fbd2b4aeb5d6872681c873f48e39458b72197cf2b` |
