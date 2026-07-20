import { describe, expect, test } from "bun:test";

import {
  calculateTicket,
  requiresResultRecalculation,
  type CalculationInput,
  type SportteryPlay,
  type TicketLeg,
} from "../engine";
import { SPORTTERY_RULES_V1 } from "../rules";

const leg = (
  matchId: string,
  play: SportteryPlay = "had",
  odds: readonly number[] = [2],
  extra: Partial<TicketLeg> = {},
): TicketLeg => ({ matchId, play, odds, ...extra });

describe("versioned Sporttery calculator", () => {
  test.each([
    ["had", 8],
    ["hhad", 8],
    ["crs", 4],
    ["ttg", 6],
    ["hafu", 4],
  ] satisfies [SportteryPlay, number][]) (
    "%s has the configured dynamic pass limit",
    (play, maximumPassSize) => {
      expect(SPORTTERY_RULES_V1.plays[play].maximumPassSize).toBe(maximumPassSize);
      expect(
        calculateTicket({ legs: [leg("a", play, [1.8])], passTypes: ["1x1"] }),
      ).toMatchObject({ betCount: 1, amount: 2, maximumBonus: 3.6 });
    },
  );

  test("compound selections count every bet but only the highest compatible outcome pays", () => {
    const result = calculateTicket({
      legs: [leg("a", "had", [1.5, 2.5]), leg("b", "ttg", [1.8, 3])],
      passTypes: ["2x1"],
    });
    expect(result).toMatchObject({
      betCount: 4,
      amount: 8,
      expandedCombinationCount: 1,
      maximumBonus: 15,
    });
  });

  test("simple passes from 2x1 through 8x1 expand once", () => {
    for (let size = 2; size <= 8; size += 1) {
      const result = calculateTicket({
        legs: Array.from({ length: size }, (_, index) => leg(`m-${index}`, "had", [1.5])),
        passTypes: [`${size}x1`],
      } as CalculationInput);
      expect(result.betCount).toBe(1);
      expect(result.expandedCombinationCount).toBe(1);
      expect(result.amount).toBe(2);
    }
  });

  test("free pass sums each selected simple pass size", () => {
    const result = calculateTicket({
      legs: [leg("a"), leg("b"), leg("c")],
      passTypes: ["2x1", "3x1"],
    });
    expect(result).toMatchObject({
      betCount: 4,
      amount: 8,
      expandedCombinationCount: 4,
      maximumBonus: 40,
    });
  });

  test("bankers are present in every expanded combination", () => {
    const result = calculateTicket({
      legs: [leg("a", "had", [2], { isBanker: true }), leg("b"), leg("c")],
      passTypes: ["2x1"],
    });
    expect(result).toMatchObject({
      betCount: 2,
      amount: 4,
      expandedCombinationCount: 2,
      maximumBonus: 16,
    });
  });

  test("4x11 expands to six doubles, four triples, and one quadruple", () => {
    const result = calculateTicket({
      legs: [leg("a"), leg("b"), leg("c"), leg("d")],
      passTypes: ["4x11"],
    });
    expect(result).toMatchObject({
      betCount: 11,
      amount: 22,
      expandedCombinationCount: 11,
      maximumBonus: 144,
    });
  });

  test("void legs are removed per original bet rather than replaced with odds 1", () => {
    const result = calculateTicket({
      legs: [leg("a", "had", [1.8, 2.2], { isVoid: true }), leg("b", "had", [3])],
      passTypes: ["2x1"],
    });
    expect(result).toMatchObject({ betCount: 2, amount: 4, maximumBonus: 12 });
  });

  test("all-void combinations refund every original compound bet", () => {
    const result = calculateTicket({
      legs: [leg("a", "had", [1.8, 2.2], { isVoid: true })],
      passTypes: ["1x1"],
      multiplier: 2,
    });
    expect(result).toMatchObject({ betCount: 2, amount: 8, maximumBonus: 8 });
  });

  test("rounds each expanded winning bet half-up to cents", () => {
    expect(
      calculateTicket({ legs: [leg("a", "had", [1.0025])], passTypes: ["1x1"] })
        .maximumBonus,
    ).toBe(2.01);
  });

  test("reports ticket amount and payout cap overages", () => {
    const amountOverage = calculateTicket({
      legs: Array.from({ length: 8 }, (_, index) => leg(`m-${index}`, "had", [1.5, 2])),
      passTypes: ["8x247"],
    });
    expect(amountOverage.amount).toBe(13_088);
    expect(amountOverage.amountCapExceeded).toBe(true);

    const payoutOverage = calculateTicket({
      legs: Array.from({ length: 6 }, (_, index) => leg(`p-${index}`, "had", [1_000])),
      passTypes: ["6x1"],
    });
    expect(payoutOverage.payoutCap).toBe(1_000_000);
    expect(payoutOverage.payoutCapExceeded).toBe(true);
    expect(payoutOverage.maximumBonus).toBe(1_000_000);
  });

  test("rejects combinations above the strictest selected play limit", () => {
    expect(() =>
      calculateTicket({
        legs: [
          leg("a", "crs"),
          leg("b"),
          leg("c"),
          leg("d"),
          leg("e"),
        ],
        passTypes: ["5x1"],
      }),
    ).toThrow("at most 4 legs");
  });

  test("only an official Sporttery result correction triggers recalculation", () => {
    expect(requiresResultRecalculation("sporttery_official")).toBe(true);
    expect(requiresResultRecalculation("competition_organizer")).toBe(false);
  });
});
