import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { fromPreset, isValid, toUSGSParams, getPresetKeys } from '../../src/domain/date-range.js';

describe('fromPreset', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-03-22T12:00:00Z'));
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns a 1-hour range for "1h"', () => {
    const { start_date, end_date } = fromPreset('1h');
    expect(end_date.getTime() - start_date.getTime()).toBe(60 * 60 * 1000);
  });

  it('returns a 24-hour range for "24h"', () => {
    const { start_date, end_date } = fromPreset('24h');
    expect(end_date.getTime() - start_date.getTime()).toBe(24 * 60 * 60 * 1000);
  });

  it('returns a 7-day range for "7d"', () => {
    const { start_date, end_date } = fromPreset('7d');
    expect(end_date.getTime() - start_date.getTime()).toBe(7 * 24 * 60 * 60 * 1000);
  });

  it('returns a 30-day range for "30d"', () => {
    const { start_date, end_date } = fromPreset('30d');
    expect(end_date.getTime() - start_date.getTime()).toBe(30 * 24 * 60 * 60 * 1000);
  });

  it('throws for unknown preset', () => {
    expect(() => fromPreset('99d')).toThrow('Unknown preset');
  });
});

describe('isValid', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-03-22T12:00:00Z'));
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns valid for a proper date range', () => {
    const result = isValid(new Date('2026-03-01'), new Date('2026-03-20'));
    expect(result.valid).toBe(true);
    expect(result.error_message).toBeNull();
  });

  it('rejects end date before start date', () => {
    const result = isValid(new Date('2026-03-20'), new Date('2026-03-01'));
    expect(result.valid).toBe(false);
    expect(result.error_message).toContain('precede');
  });

  it('rejects future end date', () => {
    const result = isValid(new Date('2026-03-01'), new Date('2026-03-25'));
    expect(result.valid).toBe(false);
    expect(result.error_message).toContain('future');
  });

  it('rejects invalid start date', () => {
    const result = isValid(new Date('invalid'), new Date('2026-03-20'));
    expect(result.valid).toBe(false);
    expect(result.error_message).toContain('Invalid start date');
  });

  it('rejects invalid end date', () => {
    const result = isValid(new Date('2026-03-01'), new Date('invalid'));
    expect(result.valid).toBe(false);
    expect(result.error_message).toContain('Invalid end date');
  });
});

describe('toUSGSParams', () => {
  it('converts dates to ISO strings', () => {
    const start = new Date('2026-03-01T00:00:00Z');
    const end = new Date('2026-03-15T23:59:59Z');
    const params = toUSGSParams(start, end);
    expect(params.starttime).toBe('2026-03-01T00:00:00.000Z');
    expect(params.endtime).toBe('2026-03-15T23:59:59.000Z');
  });
});

describe('getPresetKeys', () => {
  it('returns all available preset keys', () => {
    const keys = getPresetKeys();
    expect(keys).toEqual(['1h', '24h', '7d', '30d']);
  });
});
