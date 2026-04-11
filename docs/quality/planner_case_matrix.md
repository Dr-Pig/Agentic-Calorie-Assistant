# Planner Case Matrix

This matrix defines the canonical case families for the LLM-first calorie estimation workflow.

## Core Families

| Case Family | Example | Expected Planner Outcome | Expected Primary Outcome |
| --- | --- | --- | --- |
| `exact_item` | `麥當勞勁辣雞腿堡` | `entity_type=exact_item`, `clarification_needed=false` | direct answer when evidence is sufficient |
| `brand_only_chain` | `摩斯漢堡` | `clarification_needed=true`, target `menu_item_identity` | ask which menu item/combo was ordered |
| `brand_plus_partial_item` | `摩斯豬排堡` | prefer exact or partial item lookup | estimate or ask one targeted follow-up |
| `combo_meal` | `青梅豬排堡加紅茶` | `entity_type=combo_meal` | decompose main item + sides + drink |
| `customizable_drink` | `珍珠奶茶中杯微糖去冰` | drink customization targets | ask only missing customization slots |
| `customizable_bowl` | `滷味加王子麵跟豆皮` | component rebuild | rebuild components before estimate |
| `shared_meal` | `聚餐吃了魚跟炒麵` | target `personal_share_portion` | follow-up before estimate |
| `buffet_like` | `自助餐夾三樣菜` | target portion slots | follow-up before estimate |
| `home_cooked` | `媽媽煮咖哩飯` | home/private prior | estimate with uncertainty or ask portion |
| `soup_or_broth_sensitive` | `拉麵` | target `broth_consumption` | ask about broth if missing |
| `snack_packaged` | `7-11 茶葉蛋` | exact/package lookup | direct answer when exact truth exists |

## Multi-Turn Families

| Flow | Example | Expected Planner Outcome |
| --- | --- | --- |
| `ambiguous_short_reply` | `大碗的` | clarification linked to active meal |
| `correction_or_override` | `不是剛剛那個，我晚餐是牛肉麵` | correction or new meal switch |
| `new_meal_switch` | `早餐講完後又說午餐吃便當` | break from active meal and start new intake |
| `brand_followup_completion` | `摩斯漢堡 -> 我是吃青梅豬排堡加紅茶` | second turn should be clarification/correction, not standalone new intake by default |

## Invariants

- `brand_only_chain` must never directly produce kcal/macros.
- `clarification_needed=true` must force `action_taken=follow_up`.
- `clarification` / `modification` / `correction` should reuse active meal lineage unless the planner explicitly marks `state_link=new_meal_switch`.
- Grounding should prefer `resolved_query` over raw user text.
