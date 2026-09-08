"""Fixed read-only DOM collection shared by all four runners."""

COLLECT_FACTS = r"""() => {
  const text = el => el && el.getClientRects().length ? el.innerText.trim() : '';
  const product = document.querySelector('#productTitle');
  const heading = product || document.querySelector('h1');
  const price = document.querySelector('#corePriceDisplay_desktop_feature_div');
  return JSON.stringify({url: location.href, heading: text(heading).slice(0,2000),
    price_text: text(price).slice(0,4000)});
}"""
