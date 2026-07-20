import {
  DEFAULT_SPORTTERY_RULES,
  type PassType,
  type SportteryPlay,
  type SportteryRules,
} from "./rules";

export type { PassType, SportteryPlay, SportteryRules } from "./rules";

export interface TicketLeg {
  readonly matchId: string;
  readonly play: SportteryPlay;
  /** Fixed-odds snapshots for every selected outcome in this play. */
  readonly odds: readonly number[];
  readonly isVoid?: boolean;
  readonly isBanker?: boolean;
}

export interface CalculationInput {
  readonly legs: readonly TicketLeg[];
  /** Multiple simple pass types represent a free-pass selection. */
  readonly passTypes: readonly PassType[];
  readonly multiplier?: number;
  readonly bankerMatchIds?: readonly string[];
}

export interface CalculationResult {
  readonly rulesVersion: number;
  readonly betCount: number;
  readonly amount: number;
  readonly expandedCombinationCount: number;
  readonly uncappedMaximumBonus: number;
  readonly maximumBonus: number;
  readonly payoutCap: number;
  readonly payoutCapExceeded: boolean;
  readonly amountCapExceeded: boolean;
}

/** Compatibility result for the Gate 0 three-argument API. */
export interface TicketResult {
  readonly betCount: number;
  readonly amount: number;
  readonly maximumBonus: number;
  readonly effectiveCombinationCount: number;
}

export type ResultCorrectionSource =
  "sporttery_official" | "competition_organizer";

const money = (value: number): number => {
  const scaled = value * 100;
  const lower = Math.floor(scaled);
  const fraction = scaled - lower;
  const tolerance = 1e-9;
  if (fraction > 0.5 + tolerance) return (lower + 1) / 100;
  if (fraction < 0.5 - tolerance) return lower / 100;
  return (lower % 2 === 0 ? lower : lower + 1) / 100;
};

function combinations<T>(items: readonly T[], size: number): T[][] {
  if (size === 0) return [[]];
  if (items.length < size) return [];
  return items.flatMap((item, index) =>
    combinations(items.slice(index + 1), size - 1).map((rest) => [
      item,
      ...rest,
    ]),
  );
}

function product(values: readonly number[]): number {
  return values.reduce((total, value) => total * value, 1);
}

function parsePassType(passType: PassType): {
  matchCount: number;
  betCount: number;
} {
  const [matchCount, betCount] = passType.split("x").map(Number);
  return { matchCount, betCount };
}

function selectedBankers(input: CalculationInput): Set<string> {
  const bankers = new Set(input.bankerMatchIds ?? []);
  for (const leg of input.legs) {
    if (leg.isBanker) bankers.add(leg.matchId);
  }
  return bankers;
}

function expandWithBankers(
  legs: readonly TicketLeg[],
  componentSize: number,
  bankerIds: ReadonlySet<string>,
): TicketLeg[][] {
  const bankers = legs.filter((leg) => bankerIds.has(leg.matchId));
  const drags = legs.filter((leg) => !bankerIds.has(leg.matchId));
  return combinations(drags, componentSize - bankers.length).map(
    (selection) => [...bankers, ...selection],
  );
}

function payoutCapForLegs(legCount: number, rules: SportteryRules): number {
  const band = rules.payoutCaps.find(
    ({ minimumLegs, maximumLegs }) =>
      legCount >= minimumLegs && legCount <= maximumLegs,
  );
  if (!band)
    throw new Error(`no payout cap is configured for ${legCount} legs`);
  return band.amount;
}

export function validateTicket(
  input: CalculationInput,
  rules: SportteryRules = DEFAULT_SPORTTERY_RULES,
): void {
  const multiplier = input.multiplier ?? 1;
  if (
    !Number.isInteger(multiplier) ||
    multiplier < 1 ||
    multiplier > rules.maximumMultiplier
  ) {
    throw new Error(
      `multiplier must be an integer between 1 and ${rules.maximumMultiplier}`,
    );
  }
  if (input.legs.length === 0) throw new Error("at least one leg is required");
  if (input.passTypes.length === 0)
    throw new Error("at least one pass type is required");
  if (new Set(input.passTypes).size !== input.passTypes.length) {
    throw new Error("pass types must be unique");
  }
  if (
    new Set(input.legs.map((leg) => leg.matchId)).size !== input.legs.length
  ) {
    throw new Error("a ticket may contain at most one play per match");
  }
  for (const leg of input.legs) {
    if (!rules.plays[leg.play])
      throw new Error(`unsupported play: ${leg.play}`);
    if (
      leg.odds.length === 0 ||
      leg.odds.some((odd) => !Number.isFinite(odd) || odd <= 1)
    ) {
      throw new Error(
        "each leg requires one or more finite fixed odds greater than 1",
      );
    }
  }

  const dynamicMaximum = Math.min(
    ...input.legs.map((leg) => rules.plays[leg.play].maximumPassSize),
  );
  if (input.legs.length > dynamicMaximum) {
    throw new Error(`selected plays allow at most ${dynamicMaximum} legs`);
  }

  const bankerIds = selectedBankers(input);
  if (
    [...bankerIds].some(
      (matchId) => !input.legs.some((leg) => leg.matchId === matchId),
    )
  ) {
    throw new Error("every banker must reference a selected match");
  }

  let minimumComponentSize = Number.POSITIVE_INFINITY;
  for (const passType of input.passTypes) {
    const componentSizes = rules.passTypes[passType];
    if (!componentSizes) throw new Error(`unsupported pass type: ${passType}`);
    const { matchCount, betCount } = parsePassType(passType);
    if (betCount > 1 && input.legs.length !== matchCount) {
      throw new Error(`${passType} requires exactly ${matchCount} legs`);
    }
    if (betCount === 1 && input.legs.length < matchCount) {
      throw new Error(`${passType} requires at least ${matchCount} legs`);
    }
    if (matchCount > dynamicMaximum) {
      throw new Error(
        `${passType} exceeds the selected plays' ${dynamicMaximum}-leg limit`,
      );
    }
    minimumComponentSize = Math.min(minimumComponentSize, ...componentSizes);
  }
  if (bankerIds.size >= minimumComponentSize) {
    throw new Error(`banker count must be less than ${minimumComponentSize}`);
  }
}

export function calculateTicket(
  input: CalculationInput,
  rules: SportteryRules = DEFAULT_SPORTTERY_RULES,
): CalculationResult {
  validateTicket(input, rules);
  const multiplier = input.multiplier ?? 1;
  const bankerIds = selectedBankers(input);
  let betCount = 0;
  let expandedCombinationCount = 0;
  let uncappedMaximumBonus = 0;

  for (const passType of input.passTypes) {
    for (const componentSize of rules.passTypes[passType]) {
      for (const combo of expandWithBankers(
        input.legs,
        componentSize,
        bankerIds,
      )) {
        expandedCombinationCount += 1;
        const originalBetCount = product(combo.map((leg) => leg.odds.length));
        betCount += originalBetCount;

        const voidLegs = combo.filter((leg) => leg.isVoid);
        const effectiveLegs = combo.filter((leg) => !leg.isVoid);
        const voidDuplicateCount = product(
          voidLegs.map((leg) => leg.odds.length),
        );
        const linePayout =
          effectiveLegs.length === 0
            ? rules.unitStake * multiplier * originalBetCount
            : rules.unitStake *
              multiplier *
              voidDuplicateCount *
              product(effectiveLegs.map((leg) => Math.max(...leg.odds)));
        uncappedMaximumBonus += money(linePayout);
      }
    }
  }

  const amount = money(rules.unitStake * multiplier * betCount);
  uncappedMaximumBonus = money(uncappedMaximumBonus);
  const payoutCapLegCount = Math.max(
    ...input.passTypes.map((passType) => parsePassType(passType).matchCount),
  );
  const payoutCap = payoutCapForLegs(payoutCapLegCount, rules);
  return {
    rulesVersion: rules.version,
    betCount,
    amount,
    expandedCombinationCount,
    uncappedMaximumBonus,
    maximumBonus: Math.min(uncappedMaximumBonus, payoutCap),
    payoutCap,
    payoutCapExceeded: uncappedMaximumBonus > payoutCap,
    amountCapExceeded: amount > rules.maximumTicketAmount,
  };
}

export function requiresResultRecalculation(
  source: ResultCorrectionSource,
): boolean {
  return source === "sporttery_official";
}

export function validateCombo(
  legs: readonly TicketLeg[],
  passSize: number,
  multiplier: number,
  rules: SportteryRules = DEFAULT_SPORTTERY_RULES,
): void {
  if (!Number.isInteger(passSize) || passSize < 1 || passSize > 8) {
    throw new Error("passSize must be an integer between 1 and 8");
  }
  validateTicket(
    { legs, passTypes: [`${passSize}x1` as PassType], multiplier },
    rules,
  );
}

export function calcCombinations(
  legs: readonly TicketLeg[],
  passSize: number,
  multiplier = 1,
  rules: SportteryRules = DEFAULT_SPORTTERY_RULES,
): TicketResult {
  validateCombo(legs, passSize, multiplier, rules);
  const result = calculateTicket(
    { legs, passTypes: [`${passSize}x1` as PassType], multiplier },
    rules,
  );
  return {
    betCount: result.betCount,
    amount: result.amount,
    maximumBonus: result.maximumBonus,
    effectiveCombinationCount: result.betCount,
  };
}
