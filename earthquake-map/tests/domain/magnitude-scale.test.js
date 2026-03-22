import { describe, it, expect } from 'vitest';
import { magnitudeToRadius, magnitudeToColor } from '../../src/domain/magnitude-scale.js';

describe('magnitudeToRadius', () => {
  it('returns 4 for magnitude below 3.0', () => {
    expect(magnitudeToRadius(0)).toBe(4);
    expect(magnitudeToRadius(1.5)).toBe(4);
    expect(magnitudeToRadius(2.9)).toBe(4);
  });

  it('returns 7 for magnitude 3.0 to 4.9', () => {
    expect(magnitudeToRadius(3.0)).toBe(7);
    expect(magnitudeToRadius(4.5)).toBe(7);
    expect(magnitudeToRadius(4.9)).toBe(7);
  });

  it('returns 11 for magnitude 5.0 to 6.9', () => {
    expect(magnitudeToRadius(5.0)).toBe(11);
    expect(magnitudeToRadius(6.5)).toBe(11);
    expect(magnitudeToRadius(6.9)).toBe(11);
  });

  it('returns 16 for magnitude 7.0 and above', () => {
    expect(magnitudeToRadius(7.0)).toBe(16);
    expect(magnitudeToRadius(9.0)).toBe(16);
  });
});

describe('magnitudeToColor', () => {
  it('returns green (#00CC00) for magnitude below 3.0', () => {
    expect(magnitudeToColor(0)).toBe('#00CC00');
    expect(magnitudeToColor(2.9)).toBe('#00CC00');
  });

  it('returns yellow (#CCCC00) for magnitude 3.0 to 4.9', () => {
    expect(magnitudeToColor(3.0)).toBe('#CCCC00');
    expect(magnitudeToColor(4.9)).toBe('#CCCC00');
  });

  it('returns orange (#FF8800) for magnitude 5.0 to 6.9', () => {
    expect(magnitudeToColor(5.0)).toBe('#FF8800');
    expect(magnitudeToColor(6.9)).toBe('#FF8800');
  });

  it('returns red (#CC0000) for magnitude 7.0 and above', () => {
    expect(magnitudeToColor(7.0)).toBe('#CC0000');
    expect(magnitudeToColor(9.5)).toBe('#CC0000');
  });
});
