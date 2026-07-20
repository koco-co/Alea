# G5 — Data source authorization and Sporttery rules

Status: **official pages located; human rule transcription and licensing decision blocked**.

On 2026-07-20, the official help center exposed the five football game-rule pages plus
mixed/free-pass and bonus-calculation explanations. The current rule footnotes visible on
the official pages state a base stake of CNY 2, multi-bet range adjusted to 2–50, maximum
ticket purchase amount adjusted to CNY 6,000, and void-match recalculation by removing the
match from each original pass combination rather than substituting odds of 1.0.

Sources used for the draft golden fixture:

- <https://www.sporttery.cn/bzzx/20210118/3060333.html?gid=3>
- <https://www.sporttery.cn/bzzx/20210118/3060334.html?gid=3>
- <https://www.sporttery.cn/bzzx/20210118/3003197.html?gid=3>
- <https://www.sporttery.cn/bzzx/20210118/3003195.html?gid=3>
- <https://www.sporttery.cn/bzzx/20210118/3003194.html?gid=3>
- <https://www.sporttery.cn/bzzx/20210207/3040217.html?gid=3>
- <https://www.sporttery.cn/bzzx/20210207/3249715.html?gid=3>
- <https://www.sporttery.cn/bzzx/20210207/3273604.html?gid=3>

The fixture is explicitly labelled non-official interaction SP. It may validate arithmetic
but cannot close the production rule/version or data-license Gate. A human must verify the
complete pass-type matrix, per-play maxima, caps, rounding, effective dates, amendments,
and permission for automated access/cache/display/history/redistribution before adding the
`sporttery_rule_versions` seed.

```bash
cd api
uv run --locked pytest tests/test_g5_data_rules.py -v
cd ../web
bun test src/lib/calculator/engine.test.ts
```
