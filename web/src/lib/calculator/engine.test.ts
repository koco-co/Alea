import { describe, expect, test } from "bun:test";

import fixture from "../../../../api/tests/fixtures/sporttery_sample.json";
import { calcCombinations, type SportteryPlay } from "./engine";

describe("Sporttery golden fixtures", () => {
  for (const sample of fixture.cases) {
    test(sample.name, () => {
      const result = calcCombinations(
        sample.legs.map((leg) => ({
          matchId: leg.match_id,
          play: leg.play as SportteryPlay,
          odds: leg.odds,
          isVoid: leg.is_void,
        })),
        sample.pass_size,
        sample.multiplier,
      );
      expect(result).toEqual({
        betCount: sample.expected.bet_count,
        amount: sample.expected.amount,
        maximumBonus: sample.expected.maximum_bonus,
        effectiveCombinationCount: sample.expected.effective_combination_count,
      });
    });
  }
});
