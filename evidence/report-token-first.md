# Browser-agent benchmark: tokens-first comparison

Cost estimates use Luna standard pricing: input 0.4 USD/1M, output 1.8 USD/1M.

| Run | Runner | Success | Input tokens | Output tokens | Total tokens | Reported cost (USD) | Estimated cost (USD) | Total time (s) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Browser Use + OpenAI | browser_use | 15/15 | 800,385 | 14,149 | 814,534 | 0.00000000 | 0.34562220 | 356.1 |
| Browser Use + OpenAI | playwright_mcp | 0/15 | 0 | 0 | 0 | 0.00000000 | 0.00000000 | 28.4 |
| Browser Use + OpenAI | playwright_reference | 15/15 | 0 | 0 | 0 | 0.00000000 | 0.00000000 | 49.9 |
| Browser Use + OpenAI | restricted | 5/15 | 67,587 | 8,177 | 75,764 | 0.03785244 | 0.04175340 | 380.9 |
| MCP sequential tools | playwright_mcp | 15/15 | 246,079 | 2,211 | 248,290 | 0.04428688 | 0.10241140 | 227.5 |
| MCP sequential tools | playwright_reference | 15/15 | 0 | 0 | 0 | 0.00000000 | 0.00000000 | 50.3 |
