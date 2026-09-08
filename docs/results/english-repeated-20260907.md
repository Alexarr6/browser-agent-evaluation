# Repeated browser-agent evaluation

This report covers one unified matrix of **7 tasks** (5 standard and 2 experimental), 3 repetitions and 4 runners. Every task is mandatory in the execution matrix. Tasks with reachability-only checks are reported as unverified and never counted as completed.

> `passed` is reserved for task-completion contracts. A successful reachability-only check is `unverified`, never a completed task.

> Open-task deterministic references are control checks, not solution claims. They validate current site and verifier feasibility but are excluded from solution denominators.

## Run configuration

| Property | Value |
|---|---|
| Created | 2026-09-07T18:12:17.189522+00:00 |
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

| Task | Category | Verification | Assertions | Timeout | Action cap | Contract |
|---|---|---|---|---:|---:|---|
| Wikipedia (English) | standard | `task_completion` | `page_title`, `url_contains` | 300s | 48 | `wikipedia-search-en.yaml` (`b5d3dc86c771`) |
| MDN (English) | standard | `task_completion` | `url_contains`, `visible_text` | 300s | 48 | `mdn-reference-en.yaml` (`0daa9c91104e`) |
| Selenium web form (English) | standard | `task_completion` | `url_contains`, `visible_text` | 300s | 48 | `selenium-web-form-en.yaml` (`1dfd38d6dee9`) |
| Selenium AJAX labels (English) | standard | `task_completion` | `visible_text` | 300s | 48 | `selenium-ajax-labels-en.yaml` (`0da47f7d5925`) |
| Selenium key events (English) | standard | `task_completion` | `visible_text` | 300s | 48 | `selenium-key-events-en.yaml` (`8b691a3afd73`) |
| Marca Real Madrid (English) | experimental | `task_completion` | `verifier` | 300s | 48 | `marca-real-madrid-open-en.yaml` (`2dce04a429a5`) |
| Amazon coffee beans below 14 EUR/kg (English) | experimental | `task_completion` | `verifier` | 300s | 48 | `amazon-cheapest-coffee-beans-en.yaml` (`39824fe44552`) |

## Per-task results

`Verified success` is available only for task-completion contracts. Open-task deterministic references are shown as `N/A (control x/y)` because their site-specific recipes are controls, not general solutions. `Unverified` means that a reachability probe succeeded without proving the task instruction. `Invalid` identifies trials without comparable cleanup evidence. `Ref-skipped` records planned AI trials that were not started because the deterministic reference failed.

| Task | Category | Runner | Verified success | Unverified | Invalid | Ref-skipped | Median accepted time | Requests | Tokens | Cost (USD) |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Wikipedia (English) | standard | Deterministic reference | 2/3 | 0 | 0 | 0 | 1.206s | 0 | — | — |
| Wikipedia (English) | standard | Restricted agent | 3/3 | 0 | 0 | 0 | 13.715s | 14 | 49,335 | 0.01709408 |
| Wikipedia (English) | standard | browser-use | 3/3 | 0 | 0 | 0 | 15.573s | 12 | 108,930 | unavailable (3 trials) |
| Wikipedia (English) | standard | Playwright MCP | 3/3 | 0 | 0 | 0 | 8.036s | 9 | 53,138 | 0.01099096 |
| MDN (English) | standard | Deterministic reference | 3/3 | 0 | 0 | 0 | 0.854s | 0 | — | — |
| MDN (English) | standard | Restricted agent | 1/3 | 0 | 0 | 0 | 30.814s | 13 | 42,867 | 0.01689860 |
| MDN (English) | standard | browser-use | 3/3 | 0 | 0 | 0 | 18.614s | 15 | 144,122 | unavailable (3 trials) |
| MDN (English) | standard | Playwright MCP | 3/3 | 0 | 0 | 0 | 12.328s | 15 | 166,920 | 0.02834496 |
| Selenium web form (English) | standard | Deterministic reference | 3/3 | 0 | 0 | 0 | 31.067s | 0 | — | — |
| Selenium web form (English) | standard | Restricted agent | 2/3 | 0 | 0 | 0 | 21.764s | 22 | 37,124 | 0.01355132 |
| Selenium web form (English) | standard | browser-use | 3/3 | 0 | 0 | 0 | 27.155s | 25 | 210,368 | unavailable (3 trials) |
| Selenium web form (English) | standard | Playwright MCP | 3/3 | 0 | 0 | 0 | 13.674s | 24 | 103,366 | 0.01171484 |
| Selenium AJAX labels (English) | standard | Deterministic reference | 3/3 | 0 | 0 | 0 | 12.618s | 0 | — | — |
| Selenium AJAX labels (English) | standard | Restricted agent | 3/3 | 0 | 0 | 0 | 30.587s | 21 | 28,111 | 0.00996448 |
| Selenium AJAX labels (English) | standard | browser-use | 3/3 | 0 | 0 | 0 | 30.871s | 25 | 198,864 | unavailable (3 trials) |
| Selenium AJAX labels (English) | standard | Playwright MCP | 3/3 | 0 | 0 | 0 | 17.628s | 21 | 41,998 | 0.00464244 |
| Selenium key events (English) | standard | Deterministic reference | 3/3 | 0 | 0 | 0 | 0.595s | 0 | — | — |
| Selenium key events (English) | standard | Restricted agent | 3/3 | 0 | 0 | 0 | 21.185s | 24 | 31,920 | 0.01167656 |
| Selenium key events (English) | standard | browser-use | 3/3 | 0 | 0 | 0 | 20.276s | 24 | 188,921 | unavailable (3 trials) |
| Selenium key events (English) | standard | Playwright MCP | 3/3 | 0 | 0 | 0 | 12.005s | 24 | 42,418 | 0.00467148 |
| Marca Real Madrid (English) | experimental | Deterministic reference | N/A (control 3/3) | 0 | 0 | 0 | 2.325s | 0 | — | — |
| Marca Real Madrid (English) | experimental | Restricted agent | 3/3 | 0 | 0 | 0 | 9.365s | 7 | 25,765 | 0.01220160 |
| Marca Real Madrid (English) | experimental | browser-use | 3/3 | 0 | 0 | 0 | 25.264s | 13 | 134,456 | unavailable (3 trials) |
| Marca Real Madrid (English) | experimental | Playwright MCP | 3/3 | 0 | 0 | 0 | 69.314s | 9 | 121,094 | 0.02675364 |
| Amazon coffee beans below 14 EUR/kg (English) | experimental | Deterministic reference | N/A (control 3/3) | 0 | 0 | 0 | 8.575s | 0 | — | — |
| Amazon coffee beans below 14 EUR/kg (English) | experimental | Restricted agent | 2/3 | 0 | 0 | 0 | 17.791s | 14 | 48,203 | 0.02029032 |
| Amazon coffee beans below 14 EUR/kg (English) | experimental | browser-use | 3/3 | 0 | 0 | 0 | 33.749s | 22 | 251,891 | unavailable (3 trials) |
| Amazon coffee beans below 14 EUR/kg (English) | experimental | Playwright MCP | 0/3 | 0 | 0 | 0 | — | 31 | 1,094,571 | 0.10930504 |

## Runner aggregate

Verified-success denominators contain only task-completion contracts. The deterministic reference denominator excludes verifier-backed open tasks because those recipes are controls rather than general solutions. Consumption totals contain every attempted task, including reachability-only tasks and failures.

| Runner | Verified success | Unverified | Invalid | Ref-skipped | Median verified time | Requests | Tokens | Cost (USD) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Deterministic reference | 14/15 | 0 | 0 | 0 | 1.341s | 0 | — | — |
| Restricted agent | 17/21 | 0 | 0 | 0 | 21.185s | 115 | 263,325 | 0.10167696 |
| browser-use | 21/21 | 0 | 0 | 0 | 25.264s | 136 | 1,237,552 | unavailable (21 trials) |
| Playwright MCP | 18/21 | 0 | 0 | 0 | 13.159s | 133 | 1,623,505 | 0.19642336 |

## Aggregate observations

- Highest observed AI success rate: browser-use (21/21).
- Lowest median duration among successful AI trials: Playwright MCP (13.159s). This is not a like-for-like speed ranking when runners fail different task mixes.
- Lowest reported AI token consumption: Restricted agent (263,325 tokens across all its attempts).
- A complete cost ranking is unavailable because cost was not reported for browser-use.
- Deterministic-reference failures require separate inspection and are potential site or harness confounds: Wikipedia (English) (1/3).
- Observed Restricted agent failures: MDN (English) (2/3), Selenium web form (English) (1/3), Amazon coffee beans below 14 EUR/kg (English) (1/3).
- Observed Playwright MCP failures: Amazon coffee beans below 14 EUR/kg (English) (3/3).

## Limits and interpretation warnings

- Cost limit: USD 2.00 per round; per-trial limit: USD 0.25.
- Per-trial limits: 48 model requests and 1,000,000 cumulative tokens. Task-specific time and action limits appear above.
- Failed and invalidated attempts remain in request, token and known-cost totals. Missing tokens or cost are labelled unavailable rather than converted to zero.
- Verifier-backed open-task references are site and verifier controls. Their site-specific recipes are excluded from solution claims and method rankings.
- Reference failures are site-health signals. AI trials still run unless the manifest explicitly enables reference-failure skipping; any skipped cells are not AI successes or failures.
- Reachability-only tasks are mandatory members of this run, but successful probes are unverified and excluded from task-completion success rates.
- Action counts are omitted from the comparison because framework-native actions are not equivalent across runners.
- Public websites, provider limits and framework startup can affect outcomes and end-to-end duration. Repetitions reduce, but do not remove, those confounds.

## Evidence manifest

Run manifest: `run-manifest.json`

| Trial | Task | Runner | Outcome | Evidence | SHA-256 |
|---|---|---|---|---|---|
| `browser_use-r1-00969d0b7458` | `selenium-ajax-labels-en` | browser-use | passed | `browser_use-r1-00969d0b7458.json` | `b20493dfdabe48d38caf03e4aa42084e515a9f6e11e1973821cbd476faca1323` |
| `browser_use-r1-51a27867e571` | `wikipedia-search-en` | browser-use | passed | `browser_use-r1-51a27867e571.json` | `24624e760793e0a5a8598282323a65ca1510accae0bf6ae610824e59fee8fb9a` |
| `browser_use-r1-55fe7a613efc` | `mdn-reference-en` | browser-use | passed | `browser_use-r1-55fe7a613efc.json` | `4fc8f023c14b442bf82ddea825a8863ae3b9e287a3c9128b6008ce7e684ee135` |
| `browser_use-r1-72edda569370` | `selenium-web-form-en` | browser-use | passed | `browser_use-r1-72edda569370.json` | `5d12bae9fe81e6bcbdffb587571d9e6455b87d7962b4d70767253d44d066435b` |
| `browser_use-r1-d4052fdb8762` | `amazon-cheapest-coffee-beans-en` | browser-use | passed | `browser_use-r1-d4052fdb8762.json` | `c93a90842dc9351fd8f33ce0e8b890308928005714c5de6528bef2185c1d5ab7` |
| `browser_use-r1-d6a2feecee51` | `marca-real-madrid-open-en` | browser-use | passed | `browser_use-r1-d6a2feecee51.json` | `494fc6ec8110f7780e1c056239936701de9bc7140f96af1cca6a3935b887d183` |
| `browser_use-r1-df67abea76df` | `selenium-key-events-en` | browser-use | passed | `browser_use-r1-df67abea76df.json` | `10296a44336615e9a388f7a35c82b05050f811be7d8db78a2f1f6bdf4e1781ee` |
| `browser_use-r2-025c82193718` | `marca-real-madrid-open-en` | browser-use | passed | `browser_use-r2-025c82193718.json` | `7afa3e981350d97fb3671490e77bf819968d708f2114ce41391d2e933c8491eb` |
| `browser_use-r2-6bb489b1d1a7` | `wikipedia-search-en` | browser-use | passed | `browser_use-r2-6bb489b1d1a7.json` | `211677dac0b4c88dd844837e1b0ac2ec5bc085fec506a3fd9a3b72c31fe0c2eb` |
| `browser_use-r2-785b1084a369` | `mdn-reference-en` | browser-use | passed | `browser_use-r2-785b1084a369.json` | `2007ef6f6b66d747337de97b1056edd4c2d7808dee6245dc565224afa4395e3f` |
| `browser_use-r2-7a743937d710` | `selenium-web-form-en` | browser-use | passed | `browser_use-r2-7a743937d710.json` | `bd24274efd0b39e1ebeaa48f00836c9ffdaf5085a7a72e58591f7aa99e904338` |
| `browser_use-r2-ae7b562d4795` | `selenium-key-events-en` | browser-use | passed | `browser_use-r2-ae7b562d4795.json` | `ca2dcc28f7a8d766ad19845403f67aa439f6943642ef9c196b6a10554f940ac0` |
| `browser_use-r2-afde9b04a199` | `amazon-cheapest-coffee-beans-en` | browser-use | passed | `browser_use-r2-afde9b04a199.json` | `2e91203ddb6ea444807805c9e97ff2292d681679c08b5acac818086cc4bb242b` |
| `browser_use-r2-b43eb7d194d2` | `selenium-ajax-labels-en` | browser-use | passed | `browser_use-r2-b43eb7d194d2.json` | `eeed2b150038ddc97d169246b73123c263db9276ede0de470508d768ed1391e9` |
| `browser_use-r3-11279448f82d` | `selenium-web-form-en` | browser-use | passed | `browser_use-r3-11279448f82d.json` | `bba42e634224a79377658d03a36d0428a285f35590db21631c15bfcd8a52ba98` |
| `browser_use-r3-14f4a20502ff` | `mdn-reference-en` | browser-use | passed | `browser_use-r3-14f4a20502ff.json` | `f5af537cfa6828d808911a55751cc7a454a0866970d1edb63b0bb8560e6c1c48` |
| `browser_use-r3-67df0dd90b53` | `selenium-key-events-en` | browser-use | passed | `browser_use-r3-67df0dd90b53.json` | `712d0abe808e64e72d5d9aa26d6fd62c4f2ad4a7118ab606d9315ce6dc83497a` |
| `browser_use-r3-7efd079f49f0` | `selenium-ajax-labels-en` | browser-use | passed | `browser_use-r3-7efd079f49f0.json` | `39619393d5db8a43e48d41d377f831caba722f1018e4f2d656d7a230547edb4e` |
| `browser_use-r3-8269101a3caa` | `wikipedia-search-en` | browser-use | passed | `browser_use-r3-8269101a3caa.json` | `af4450b9f86029b577e57260f90bb32a6b6574f5f719ad66376568b8ea0f6783` |
| `browser_use-r3-ade629d2f3ac` | `marca-real-madrid-open-en` | browser-use | passed | `browser_use-r3-ade629d2f3ac.json` | `68a5f0a3bddb56bd12bb646ddc143749038937b6cb587c8eef01f164c80e4515` |
| `browser_use-r3-d1c5d8378e35` | `amazon-cheapest-coffee-beans-en` | browser-use | passed | `browser_use-r3-d1c5d8378e35.json` | `323e3234571bbf5b09793558085a8593e38a34da90e27f2db76b0d4ef2f74ebf` |
| `playwright_mcp-r1-3abfdb43af1e` | `amazon-cheapest-coffee-beans-en` | Playwright MCP | failed | `playwright_mcp-r1-3abfdb43af1e.json` | `d04ab427ee8eb1e7d6ee6a54bf7c7b295411d515797821fd74aa317812d55b53` |
| `playwright_mcp-r1-65b05d98c23e` | `mdn-reference-en` | Playwright MCP | passed | `playwright_mcp-r1-65b05d98c23e.json` | `72854cd00989ef3072b292680c81733ca0b1ef1fe46b8df9615083f9f2778618` |
| `playwright_mcp-r1-9e827804d5dd` | `marca-real-madrid-open-en` | Playwright MCP | passed | `playwright_mcp-r1-9e827804d5dd.json` | `a519739bf1660c0f5d6709ff31da6ca532c459dcfdb5b23355bce6157b4aab94` |
| `playwright_mcp-r1-a86e2ce27dd2` | `selenium-web-form-en` | Playwright MCP | passed | `playwright_mcp-r1-a86e2ce27dd2.json` | `7b3e1592ece1736240b9e4d7495910c89149c84e8a54d9234c23900cc7b539ce` |
| `playwright_mcp-r1-bc9aca0fb33f` | `selenium-ajax-labels-en` | Playwright MCP | passed | `playwright_mcp-r1-bc9aca0fb33f.json` | `8558154d1df4c1b5cc707ed63c2ecd505ad389a6ec079dc6009d1d54df48e7ce` |
| `playwright_mcp-r1-e0d03c204385` | `wikipedia-search-en` | Playwright MCP | passed | `playwright_mcp-r1-e0d03c204385.json` | `d5e98fd9ec70568158d882f334f1d15c85806a9ac46626c06f95781d04f3e7d4` |
| `playwright_mcp-r1-e6f82f305045` | `selenium-key-events-en` | Playwright MCP | passed | `playwright_mcp-r1-e6f82f305045.json` | `44c409ee1383fcb834c8d58d087178cdb53f9dec58da33c379666779a9df4b0f` |
| `playwright_mcp-r2-39c53e6c679f` | `selenium-ajax-labels-en` | Playwright MCP | passed | `playwright_mcp-r2-39c53e6c679f.json` | `53f9d21bff786304a410cb19bc68c9a2c00acf067eb2d38bace7ec846cfc0967` |
| `playwright_mcp-r2-496537ec71ca` | `amazon-cheapest-coffee-beans-en` | Playwright MCP | failed | `playwright_mcp-r2-496537ec71ca.json` | `c659117c126402d214c374f3a242278e0006179d21e96e8f276c62b6fc4dcbda` |
| `playwright_mcp-r2-5f2c6cd4e26d` | `marca-real-madrid-open-en` | Playwright MCP | passed | `playwright_mcp-r2-5f2c6cd4e26d.json` | `588be579702572ef32f4b42ec56f47aebae54ec0dfba41df5c41529bd4425e3d` |
| `playwright_mcp-r2-ba4b089efdcd` | `selenium-web-form-en` | Playwright MCP | passed | `playwright_mcp-r2-ba4b089efdcd.json` | `969aa19477219026ad6fc5a0be04f5f6ab5d075e15910542e467ff16cc1c96eb` |
| `playwright_mcp-r2-dddcb40266d8` | `wikipedia-search-en` | Playwright MCP | passed | `playwright_mcp-r2-dddcb40266d8.json` | `7530ecab138c9ab738977b315f92d8f987128df2f7bb4baa3207974d28589c16` |
| `playwright_mcp-r2-f7fe63340098` | `selenium-key-events-en` | Playwright MCP | passed | `playwright_mcp-r2-f7fe63340098.json` | `05d724504e47a0fc5d300c8d8db08caf9df282da4979d501b5a49c88c3cd4717` |
| `playwright_mcp-r2-fa9bc1d229d1` | `mdn-reference-en` | Playwright MCP | passed | `playwright_mcp-r2-fa9bc1d229d1.json` | `fc802aa40609e048bae5bc229dbba1073aa5f49f6af33d656c84028f262df454` |
| `playwright_mcp-r3-014f55bf975d` | `mdn-reference-en` | Playwright MCP | passed | `playwright_mcp-r3-014f55bf975d.json` | `65f696708b4641fb425d63f132cefb158e48f6e6b90dfca06adcb04cb84892b2` |
| `playwright_mcp-r3-0c204a599d37` | `selenium-key-events-en` | Playwright MCP | passed | `playwright_mcp-r3-0c204a599d37.json` | `6445eedab3686ec5e2650b794a744b13591437a02fa3fba80b4aa8b61f10d0df` |
| `playwright_mcp-r3-0dd8221b023c` | `wikipedia-search-en` | Playwright MCP | passed | `playwright_mcp-r3-0dd8221b023c.json` | `e01bb26dcf2fd8c8e8eb1471ed3d59f44841815be414bcaf1834440053353949` |
| `playwright_mcp-r3-159b037d8097` | `amazon-cheapest-coffee-beans-en` | Playwright MCP | failed | `playwright_mcp-r3-159b037d8097.json` | `4ab1810bfc9b6d8326c613127511c4eaa3777304ea1ec32e0711d19e4042640c` |
| `playwright_mcp-r3-3c44e387c978` | `selenium-web-form-en` | Playwright MCP | passed | `playwright_mcp-r3-3c44e387c978.json` | `1af6604d729a52437983a47c3a7e8e1332238aafbd504361ae6408b1c4c114e2` |
| `playwright_mcp-r3-67442044fafc` | `selenium-ajax-labels-en` | Playwright MCP | passed | `playwright_mcp-r3-67442044fafc.json` | `11e1b399b3f18f85c037a8c5a261facd747d5aa69ff7a0d8e69be5a475fce0e7` |
| `playwright_mcp-r3-975e686f0475` | `marca-real-madrid-open-en` | Playwright MCP | passed | `playwright_mcp-r3-975e686f0475.json` | `54240fc562126bf42106099ead31c9a0213cffac05610aa3d612d339fa4fd661` |
| `reference-0183708a2583` | `wikipedia-search-en` | Deterministic reference | passed | `reference-0183708a2583.json` | `5ab93a42aaabfefcd36f6eb666ac7080c7134be8ef30db2c31a0f75a4ca12823` |
| `reference-07a8befc5b76` | `mdn-reference-en` | Deterministic reference | passed | `reference-07a8befc5b76.json` | `e51dc80d56e22bbea6a947ed798c1ddbdff10e81afc5af28c0cebcf69c96fb1c` |
| `reference-0b7564b08675` | `selenium-key-events-en` | Deterministic reference | passed | `reference-0b7564b08675.json` | `1ad3aa0079f356005d8d381bbc4021640825871ebc2689b216335d00ccd6282a` |
| `reference-412d22efa18a` | `selenium-key-events-en` | Deterministic reference | passed | `reference-412d22efa18a.json` | `9f4bffaeb51eb2215ecb5491f3c4ef91ad6f6dfa81170de2b4d829ff91113ffe` |
| `reference-49e618530762` | `selenium-web-form-en` | Deterministic reference | passed | `reference-49e618530762.json` | `2adbe1feea541d083a770ad56023007767fbbd4b9956e2319150c4e535cb7540` |
| `reference-6dc15cc89ca9` | `wikipedia-search-en` | Deterministic reference | failed | `reference-6dc15cc89ca9.json` | `2cf00b98dca6761fd6e78c18d34c378e2a145feb146ffab3480e9581251e3ad4` |
| `reference-73c3dd14f4cc` | `selenium-ajax-labels-en` | Deterministic reference | passed | `reference-73c3dd14f4cc.json` | `e612592ec860f36172b633754ee0af1f79be79968bfb585ce0d860fb5e0765dc` |
| `reference-751182b9f6bb` | `mdn-reference-en` | Deterministic reference | passed | `reference-751182b9f6bb.json` | `cca9e61eeee52ea9890c687a524c3f750fa12a2ac08ef62e2a3d42f79a2b09d0` |
| `reference-7fac332c73e6` | `wikipedia-search-en` | Deterministic reference | passed | `reference-7fac332c73e6.json` | `472c69b7d5b8c39644c7675452998fa3f069966780d939ea630f97c1248cfa45` |
| `reference-801b005f7031` | `amazon-cheapest-coffee-beans-en` | Deterministic reference | passed | `reference-801b005f7031.json` | `70a5cd860f508683b057b5abaf0e65aa65b8fad2bbd7cdd7fc3aafa06805ed97` |
| `reference-869890725b74` | `amazon-cheapest-coffee-beans-en` | Deterministic reference | passed | `reference-869890725b74.json` | `ba50139a77b4f986c5aa76263b3d3e0a5fc7e5206e7030f7a1c584affece09c5` |
| `reference-87fafab3f725` | `marca-real-madrid-open-en` | Deterministic reference | passed | `reference-87fafab3f725.json` | `652e06405295035a2a0f7cfab939d9aba8d47fdd7fc4251b3192da58070e6b2c` |
| `reference-972e2d9a4788` | `selenium-web-form-en` | Deterministic reference | passed | `reference-972e2d9a4788.json` | `10c38f1fe0fd5d6f06bff6b227d26d61bf3eb7ba3ff16307bc69db7641ae28b9` |
| `reference-a282aa519b0e` | `selenium-ajax-labels-en` | Deterministic reference | passed | `reference-a282aa519b0e.json` | `ff71939c697f1f84baac091057a87a166ec2de2e8f03aee7fd6c779fe1d38f73` |
| `reference-a7ab9aab6193` | `selenium-key-events-en` | Deterministic reference | passed | `reference-a7ab9aab6193.json` | `02b2e13c98b3d5c6228bc672af6f83d969831ab9ec2761e50b2c8e5668e4396b` |
| `reference-ab32ee136b7d` | `selenium-ajax-labels-en` | Deterministic reference | passed | `reference-ab32ee136b7d.json` | `a77dad340d7c88f669805b3f27cc481421d97d64604b135245c9c7291787f810` |
| `reference-adaa75baf18c` | `marca-real-madrid-open-en` | Deterministic reference | passed | `reference-adaa75baf18c.json` | `099e49172679ef1580fd4fe0aa8c1b6ffe5d67bedde039a069f3f46ab78973e1` |
| `reference-c34f81aef5c4` | `mdn-reference-en` | Deterministic reference | passed | `reference-c34f81aef5c4.json` | `ab9bde7899e33c3ebae186030cfd6f347371454c690cf928919de07176750b18` |
| `reference-c5e2e1792bcc` | `selenium-web-form-en` | Deterministic reference | passed | `reference-c5e2e1792bcc.json` | `6f610cc4ce92550fada2ed659f32d0538d6e4e70b9bd19a623635097108bda33` |
| `reference-e896d5145974` | `marca-real-madrid-open-en` | Deterministic reference | passed | `reference-e896d5145974.json` | `2a273141bd5a15cb8dd436eacdaf3bc8feaa8c3dcd47270edf25f36480f0092f` |
| `reference-eae6ae440cff` | `amazon-cheapest-coffee-beans-en` | Deterministic reference | passed | `reference-eae6ae440cff.json` | `07df043acf22532287995a0c99400267450ab9f7f05e38248c971697d750c44c` |
| `restricted-r1-1ca0527c5f11` | `selenium-key-events-en` | Restricted agent | passed | `restricted-r1-1ca0527c5f11.json` | `9a16608d3a303448ec46b2c8e25d6ac50b5380ef5bb9d9acf26790d15e138e13` |
| `restricted-r1-48b5c60916c9` | `mdn-reference-en` | Restricted agent | passed | `restricted-r1-48b5c60916c9.json` | `e8868e936c2cee54d468763cab2767ef38f145804eab5b8db2770c5766b5f4df` |
| `restricted-r1-72e8c321d047` | `selenium-ajax-labels-en` | Restricted agent | passed | `restricted-r1-72e8c321d047.json` | `bfa05ec5e92df4dfa000e5f231feff72877d31b5a03bd9e2092d34c75f66c185` |
| `restricted-r1-79835ac6dd8c` | `amazon-cheapest-coffee-beans-en` | Restricted agent | failed | `restricted-r1-79835ac6dd8c.json` | `c242105ac62c91bdfeac27d1721566b5a31fd1db7d0712782caa17303cac174d` |
| `restricted-r1-956a413cff8a` | `marca-real-madrid-open-en` | Restricted agent | passed | `restricted-r1-956a413cff8a.json` | `f2be35821d74133c203f70befeb3cb580ebda6e71eb1da8317d1b0f03e4e320f` |
| `restricted-r1-95d06bb39c35` | `wikipedia-search-en` | Restricted agent | passed | `restricted-r1-95d06bb39c35.json` | `0ff0c775605620bac0164d9a712759dcca974c7019955d7891219678d47d51a9` |
| `restricted-r1-aef5f3b3a382` | `selenium-web-form-en` | Restricted agent | failed | `restricted-r1-aef5f3b3a382.json` | `cff6d4935dff35ecd4d95eb20a49922e096869688dc0c43b5888e261dc938116` |
| `restricted-r2-07b25c2ea73a` | `amazon-cheapest-coffee-beans-en` | Restricted agent | passed | `restricted-r2-07b25c2ea73a.json` | `6418d43cb3220941fbf310d434420bf7e56d1d3b2008559228f1ed3c7fbc7f6f` |
| `restricted-r2-662d67c509cd` | `mdn-reference-en` | Restricted agent | failed | `restricted-r2-662d67c509cd.json` | `0fb2b6a92a7ed987e67bf46ffd984d3944fbc5293d10c67d62e667920747baad` |
| `restricted-r2-914a64406708` | `selenium-ajax-labels-en` | Restricted agent | passed | `restricted-r2-914a64406708.json` | `ab7c1bb078cead35823116b79db0bad16f201147c86122c06e31d916996e40d1` |
| `restricted-r2-9aaefa67a5b2` | `selenium-key-events-en` | Restricted agent | passed | `restricted-r2-9aaefa67a5b2.json` | `f8ac1e3b3536404401dcf1b67c79107d248d55ace1954574156991333fea1810` |
| `restricted-r2-9db2895a3186` | `wikipedia-search-en` | Restricted agent | passed | `restricted-r2-9db2895a3186.json` | `c9c17582f6357273fabb5aacf1f572ebe71ddd69262f2c7a25dff8fb0db61c5e` |
| `restricted-r2-c42d82750018` | `selenium-web-form-en` | Restricted agent | passed | `restricted-r2-c42d82750018.json` | `beeb1c3136a7a36f798f5f1f54c6e53923436b91f0ef8454e5a964fd9eafc3e5` |
| `restricted-r2-dd1e201934bf` | `marca-real-madrid-open-en` | Restricted agent | passed | `restricted-r2-dd1e201934bf.json` | `5b5bcde1c833802c40844003b98f0e7d2476d11d6770a7e197cabc7053318d60` |
| `restricted-r3-2aa119f3eade` | `marca-real-madrid-open-en` | Restricted agent | passed | `restricted-r3-2aa119f3eade.json` | `dc03f3c0c18f91a18b1411f19ee29af59e4f41719e2d3522125219505cfbbe86` |
| `restricted-r3-624a02133ae2` | `amazon-cheapest-coffee-beans-en` | Restricted agent | passed | `restricted-r3-624a02133ae2.json` | `7039058b1618832f57941a07b43171fc43a8a7409f38a498dee35f38c0ca759e` |
| `restricted-r3-7c881de0408c` | `mdn-reference-en` | Restricted agent | failed | `restricted-r3-7c881de0408c.json` | `8f153cde6463f4fe5059bcbe27431b7460e7fc4637c519e46a4fe6a26f252707` |
| `restricted-r3-95b53ffa0d2d` | `selenium-web-form-en` | Restricted agent | passed | `restricted-r3-95b53ffa0d2d.json` | `0851ee50a0ce67eb39425747601493910d9581791bb25269284005a1a7c34c43` |
| `restricted-r3-9c455b49bcb5` | `selenium-key-events-en` | Restricted agent | passed | `restricted-r3-9c455b49bcb5.json` | `7e8e546db227cdd4f8a27cc1de2b944150ec97dfba02f78a604fef3ea3a81a9a` |
| `restricted-r3-c6ca1a24a116` | `selenium-ajax-labels-en` | Restricted agent | passed | `restricted-r3-c6ca1a24a116.json` | `58c3e5f70c324ed41af00a6e530c466d7110dd49d62669aa18c01de6af839b3c` |
| `restricted-r3-de6ddab01922` | `wikipedia-search-en` | Restricted agent | passed | `restricted-r3-de6ddab01922.json` | `75970ce48f40f77045560eefeaec89a9977c54f30ea4f1684352a0515ca3773a` |
