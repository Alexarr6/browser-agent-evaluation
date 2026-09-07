# Repeated browser-agent evaluation

This report covers one unified matrix of **7 tasks** (5 standard and 2 experimental), 3 repetitions and 4 runners. Experimental tasks are labelled because their acceptance criteria are less mature, but they are planned and reported exactly like the standard tasks.

> A pass means that the configured end-state assertions succeeded. It does not prove that every semantic detail of the natural-language task was independently verified.

## Run configuration

| Property | Value |
|---|---|
| Created | 2026-09-07T12:20:04.765549+00:00 |
| Language | en |
| Model | `gpt-5.6-luna` |
| Provider endpoint | `https://api.openai.com/v1` |
| Rendering | `visual-parity` |
| Browser mode | headless |
| Reference policy | always run AI |
| Rounds | 1, 2, 3 |
| Seeds | 20260824, 20260825, 20260826 |
| Planned trial slots | 84 |
| Reference/MCP/restricted browser | Chromium 140.0.7339.16 |
| browser-use browser | Chromium 140.0.7339.16 |

## Task contracts

| Task | Category | Assertions | Timeout | Action cap | Contract |
|---|---|---|---:|---:|---|
| Wikipedia (English) | standard | `page_title`, `url_contains` | 300s | 48 | `wikipedia-search-en.yaml` (`7dc0d11b9912`) |
| MDN (English) | standard | `url_contains`, `visible_text` | 300s | 48 | `mdn-reference-en.yaml` (`5b01320dec1c`) |
| Selenium web form (English) | standard | `url_contains`, `visible_text` | 300s | 48 | `selenium-web-form-en.yaml` (`1ea033273019`) |
| Selenium AJAX labels (English) | standard | `visible_text` | 300s | 48 | `selenium-ajax-labels-en.yaml` (`20d69ab69c50`) |
| Selenium key events (English) | standard | `visible_text` | 300s | 48 | `selenium-key-events-en.yaml` (`6396e6a6740b`) |
| Marca Real Madrid (English) | experimental | `visible_text` | 300s | 48 | `marca-real-madrid-open-en.yaml` (`97b0780359ba`) |
| Amazon cheapest coffee beans (English) | experimental | `url_contains` | 300s | 48 | `amazon-cheapest-coffee-beans-en.yaml` (`18e5e01feb18`) |

## Per-task results

Success uses valid trials as its denominator. `Invalid` identifies trials without comparable cleanup evidence. `Ref-skipped` records planned AI trials that were not started because the deterministic reference failed.

| Task | Category | Runner | Success | Invalid | Ref-skipped | Median passing time | Requests | Tokens | Cost (USD) |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| Wikipedia (English) | standard | Deterministic reference | 0/3 | 0 | 0 | — | 0 | — | — |
| Wikipedia (English) | standard | Restricted agent | 3/3 | 0 | 0 | 15.109s | 14 | 49,858 | 0.01793220 |
| Wikipedia (English) | standard | browser-use | 3/3 | 0 | 0 | 17.332s | 12 | 108,735 | unavailable (3 trials) |
| Wikipedia (English) | standard | Playwright MCP | 3/3 | 0 | 0 | 7.503s | 9 | 52,571 | 0.00973776 |
| MDN (English) | standard | Deterministic reference | 3/3 | 0 | 0 | 0.874s | 0 | — | — |
| MDN (English) | standard | Restricted agent | 2/3 | 0 | 0 | 16.622s | 14 | 45,124 | 0.01794856 |
| MDN (English) | standard | browser-use | 3/3 | 0 | 0 | 17.745s | 15 | 144,037 | unavailable (3 trials) |
| MDN (English) | standard | Playwright MCP | 3/3 | 0 | 0 | 12.554s | 16 | 186,734 | 0.02735664 |
| Selenium web form (English) | standard | Deterministic reference | 3/3 | 0 | 0 | 31.096s | 0 | — | — |
| Selenium web form (English) | standard | Restricted agent | 3/3 | 0 | 0 | 19.178s | 24 | 38,395 | 0.01183600 |
| Selenium web form (English) | standard | browser-use | 3/3 | 0 | 0 | 29.125s | 27 | 227,911 | unavailable (3 trials) |
| Selenium web form (English) | standard | Playwright MCP | 3/3 | 0 | 0 | 13.878s | 24 | 102,040 | 0.01162152 |
| Selenium AJAX labels (English) | standard | Deterministic reference | 3/3 | 0 | 0 | 12.523s | 0 | — | — |
| Selenium AJAX labels (English) | standard | Restricted agent | 3/3 | 0 | 0 | 30.153s | 21 | 26,660 | 0.00996268 |
| Selenium AJAX labels (English) | standard | browser-use | 3/3 | 0 | 0 | 31.999s | 26 | 206,676 | unavailable (3 trials) |
| Selenium AJAX labels (English) | standard | Playwright MCP | 3/3 | 0 | 0 | 17.813s | 21 | 40,836 | 0.00505164 |
| Selenium key events (English) | standard | Deterministic reference | 3/3 | 0 | 0 | 0.624s | 0 | — | — |
| Selenium key events (English) | standard | Restricted agent | 3/3 | 0 | 0 | 23.818s | 24 | 30,949 | 0.01356612 |
| Selenium key events (English) | standard | browser-use | 3/3 | 0 | 0 | 23.579s | 24 | 189,127 | unavailable (3 trials) |
| Selenium key events (English) | standard | Playwright MCP | 3/3 | 0 | 0 | 11.952s | 24 | 40,989 | 0.00451872 |
| Marca Real Madrid (English) | experimental | Deterministic reference | 3/3 | 0 | 0 | 1.782s | 0 | — | — |
| Marca Real Madrid (English) | experimental | Restricted agent | 0/3 | 0 | 0 | — | 9 | 32,873 | 0.01505180 |
| Marca Real Madrid (English) | experimental | browser-use | 3/3 | 0 | 0 | 23.321s | 10 | 104,672 | unavailable (3 trials) |
| Marca Real Madrid (English) | experimental | Playwright MCP | 3/3 | 0 | 0 | 69.760s | 9 | 121,889 | 0.02712332 |
| Amazon cheapest coffee beans (English) | experimental | Deterministic reference | 3/3 | 0 | 0 | 0.857s | 0 | — | — |
| Amazon cheapest coffee beans (English) | experimental | Restricted agent | 0/3 | 0 | 0 | — | 14 | 49,456 | 0.02208400 |
| Amazon cheapest coffee beans (English) | experimental | browser-use | 2/3 | 0 | 0 | 124.378s | 38 | 678,293 | unavailable (3 trials) |
| Amazon cheapest coffee beans (English) | experimental | Playwright MCP | 0/3 | 0 | 0 | — | 39 | 1,679,345 | 0.15149980 |

## Runner aggregate

| Runner | Success | Invalid | Ref-skipped | Median passing time | Requests | Tokens | Cost (USD) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Deterministic reference | 18/21 | 0 | 0 | 1.504s | 0 | — | — |
| Restricted agent | 14/21 | 0 | 0 | 21.343s | 120 | 273,315 | 0.10838136 |
| browser-use | 20/21 | 0 | 0 | 23.828s | 152 | 1,659,451 | unavailable (21 trials) |
| Playwright MCP | 18/21 | 0 | 0 | 13.987s | 142 | 2,224,404 | 0.23690940 |

## Aggregate observations

- Highest observed AI success rate: browser-use (20/21).
- Lowest median duration among successful AI trials: Playwright MCP (13.987s). This is not a like-for-like speed ranking when runners fail different task mixes.
- Lowest reported AI token consumption: Restricted agent (273,315 tokens across all its attempts).
- A complete cost ranking is unavailable because cost was not reported for browser-use.
- Deterministic-reference failures require separate inspection and are potential site or harness confounds: Wikipedia (English) (3/3).
- Observed Restricted agent failures: MDN (English) (1/3), Marca Real Madrid (English) (3/3), Amazon cheapest coffee beans (English) (3/3).
- Observed browser-use failures: Amazon cheapest coffee beans (English) (1/3).
- Observed Playwright MCP failures: Amazon cheapest coffee beans (English) (3/3).

## Limits and interpretation warnings

- Cost limit: USD 2.00 per round; per-trial limit: USD 0.25.
- Per-trial limits: 48 model requests and 1,000,000 cumulative tokens. Task-specific time and action limits appear above.
- Failed and invalidated attempts remain in request, token and known-cost totals. Missing tokens or cost are labelled unavailable rather than converted to zero.
- Reference failures are site-health signals. AI trials still run unless the manifest explicitly enables reference-failure skipping; any skipped cells are not AI successes or failures.
- Experimental tasks are mandatory members of this run, but their current assertions do not independently verify every requested semantic detail.
- Action counts are omitted from the comparison because framework-native actions are not equivalent across runners.
- Public websites, provider limits and framework startup can affect outcomes and end-to-end duration. Repetitions reduce, but do not remove, those confounds.

## Evidence manifest

Run manifest: `run-manifest.json`

| Trial | Task | Runner | Outcome | Evidence | SHA-256 |
|---|---|---|---|---|---|
| `browser_use-r1-078b7abc5a95` | `selenium-key-events-en` | browser-use | passed | `browser_use-r1-078b7abc5a95.json` | `856f958a79eccdc26c8298996d5c6affd8bbe5abf8e74925ed67ccbd9226735d` |
| `browser_use-r1-1a0bb209e807` | `mdn-reference-en` | browser-use | passed | `browser_use-r1-1a0bb209e807.json` | `b9200081bafa5d2d8a023bf167979d482103cdf493f80700766bb7cd5b63983e` |
| `browser_use-r1-218fe911d4b9` | `amazon-cheapest-coffee-beans-en` | browser-use | failed | `browser_use-r1-218fe911d4b9.json` | `5774e451b834043a6d2971d7da2623df466ec043efb8c88f84c1203611ea0412` |
| `browser_use-r1-27bc1c7cd688` | `wikipedia-search-en` | browser-use | passed | `browser_use-r1-27bc1c7cd688.json` | `159c8245e0be2405453ee461d0d33aef11b5887bf36f932c83169644e936f1de` |
| `browser_use-r1-6b6b3c04420a` | `selenium-web-form-en` | browser-use | passed | `browser_use-r1-6b6b3c04420a.json` | `b47e113c9edfe71e7766df55dd294f082152938bfb0b677632fd3285464639d8` |
| `browser_use-r1-77e01bb01710` | `marca-real-madrid-open-en` | browser-use | passed | `browser_use-r1-77e01bb01710.json` | `099f8b65030688e7007535adbeacf05d958b5967d4baba122d8e118060ab7de4` |
| `browser_use-r1-c6b520d6d3aa` | `selenium-ajax-labels-en` | browser-use | passed | `browser_use-r1-c6b520d6d3aa.json` | `983825ae27fc7c1cc3643755f10dd85b829904e01999a3e6d762b77c0259697b` |
| `browser_use-r2-01c769d3969f` | `marca-real-madrid-open-en` | browser-use | passed | `browser_use-r2-01c769d3969f.json` | `2cbbd84f6fd02dcb606ac8e9bee1c27cb9f0bc1508f42e015e84937d19e9f9ee` |
| `browser_use-r2-2d79f375a024` | `amazon-cheapest-coffee-beans-en` | browser-use | passed | `browser_use-r2-2d79f375a024.json` | `8bc1bd3355d2a7cc42b6a3720791b042da9ed9f4bb936758a669531b65d3834d` |
| `browser_use-r2-48f7f3cc4ea3` | `mdn-reference-en` | browser-use | passed | `browser_use-r2-48f7f3cc4ea3.json` | `3af23b6c3c18a729c14bef2e68a3336660bda7dbb55e2e6e09eb46bbec22ee1c` |
| `browser_use-r2-4ed75b7f3d7f` | `selenium-web-form-en` | browser-use | passed | `browser_use-r2-4ed75b7f3d7f.json` | `020f79d795e04eb57dc34aa25470a2f1b3bea94685b418e28fb7383a95fb26c8` |
| `browser_use-r2-8d3966d5eb99` | `selenium-key-events-en` | browser-use | passed | `browser_use-r2-8d3966d5eb99.json` | `8cce5550c65e86a25a21bb62ff6babf5189343240ad94d47c6a9a53d7bbed61e` |
| `browser_use-r2-b4546959c091` | `wikipedia-search-en` | browser-use | passed | `browser_use-r2-b4546959c091.json` | `f1809ad37d43f027a40872a918145a827e4ee9394e8de5876e067731c3d029ea` |
| `browser_use-r2-ee6d637d4801` | `selenium-ajax-labels-en` | browser-use | passed | `browser_use-r2-ee6d637d4801.json` | `b811035d04537317991da67fbb8574fce632d82c6a3ffe93b2037c97a93bb859` |
| `browser_use-r3-0737b61cc4d8` | `amazon-cheapest-coffee-beans-en` | browser-use | passed | `browser_use-r3-0737b61cc4d8.json` | `b368bf3ab02e9994f351e7766ad64a845947925cfe91c193daff43fc6b5c021d` |
| `browser_use-r3-1bba681fd92b` | `marca-real-madrid-open-en` | browser-use | passed | `browser_use-r3-1bba681fd92b.json` | `a50fd2ed86c2b17c152f73ec93dcc7bf9dfca80fc9dfd19d26267818585f9135` |
| `browser_use-r3-3f4d6d3d5561` | `mdn-reference-en` | browser-use | passed | `browser_use-r3-3f4d6d3d5561.json` | `3f15faa2152ddaf0d2a29d9eba06b5a6cd3f1ea33fd0c38875bbfafcdace619d` |
| `browser_use-r3-46143329cddf` | `selenium-ajax-labels-en` | browser-use | passed | `browser_use-r3-46143329cddf.json` | `bcc42e6b56f6f16f9a0cf0ab032a30fd0d823627242b2dae056eee1f2fa1498f` |
| `browser_use-r3-5032c4e3cb19` | `selenium-web-form-en` | browser-use | passed | `browser_use-r3-5032c4e3cb19.json` | `a8ec336c559e7339235a0a133ef0d239808904433b2499975acfb773cc9b55e8` |
| `browser_use-r3-7c1953389a0c` | `wikipedia-search-en` | browser-use | passed | `browser_use-r3-7c1953389a0c.json` | `3ee98c2d717308f4edef53104cda30dc2e69707239abe625bb14bacfce97951e` |
| `browser_use-r3-ae573b53839a` | `selenium-key-events-en` | browser-use | passed | `browser_use-r3-ae573b53839a.json` | `954486ac8e0ed3076930938f6184279785b0a7b7edd5e63420c3687953fc4cfa` |
| `playwright_mcp-r1-1e5abc64cc91` | `selenium-ajax-labels-en` | Playwright MCP | passed | `playwright_mcp-r1-1e5abc64cc91.json` | `e58060ea625ccdb5602d5adf271d475a2166d4881409bb80b2977db3dbc6f804` |
| `playwright_mcp-r1-560b802c6087` | `selenium-web-form-en` | Playwright MCP | passed | `playwright_mcp-r1-560b802c6087.json` | `c9ca3dff7074f034003b8a4d99d0b4c9170eb336c5200e63c172ce2d347c396f` |
| `playwright_mcp-r1-5bf0fe809661` | `wikipedia-search-en` | Playwright MCP | passed | `playwright_mcp-r1-5bf0fe809661.json` | `cc48d11150e029a1c63dc002fc76970d8e1e75fe8bf1040da37df0c6bce27f07` |
| `playwright_mcp-r1-7e956c44971d` | `marca-real-madrid-open-en` | Playwright MCP | passed | `playwright_mcp-r1-7e956c44971d.json` | `eb37ed8750bb4a2c10bf9ba9c0f9c1e291402f5a7aebde75adb5d1c6c0eee8b4` |
| `playwright_mcp-r1-b07cbe41bbe0` | `mdn-reference-en` | Playwright MCP | passed | `playwright_mcp-r1-b07cbe41bbe0.json` | `06f800d3153bd2231da9c21aed14726b8767934ee96eb8daebdd31bec723dc94` |
| `playwright_mcp-r1-c9dfc7262609` | `amazon-cheapest-coffee-beans-en` | Playwright MCP | failed | `playwright_mcp-r1-c9dfc7262609.json` | `18f2c9ba8ccbf43ee692777b9570907d0f25bcff4770730ec775b2d2cc0aadcd` |
| `playwright_mcp-r1-fbb108617c62` | `selenium-key-events-en` | Playwright MCP | passed | `playwright_mcp-r1-fbb108617c62.json` | `fe4a7244e6312313e34732fb91cf1c3382af46661adbefca6db1f3d303142052` |
| `playwright_mcp-r2-22a7494352e4` | `mdn-reference-en` | Playwright MCP | passed | `playwright_mcp-r2-22a7494352e4.json` | `2c84ca1a4bf42c083afe2f0c4af688d484e31be1521a9b191edcec78b24cf6eb` |
| `playwright_mcp-r2-2bc6a5acfe48` | `selenium-ajax-labels-en` | Playwright MCP | passed | `playwright_mcp-r2-2bc6a5acfe48.json` | `4c33b6b28cc4836b07d21e3f6378cb035a0d8cbf29b5eba93c8b946b65628344` |
| `playwright_mcp-r2-4c65870bacb3` | `selenium-key-events-en` | Playwright MCP | passed | `playwright_mcp-r2-4c65870bacb3.json` | `ec235b91bf21ec3102c995f3896bb676c981aed22e496222360e44a73e9c9ea6` |
| `playwright_mcp-r2-5a1c54aed9f3` | `marca-real-madrid-open-en` | Playwright MCP | passed | `playwright_mcp-r2-5a1c54aed9f3.json` | `6f1582fce418e9e59db37f23c441a4d4ddf211fa7f0920db4926e52cd6ad6026` |
| `playwright_mcp-r2-9c0666d3f55e` | `wikipedia-search-en` | Playwright MCP | passed | `playwright_mcp-r2-9c0666d3f55e.json` | `6cf42582e4d8f8941f35e99b8e77ce87cb1f09a55c453a4bbe2d31912052d590` |
| `playwright_mcp-r2-b228d45bd97d` | `amazon-cheapest-coffee-beans-en` | Playwright MCP | failed | `playwright_mcp-r2-b228d45bd97d.json` | `bad359258842d9875a1e5d87d132cfc075364309b6a575f017f99a2f323d77a0` |
| `playwright_mcp-r2-c6bd8bcbc4a8` | `selenium-web-form-en` | Playwright MCP | passed | `playwright_mcp-r2-c6bd8bcbc4a8.json` | `df24908ad6f7b45a4bf93be2eb6680229637d332df576d315761cb6e79f5289f` |
| `playwright_mcp-r3-0cb25f5b945c` | `wikipedia-search-en` | Playwright MCP | passed | `playwright_mcp-r3-0cb25f5b945c.json` | `71838d7fdd58197037594029435ecbd3f2f79e2b3b3ee324e339cbb89af7e2c1` |
| `playwright_mcp-r3-1c77636f743e` | `mdn-reference-en` | Playwright MCP | passed | `playwright_mcp-r3-1c77636f743e.json` | `d82e7c3db2389f3e5b3c148199e4f1ad8537acf505c962988874df1febc2010c` |
| `playwright_mcp-r3-8bfd201f42c1` | `selenium-web-form-en` | Playwright MCP | passed | `playwright_mcp-r3-8bfd201f42c1.json` | `2fecb0e484a4daaeee512b8300b7f19be077a4dc42a4845c1f1fb894f767be23` |
| `playwright_mcp-r3-b9b171ee6c45` | `amazon-cheapest-coffee-beans-en` | Playwright MCP | failed | `playwright_mcp-r3-b9b171ee6c45.json` | `b4963a57922b33378775431088c1a200e7bfb831e654dd122fd3a6aa74cadd94` |
| `playwright_mcp-r3-c664a0204409` | `selenium-ajax-labels-en` | Playwright MCP | passed | `playwright_mcp-r3-c664a0204409.json` | `249417d507be3717ac29e530b120e85c751956d22aa7f8b0389cfddb76c94c52` |
| `playwright_mcp-r3-df5fce850a8f` | `marca-real-madrid-open-en` | Playwright MCP | passed | `playwright_mcp-r3-df5fce850a8f.json` | `42fca789e646ef16f548e7d0b2fbb1ded49d2a39cd6ca80a3a68a0a2f818d103` |
| `playwright_mcp-r3-f0ab8aef440b` | `selenium-key-events-en` | Playwright MCP | passed | `playwright_mcp-r3-f0ab8aef440b.json` | `5533c9925107ddef58d5930ffd12eb280cb962c36e3bdb6853b4055cfdac99b5` |
| `reference-01db46de806c` | `selenium-web-form-en` | Deterministic reference | passed | `reference-01db46de806c.json` | `a20d6c9fdf7f69b45a96a4762e4a49b314d3858ed5a046383a15740a3f5440da` |
| `reference-051f9f006d36` | `mdn-reference-en` | Deterministic reference | passed | `reference-051f9f006d36.json` | `f55f4f274b6c50760c8e5b2f2ae25b13b87d67282d8fe5d2b1f89f312c00775a` |
| `reference-0fb317d66dff` | `amazon-cheapest-coffee-beans-en` | Deterministic reference | passed | `reference-0fb317d66dff.json` | `9a910cf1857c3cddfbeda0230ccfb664a12610e937c1509060e67f26381ea3d0` |
| `reference-1a9b43988add` | `marca-real-madrid-open-en` | Deterministic reference | passed | `reference-1a9b43988add.json` | `efbeb8934fa2e657caa16efb0e4114797c1ac1bc35ec2c3dacdf87da842679ce` |
| `reference-39cb37f84838` | `marca-real-madrid-open-en` | Deterministic reference | passed | `reference-39cb37f84838.json` | `4b1b6052d4796fe3b55cd33f05650fc45f4541a219a9f3d5170c9361205ce207` |
| `reference-4268d5d60578` | `selenium-key-events-en` | Deterministic reference | passed | `reference-4268d5d60578.json` | `3489417df74a91af34faab01ef683403b3c8eefb0b58acea6a30edf57111cc5b` |
| `reference-510d3bcf86c5` | `selenium-ajax-labels-en` | Deterministic reference | passed | `reference-510d3bcf86c5.json` | `57c5cd9354d81fc65bb629eeb14c48233d84252b56ac47ac5778ec0430bcc403` |
| `reference-5f0de08f2c57` | `selenium-key-events-en` | Deterministic reference | passed | `reference-5f0de08f2c57.json` | `60fa665f0aaea2fd30ee15e2e819a46c2751bd752cf32fd6c39a2ff43017757a` |
| `reference-65276d4eadf6` | `amazon-cheapest-coffee-beans-en` | Deterministic reference | passed | `reference-65276d4eadf6.json` | `62fd925c39e4bd8443e2e6cd2ecf84643522d553d52467545534ee39767a9b23` |
| `reference-66fcf507efcb` | `wikipedia-search-en` | Deterministic reference | failed | `reference-66fcf507efcb.json` | `ac56fbc969547ee325e2fa146bbadba5efc05bc2d024bcf4c23fcfee3ff766ea` |
| `reference-71b0b5276af5` | `selenium-web-form-en` | Deterministic reference | passed | `reference-71b0b5276af5.json` | `2ba1dc2c0d0a4fdbc9ef167ff4fbedabd46f69c9b3b8b7b33d4f0bdb6c7cc187` |
| `reference-74225dd0c0a7` | `wikipedia-search-en` | Deterministic reference | failed | `reference-74225dd0c0a7.json` | `6a6baea89cab46289a2d48c5499e8d3054249dca55bdc66a947c3c4e2f0bd128` |
| `reference-a209617fd0bb` | `mdn-reference-en` | Deterministic reference | passed | `reference-a209617fd0bb.json` | `e2f40ce37624068fffcc4c99e521f5bd1fc55e63f6512fe31c12ebe23f9f0909` |
| `reference-a93943641eb2` | `selenium-web-form-en` | Deterministic reference | passed | `reference-a93943641eb2.json` | `b81bd02f817ca2746389409cb22500637de06438661c627811151b239b3ced2c` |
| `reference-ad3d50298abd` | `amazon-cheapest-coffee-beans-en` | Deterministic reference | passed | `reference-ad3d50298abd.json` | `011f782ade52a4536eeb37430b0e47830637aa6561457da2ab297e2637df4d24` |
| `reference-ae18a6f29175` | `marca-real-madrid-open-en` | Deterministic reference | passed | `reference-ae18a6f29175.json` | `c42112c9f5ba3e39f8a8f0d04852b65ea2b0d3a191352cbe6503856e45e2121d` |
| `reference-ba0e24e4dae4` | `wikipedia-search-en` | Deterministic reference | failed | `reference-ba0e24e4dae4.json` | `0db681b60f6fd6c06f066ec9489c173faab8c4f812c1d95c62b6fb3e6471db28` |
| `reference-ba90bbf7d5fc` | `selenium-ajax-labels-en` | Deterministic reference | passed | `reference-ba90bbf7d5fc.json` | `a855def8c0cd89fcb0ddaa25d636eec4e18c7ba76b116683ae45d32c1384ee86` |
| `reference-c83c659f58f1` | `selenium-ajax-labels-en` | Deterministic reference | passed | `reference-c83c659f58f1.json` | `484cb2b5c1403366100660dbeacb502d1d8e2e541e2f95e34cea4f1b538bd356` |
| `reference-ce4cc3a83d40` | `mdn-reference-en` | Deterministic reference | passed | `reference-ce4cc3a83d40.json` | `2be7d3a65b04c27e35097ed1fb4c8e0792765ace25f74dad92a2026fb4f2b415` |
| `reference-f062b58e840b` | `selenium-key-events-en` | Deterministic reference | passed | `reference-f062b58e840b.json` | `48c9e91f5353623980a11973a78e33c5770f457901a27d16f8813804c95a2c18` |
| `restricted-r1-7823bc1c1c19` | `selenium-ajax-labels-en` | Restricted agent | passed | `restricted-r1-7823bc1c1c19.json` | `eb71d275ea19e2454bdce75adaf07d4892d2ca385a0d09774d58b202b8ef1a32` |
| `restricted-r1-c29113609c81` | `selenium-web-form-en` | Restricted agent | passed | `restricted-r1-c29113609c81.json` | `6100a1ebab54e02451050bfa30aa84aa9f2fc4798c0d2b23ae33d684f2053f4f` |
| `restricted-r1-cf403bdfb0c4` | `marca-real-madrid-open-en` | Restricted agent | failed | `restricted-r1-cf403bdfb0c4.json` | `3665f36e3066282b6242f37ed23db7475a11c637704523527df1a5b042688639` |
| `restricted-r1-ebc0ac4e3bd6` | `wikipedia-search-en` | Restricted agent | passed | `restricted-r1-ebc0ac4e3bd6.json` | `7685f5bb4e9dd21964eb88b218db4dade9a4a240a87f5f3621d8c82c325224e6` |
| `restricted-r1-f69748782c18` | `selenium-key-events-en` | Restricted agent | passed | `restricted-r1-f69748782c18.json` | `39955ec5af7aeb491c3c50942acfd36aa31483d95a1c676bc446e7201478b5fe` |
| `restricted-r1-f6f042e81e42` | `amazon-cheapest-coffee-beans-en` | Restricted agent | failed | `restricted-r1-f6f042e81e42.json` | `0d5928156eb11c35836231d0145a2aaba8e7f1bf0bcb3242d81fb104c08dfbc3` |
| `restricted-r1-fcf64153bd3e` | `mdn-reference-en` | Restricted agent | passed | `restricted-r1-fcf64153bd3e.json` | `81eaa83c5306f922a9a71d13665970f3f1f20ab4a55ada7c47540f23f71c615b` |
| `restricted-r2-5ec89941bbec` | `mdn-reference-en` | Restricted agent | failed | `restricted-r2-5ec89941bbec.json` | `10bae59858ed21807763617ea38253a4a4998a87d983660d7d2448005f730283` |
| `restricted-r2-64ccf7426205` | `wikipedia-search-en` | Restricted agent | passed | `restricted-r2-64ccf7426205.json` | `925b923794437757a6ff6ecfca50eda81df1d0403a573fe60a59dba9cea6cfd1` |
| `restricted-r2-6b1981af7264` | `selenium-key-events-en` | Restricted agent | passed | `restricted-r2-6b1981af7264.json` | `5f730464e13f4646d04069772e55c69bc44e25c39b62ca693a27313b577b2392` |
| `restricted-r2-8983c3d0cbe0` | `selenium-web-form-en` | Restricted agent | passed | `restricted-r2-8983c3d0cbe0.json` | `6570523843c08fa437b048b85051b95ac2a164df1281680b54401f963144826c` |
| `restricted-r2-8ebd90517bc5` | `selenium-ajax-labels-en` | Restricted agent | passed | `restricted-r2-8ebd90517bc5.json` | `c6b1531a27e068c68608c55465f9d69fefaf735ebbac04227d49d744ca121fb8` |
| `restricted-r2-b2996e5885b4` | `marca-real-madrid-open-en` | Restricted agent | failed | `restricted-r2-b2996e5885b4.json` | `5fd0e0862e61f69485314f0344afbec872dbb379190cb76895b72209e45ed749` |
| `restricted-r2-c6d075db5d51` | `amazon-cheapest-coffee-beans-en` | Restricted agent | failed | `restricted-r2-c6d075db5d51.json` | `976941ac755d04ec4b75ed11ec2f0b925b876bb5143afb403c3f9ef597106b62` |
| `restricted-r3-24fedcb9ee33` | `selenium-web-form-en` | Restricted agent | passed | `restricted-r3-24fedcb9ee33.json` | `eaa8bc8a612b8b1b19a4f50b98f4e99ebcc29eaf7b1c3e5b93b3b6797f97afef` |
| `restricted-r3-2c27a593d47e` | `marca-real-madrid-open-en` | Restricted agent | failed | `restricted-r3-2c27a593d47e.json` | `8685845eaf9ed6b2cba79899863dd172302678576ac48b10e99e43d68aa03d59` |
| `restricted-r3-5bfd1c3d78a6` | `selenium-ajax-labels-en` | Restricted agent | passed | `restricted-r3-5bfd1c3d78a6.json` | `fa2e5ee2ecab06a01c6a6cfd008bf7f93f5e94651a12f710ef5d5082044cd0bb` |
| `restricted-r3-7c109199931a` | `wikipedia-search-en` | Restricted agent | passed | `restricted-r3-7c109199931a.json` | `18228f709aefc2dfd98ef90d54110496b7c8324673d6c6d7ea83f3b8ff676b83` |
| `restricted-r3-8a2af8bcdaed` | `mdn-reference-en` | Restricted agent | passed | `restricted-r3-8a2af8bcdaed.json` | `edf81ede96ff11b920278962502ddb09441d93fc2236e373f04b7611e4939946` |
| `restricted-r3-94a32137ab31` | `amazon-cheapest-coffee-beans-en` | Restricted agent | failed | `restricted-r3-94a32137ab31.json` | `b65145122a3ed2d5809d2d0492e4c4cff6802b692debb6d17a28f54ce3510a7a` |
| `restricted-r3-f9549d324e01` | `selenium-key-events-en` | Restricted agent | passed | `restricted-r3-f9549d324e01.json` | `4b7512c54ea6c6fb27108f122ebc7a20efadf622649fc208b909e9342c6dd36f` |
