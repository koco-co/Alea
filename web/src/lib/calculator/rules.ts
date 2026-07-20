export type SportteryPlay = "had" | "hhad" | "crs" | "ttg" | "hafu";

export type PassType = `${number}x${number}`;

export interface PlayRule {
  readonly label: string;
  readonly maximumPassSize: number;
}

export interface PayoutCap {
  readonly minimumLegs: number;
  readonly maximumLegs: number;
  readonly amount: number;
}

export interface SportteryRules {
  readonly version: number;
  readonly effectiveAt: string;
  readonly currency: "CNY";
  readonly unitStake: number;
  readonly maximumMultiplier: number;
  readonly maximumTicketAmount: number;
  readonly sameMatchCrossPlayAllowed: false;
  readonly plays: Readonly<Record<SportteryPlay, PlayRule>>;
  /** Each entry expands an MxN pass into its component pass sizes. */
  readonly passTypes: Readonly<Record<PassType, readonly number[]>>;
  readonly payoutCaps: readonly PayoutCap[];
  readonly rounding: {
    readonly decimals: 2;
    readonly mode: "half_even";
    readonly scope: "each_expanded_winning_bet";
  };
  readonly invalidMatch: {
    readonly strategy: "remove_from_each_original_combination";
    readonly allVoid: "refund_original_stake";
    readonly oddsOneShortcutAllowed: false;
  };
  readonly officialCorrection: {
    readonly sportteryOfficialResult: "recalculate_and_append_revision";
    readonly competitionOrganizerResult: "keep_original_sporttery_result";
  };
  readonly verificationStatus: "official_materials_transcribed_pending_human_verification";
}

const passTypes: Record<PassType, readonly number[]> = {
  "1x1": [1],
  "2x1": [2],
  "3x1": [3],
  "3x3": [2],
  "3x4": [2, 3],
  "4x1": [4],
  "4x4": [3],
  "4x5": [3, 4],
  "4x6": [2],
  "4x11": [2, 3, 4],
  "5x1": [5],
  "5x5": [4],
  "5x6": [4, 5],
  "5x10": [2],
  "5x16": [3, 4, 5],
  "5x20": [2, 3],
  "5x26": [2, 3, 4, 5],
  "6x1": [6],
  "6x6": [5],
  "6x7": [5, 6],
  "6x15": [2],
  "6x20": [3],
  "6x22": [4, 5, 6],
  "6x35": [2, 3],
  "6x42": [3, 4, 5, 6],
  "6x50": [2, 3, 4],
  "6x57": [2, 3, 4, 5, 6],
  "7x1": [7],
  "7x7": [6],
  "7x8": [6, 7],
  "7x21": [5],
  "7x35": [4],
  "7x120": [2, 3, 4, 5, 6, 7],
  "8x1": [8],
  "8x8": [7],
  "8x9": [7, 8],
  "8x28": [6],
  "8x56": [5],
  "8x70": [4],
  "8x247": [2, 3, 4, 5, 6, 7, 8],
};

/**
 * Version 1 mirrors the rule seed used by Alea. It remains explicitly marked
 * pending human verification and must not be presented as production-authorized
 * Sporttery sales data.
 */
export const SPORTTERY_RULES_V1: SportteryRules = {
  version: 1,
  effectiveAt: "2026-07-20T00:00:00+08:00",
  currency: "CNY",
  unitStake: 2,
  maximumMultiplier: 50,
  maximumTicketAmount: 6_000,
  sameMatchCrossPlayAllowed: false,
  plays: {
    had: { label: "胜平负", maximumPassSize: 8 },
    hhad: { label: "让球胜平负", maximumPassSize: 8 },
    crs: { label: "比分", maximumPassSize: 4 },
    ttg: { label: "总进球数", maximumPassSize: 6 },
    hafu: { label: "半全场胜平负", maximumPassSize: 4 },
  },
  passTypes,
  payoutCaps: [
    { minimumLegs: 1, maximumLegs: 1, amount: 100_000 },
    { minimumLegs: 2, maximumLegs: 3, amount: 200_000 },
    { minimumLegs: 4, maximumLegs: 5, amount: 500_000 },
    { minimumLegs: 6, maximumLegs: 8, amount: 1_000_000 },
  ],
  rounding: {
    decimals: 2,
    mode: "half_even",
    scope: "each_expanded_winning_bet",
  },
  invalidMatch: {
    strategy: "remove_from_each_original_combination",
    allVoid: "refund_original_stake",
    oddsOneShortcutAllowed: false,
  },
  officialCorrection: {
    sportteryOfficialResult: "recalculate_and_append_revision",
    competitionOrganizerResult: "keep_original_sporttery_result",
  },
  verificationStatus:
    "official_materials_transcribed_pending_human_verification",
};

export const DEFAULT_SPORTTERY_RULES = SPORTTERY_RULES_V1;
