# Source Registry Review 2026-03-30

## Purpose

This review takes the 35 candidates from `source-registry-v1-20260330-024845` and decides which entries are clean enough to enter the formal `data_build/source_registry.json`.

The standard used here is stricter than the raw run:
- keep only sources that are reusable as registry entries
- prefer source families over one-off example pages
- prefer nutrition-capable official sources over identity-only menu pages
- keep `P2` only for pattern priors

## Accepted

The following 20 entries were accepted into the formal source registry:

- `tw-tfda-food-nutrition-composition-dataset`
- `tw-tfda-food-nutrition-database-portal`
- `pocari-tw-products-all`
- `heysong-fin-brand-page`
- `heysong-water-brand-page`
- `heysong-tea-brand-page`
- `seven-eleven-tw-official-product-pages`
- `familymart-freshfood-product-listing`
- `mcdonalds-tw-nutrition-calculator`
- `mos-burger-tw-item-pages`
- `burger-king-tw-nutrition-table`
- `kebuke-menu`
- `tp-tea-taiwan-menu`
- `macu-tea-drink-menu`
- `milksha-products`
- `carrefour-tw-online-product-pages`
- `pxgo-hourarrive-product-pages`
- `tainan-school-lunch-recipe-design-handbook`
- `moa-food-agri-education-recipe-platform`
- `keelung-school-lunch-work-handbook`

## Canonicalization decisions

### Merged into a broader canonical source

- `tw-7eleven-ipreorder-product-pages`
- `seven-eleven-tw-ipreorder-product-pages`

These pointed to the same official 7-ELEVEN preorder family. They were merged into one canonical entry:
- `seven-eleven-tw-official-product-pages`

### Reworded as a source family

- `mos-burger-tw-product-page-mos-burger`

This was kept, but the registry entry was renamed to `mos-burger-tw-item-pages` because the example URL is only a representative item page pattern.

## Rejected for now

### Too narrow or too item-specific

- `pxmart-yuchayuan-lemon-tea`
  - Good official retailer evidence for a single item, but too narrow to be a reusable registry source family.
- `tw-familymart-mobile-shop-product-pages`
  - Too dependent on one example product URL and client-rendered behavior.
- `mcdonalds-tw-product-page-big-mac`
  - Redundant once the official nutrition calculator is already accepted.
- `burger-king-tw-product-page-double-whopper`
  - Redundant once the official nutrition page is already accepted.
- `kfc-tw-product-page-colonel-nuggets-4pc`
  - Useful as a lead, but not strong enough yet to enter the formal registry without better confirmation of nutrition visibility and stable extraction.
- `tainan-taiwan-tilapia-school-lunch-recipes`
  - Too narrow and ingredient-specific for a reusable meal-pattern source.

### Official menu pages without enough nutrition signal

These were not admitted into the formal source registry because they look useful for identity, but the current path needs cleaner nutrition-capable sources for `exact_item` extraction:

- `tw-tasty-menu`
- `tw-tokiya-menu`
- `tw-tokiya-classic-dish-page`
- `tw-wangsteak-menu`
- `tw-wangsteak-product-page`
- `tw-yakiyan-menu`
- `tw-giguo-menu`
- `tw-sushiro-menu`

They can stay as backlog candidates for a future `identity-only` or `menu-structure` registry if we later split exact-item source classes more finely.

## Takeaways

- The raw wide-research run was useful for coverage, but too generous about what counts as a reusable registry source.
- Exact-item registry entries should prefer official nutrition destinations, stable item families, or retailer fallback families, not one-off sample pages.
- `P2` should remain small and explicit. It is for pattern priors, not for nutrition truth.
- The formal registry should stay conservative. It is easier to add sources later than to clean a polluted registry downstream.
