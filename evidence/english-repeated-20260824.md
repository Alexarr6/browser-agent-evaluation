# English-only repeated browser-agent evaluation

This report contains three repetitions for each of five English task contracts and four runners. Spanish trials and prior invalidated diagnostics are excluded.

## Per-task success

| Task | Runner | Success | Median passing time (s) | All requests | All tokens | All cost (USD) |
|---|---|---:|---:|---:|---:|---:|
| Wikipedia (English) | Deterministic reference | 3/3 | 1.558 | 0 | — | — |
| Wikipedia (English) | Restricted agent | 1/3 | 10.379 | 6 | 11,383 | 0.00282879 |
| Wikipedia (English) | browser-use | 1/3 | 13.947 | 5 | 48,521 | 0.00802315 |
| Wikipedia (English) | Playwright MCP | 3/3 | 10.367 | 6 | 26,232 | 0.00377560 |
| MDN (English) | Deterministic reference | 3/3 | 1.700 | 0 | — | — |
| MDN (English) | Restricted agent | 0/3 | — | 8 | 12,761 | 0.00338860 |
| MDN (English) | browser-use | 2/3 | 17.217 | 9 | 86,482 | 0.01063862 |
| MDN (English) | Playwright MCP | 3/3 | 12.023 | 9 | 71,011 | 0.01088415 |
| Selenium web form (English) | Deterministic reference | 3/3 | 0.931 | 0 | — | — |
| Selenium web form (English) | Restricted agent | 0/3 | — | 10 | 11,326 | 0.00361605 + 1 reserve |
| Selenium web form (English) | browser-use | 0/3 | — | 5 | 44,122 | 0.00836597 |
| Selenium web form (English) | Playwright MCP | 3/3 | 16.024 | 24 | 91,187 | 0.00658833 |
| Selenium AJAX labels (English) | Deterministic reference | 3/3 | 12.583 | 0 | — | — |
| Selenium AJAX labels (English) | Restricted agent | 2/3 | 36.171 | 15 | 16,344 | 0.00528180 |
| Selenium AJAX labels (English) | browser-use | 0/3 | — | 4 | 36,138 | 0.00816752 |
| Selenium AJAX labels (English) | Playwright MCP | 2/3 | 33.451 | 14 | 20,983 | 0.00274718 |
| Selenium key events (English) | Deterministic reference | 3/3 | 0.632 | 0 | — | — |
| Selenium key events (English) | Restricted agent | 3/3 | 29.270 | 24 | 26,792 | 0.00871300 |
| Selenium key events (English) | browser-use | 0/3 | — | 16 | 127,389 | 0.01053263 |
| Selenium key events (English) | Playwright MCP | 3/3 | 13.080 | 24 | 30,424 | 0.00362493 |

## Runner aggregate

| Runner | Success | Median passing time (s) | All requests | All tokens | All cost (USD) |
|---|---:|---:|---:|---:|---:|
| Deterministic reference | 15/15 | 1.558 | 0 | — | — |
| Restricted agent | 6/15 | 30.568 | 63 | 78,606 | 0.02382824 + 1 reserve |
| browser-use | 3/15 | 16.571 | 39 | 342,652 | 0.04572789 |
| Playwright MCP | 14/15 | 12.816 | 77 | 239,837 | 0.02762019 |

## Limits

- This is an English-only, n=3-per-cell exploratory sample; it is not pooled with Spanish tasks and does not establish general reliability.
- Every AI trial used a 600-second task timeout, 48 action cap, 24 request cap, 50,000 cumulative-token cap and USD 0.07 trial cap.
- browser-use uses its disclosed isolated Chromium 140 line; the other arms use Chromium 151.
- Failed trials remain in success, token, request and known-cost totals. Each response without provider cost is explicitly reserved at the USD 0.07 trial cap.
- Known English-only provider spend: USD 0.09717632; 1 unavailable-cost trial(s) reserve USD 0.07.

## Evidence manifest

| Trial | Evidence | SHA-256 |
|---|---|---|
| browser_use-r1-0db3fe2349cf | `browser_use-r1-0db3fe2349cf.json` | `04754465bc2b13229a80387a06496880e8d0e5a14a1ee91a4608e946cf0ab0ed` |
| browser_use-r1-1dd09eb8045c | `browser_use-r1-1dd09eb8045c.json` | `b8321b5a09eff4a3317a36e241c4b67a1f9322c28a40f1f550f32e069e1f5f72` |
| browser_use-r1-2a9954d08b4f | `browser_use-r1-2a9954d08b4f.json` | `42e8e48fa15fc05b3601a8b0fc983ee030525b9750f95b46753771fa5eaef22c` |
| browser_use-r1-2b7d19182e36 | `browser_use-r1-2b7d19182e36.json` | `5406b3a9201da9e722cb0e70af7b2e4235a9d4354557b9906aa43fdbdc6fa1b6` |
| browser_use-r1-9e3fea13a347 | `browser_use-r1-9e3fea13a347.json` | `85b2e1e3d7d9c2006dd0e30fb4cce1a9883e17560f39a5cf5eb011e53a4a91bd` |
| browser_use-r2-2261ac50d7c9 | `browser_use-r2-2261ac50d7c9.json` | `eba0a0c86b2bcaef0b1aa6cce0079ed5f3ebcd79725eb3b5e1402e769e9ab0c4` |
| browser_use-r2-2e9db09e9061 | `browser_use-r2-2e9db09e9061.json` | `a89f4a8e7b6d1a30698f4e8e9c4b67559b1e07ef8f49c6e574a1daaac0f4dd46` |
| browser_use-r2-8eac22bff417 | `browser_use-r2-8eac22bff417.json` | `4d0dc962ed316d30a818a69f84ee8c3448ec6c2069f6224d25581b0b5af0d87f` |
| browser_use-r2-92393cccf09d | `browser_use-r2-92393cccf09d.json` | `998d6a7cbef64286891af28369a58bbc1c067191c5df0ab8fce9621d8b85c53f` |
| browser_use-r2-ef10921b5b07 | `browser_use-r2-ef10921b5b07.json` | `8323cecf1686e08f84f5f1979edc3fbd16105c6dbc7147e4a7979c9921888765` |
| browser_use-r3-879518e4f1e8 | `browser_use-r3-879518e4f1e8.json` | `ebf9eac9e52628ae81c850fdc04099d29d432e1c412712bfd479cc8d3b2635b8` |
| browser_use-r3-8bcbc6e4c0e6 | `browser_use-r3-8bcbc6e4c0e6.json` | `0908d6f3f38190065cc51d92d3b3d2ac315317494b2432040bcf5bf6c2d66a0a` |
| browser_use-r3-af0133124c17 | `browser_use-r3-af0133124c17.json` | `cc95a9c2d1a0df283d861824c8175333f8cf84effcbdb787e40a272277dd5578` |
| browser_use-r3-cda05111a1d0 | `browser_use-r3-cda05111a1d0.json` | `55c57388da3759a470bde9893e2219975b2e72011aa29fe751d3746418ac7806` |
| browser_use-r3-f46124029b44 | `browser_use-r3-f46124029b44.json` | `fcdca8924cec1258210b5ed201997fc4729dec8a14cf0d64eedc5b9a8284d648` |
| playwright_mcp-r1-03abe85dc3d1 | `playwright_mcp-r1-03abe85dc3d1.json` | `10d9010f6520b4160556fd49e14653ebf191cd82ecdb3af71c1af22fe438a16e` |
| playwright_mcp-r1-0aed0ac2425a | `playwright_mcp-r1-0aed0ac2425a.json` | `012dfef6b54b4c26813edc43a63d8472965af7f45711127249c32939cf1d2d98` |
| playwright_mcp-r1-312ee14b271d | `playwright_mcp-r1-312ee14b271d.json` | `1239d8994d7cb1f50c1d36372add09834c98aa2d1703bc5efd4678b355427182` |
| playwright_mcp-r1-567fcf691038 | `playwright_mcp-r1-567fcf691038.json` | `96df175827dbdf4c21a7b664c51b600b585a87f8df549c9536fb9cbcd1e1593b` |
| playwright_mcp-r1-d5af06abc047 | `playwright_mcp-r1-d5af06abc047.json` | `b4fc24b6d5500613e0c695d5ffb974492c53049445ac97c522beb248cac606bd` |
| playwright_mcp-r2-05602cec9276 | `playwright_mcp-r2-05602cec9276.json` | `fe3f0773a7c07b898ac5683f9d147fcf9eaa827c47d7425b8fb84fb17191d909` |
| playwright_mcp-r2-122d62a97151 | `playwright_mcp-r2-122d62a97151.json` | `91b645ae67c420e42c8169c370ec75d647bfc5d5cb1e3bbf7649456039ffb6fd` |
| playwright_mcp-r2-2368c5802784 | `playwright_mcp-r2-2368c5802784.json` | `6e12dc51a68cb4b92b297e853cfdc4ee936c389aeba08db5f6fe50cd2aec4e79` |
| playwright_mcp-r2-286499b28c13 | `playwright_mcp-r2-286499b28c13.json` | `72a659c5ba5b043520ea416fddc60ca0e3c36a498f1330b56c11f04a87a53649` |
| playwright_mcp-r2-54e5c1ea5e89 | `playwright_mcp-r2-54e5c1ea5e89.json` | `cf88ee4980fc2ae9e8ef7837aeed7a44de3e68ad024e4e2377ab983524aef57b` |
| playwright_mcp-r3-30db569e463e | `playwright_mcp-r3-30db569e463e.json` | `449afea156e9e6281859648773a4944cae4d2523fd733241d5edae1318c01bfd` |
| playwright_mcp-r3-59a57a5ab588 | `playwright_mcp-r3-59a57a5ab588.json` | `e17bde1e16b8230a13413ca1db940fbe79dd0f375a220217c44377114d5a8f06` |
| playwright_mcp-r3-9e3022c6e64f | `playwright_mcp-r3-9e3022c6e64f.json` | `0524c39998c095859cb78bb1a69d806b6564388932500c57fc1319768f077eec` |
| playwright_mcp-r3-d6919b1f9d6c | `playwright_mcp-r3-d6919b1f9d6c.json` | `4e66954befc1d9c03be0eb1052af3c1b87989c98de1424d83770ca797b78d642` |
| playwright_mcp-r3-efb69aa18420 | `playwright_mcp-r3-efb69aa18420.json` | `290c6b0d8325300d00e1917e6f48c7f59b43c402274a7f8d85b34bf64726698a` |
| reference-29f782e875d0 | `reference-29f782e875d0.json` | `671f871644b32666609d2644ac44beecd24f17b000016bc3095640a89f3cfb84` |
| reference-4405936753f1 | `reference-4405936753f1.json` | `8b200a670c54ed6702a87fd50f0ffb8cd49f6c5bcb985282e01f4b7da864be38` |
| reference-6d9bb14a1f22 | `reference-6d9bb14a1f22.json` | `f393617673b630c2e00ba83e9664527319b3f2a76735619a476aaf511db0ee51` |
| reference-701f6a545e66 | `reference-701f6a545e66.json` | `b3f87ac62dc9e17e27957f69c5a0762364d8fb2efe41cd951f53b118c79d9e59` |
| reference-9300d4900e56 | `reference-9300d4900e56.json` | `efd5617088a0116ebd8a2d11c1b31da9d32eb2f573522c963f166a16e456196c` |
| reference-94425731f4b8 | `reference-94425731f4b8.json` | `3efdf22b3fd43c4369f108b1df815401d2f0a74234857cb8081f513d70c1f6c8` |
| reference-a2c77ede9b0d | `reference-a2c77ede9b0d.json` | `801143cebdd422d48d97fc104f8a73eb7e2e3e1d575e80a171bc9c80fe2f7c0b` |
| reference-c96bf80af0d8 | `reference-c96bf80af0d8.json` | `773c2aabbfc4eef5333ea3fb21c77e5c84a6ddb9ed67785f88806d1240900b29` |
| reference-cf1f7e57b1c7 | `reference-cf1f7e57b1c7.json` | `52c1f2907cb80d58ac3b7d71e19145e956e6c0ac53ba412e3047ad5c42f24a95` |
| reference-dbddf62fa9a7 | `reference-dbddf62fa9a7.json` | `2d6bd0d172306c23f3a78fde995798890d54d9dbbd5d5baf117e496e79918f9c` |
| reference-e343389e64df | `reference-e343389e64df.json` | `d27a0dc582acdddf5f9dbba464ac9bd2682c6c84c34d903365bac96a0aeb0a5d` |
| reference-f0ab2774f9e3 | `reference-f0ab2774f9e3.json` | `9b32c5feec780f5f44da0fddcc4a5ad662a4ad1fed0a41e7192fbc8a1bbe1368` |
| reference-f1081e3ea1e7 | `reference-f1081e3ea1e7.json` | `2a29b723a3e8b10931ca302b01f09d2450ef71d3be3b70976ced9b1859977093` |
| reference-f319161e34b7 | `reference-f319161e34b7.json` | `d08e59e817a636fd8a7391ba9d91f438779c54a41ad72b86a72ea2cbe9fd12e9` |
| reference-f5cbaa3ce4b2 | `reference-f5cbaa3ce4b2.json` | `fdddc782bd376a76bd240dfa17cb3b756e7e9cd2aa60348e155c219dc10f434d` |
| restricted-r1-0d5ce0482894 | `restricted-r1-0d5ce0482894.json` | `c921793f89ce11bca9cf227737e2d57a23475a3548a09c278ee81c461fc58433` |
| restricted-r1-2ef09f2353c6 | `restricted-r1-2ef09f2353c6.json` | `cb87e7c94958786ab4074f475f950afbf741c0550c001122f59662601a0eb3b6` |
| restricted-r1-a63b85e5fdb8 | `restricted-r1-a63b85e5fdb8.json` | `4498ca06fc53ba21ca4a4c6da0033215f98be6724952d21db4bf41b8b2c72c1b` |
| restricted-r1-c6a33c39aa02 | `restricted-r1-c6a33c39aa02.json` | `bbd1a19b9e1db3500c12a7bac9fc3a53722a37c3cf89f9565ecdf62cb107a4b0` |
| restricted-r1-e3a6d51324dc | `restricted-r1-e3a6d51324dc.json` | `f12ce629a5e74fa18f28038e06536ab4ccc6b2eacd14c726e9f03be55a0c41ca` |
| restricted-r2-03b6fbf220b8 | `restricted-r2-03b6fbf220b8.json` | `378d96840ab70da09d6df7d767e880afdec017a48ee64666d186473d4724b9d4` |
| restricted-r2-49136c15c4de | `restricted-r2-49136c15c4de.json` | `d270128a4dc611a786b102c50cfee985ca52f6ef834ac75ae2a411aa2ccbe739` |
| restricted-r2-626e3ccd4e6e | `restricted-r2-626e3ccd4e6e.json` | `7d26a333744414f60496bd580c8cac5a5847369902b686e309a332c05b4e4b47` |
| restricted-r2-a4c5c9ccbec5 | `restricted-r2-a4c5c9ccbec5.json` | `8fad3f0b615889cb5d2534233dcb7e9a719af55a59e91adb455458f8d644d2ab` |
| restricted-r2-b5f199946bf9 | `restricted-r2-b5f199946bf9.json` | `c95c811e471ef722afe36410b1f221ed1c1ad55f4ec79af4bb35eab517ab4b86` |
| restricted-r3-70c083d0f8c1 | `restricted-r3-70c083d0f8c1.json` | `e199bec853556978e725b997a02d6dd81af4ab8906efd58020aa750926ab107c` |
| restricted-r3-9dd2371f5ffb | `restricted-r3-9dd2371f5ffb.json` | `5fc698531722e41bb9d67beaa27bee1e9d1918fa7aa7fde18feb73a2d3d4f050` |
| restricted-r3-a7bce1bfa7fe | `restricted-r3-a7bce1bfa7fe.json` | `638d43c3fd6ecab99833a92fff49b15be39b168b59a3aaa60ea21a348306c8ae` |
| restricted-r3-be5f84b937fa | `restricted-r3-be5f84b937fa.json` | `4ccea661f30742270a23de6cf5c3cbe9957c17abbe75f0d4be77b22963402bb7` |
| restricted-r3-f856e75a5fc9 | `restricted-r3-f856e75a5fc9.json` | `c317f5ba2d94be75ded5d3854bfba11cc9e4b541640383dd98ea6d479bb78623` |
