import { describe, it, expect, vi } from 'vitest';
import {
  pipPositionsForFace,
  getPipColor,
  rollSingleDice,
  rollPair,
  calculateTotal,
  rotationForFace,
  easeOutBounce,
} from '../src/dice-logic.js';

describe('pipPositionsForFace', () => {
  it('出目1: 中央のみ', () => {
    expect(pipPositionsForFace(1)).toEqual([4]);
  });

  it('出目2: 右上と左下', () => {
    expect(pipPositionsForFace(2)).toEqual([2, 6]);
  });

  it('出目3: 右上、中央、左下', () => {
    expect(pipPositionsForFace(3)).toEqual([2, 4, 6]);
  });

  it('出目4: 四隅', () => {
    expect(pipPositionsForFace(4)).toEqual([0, 2, 6, 8]);
  });

  it('出目5: 四隅と中央', () => {
    expect(pipPositionsForFace(5)).toEqual([0, 2, 4, 6, 8]);
  });

  it('出目6: 左右3つずつ', () => {
    expect(pipPositionsForFace(6)).toEqual([0, 2, 3, 5, 6, 8]);
  });

  it('範囲外の出目は空配列', () => {
    expect(pipPositionsForFace(0)).toEqual([]);
    expect(pipPositionsForFace(7)).toEqual([]);
    expect(pipPositionsForFace(-1)).toEqual([]);
  });

  it('pip数が出目の値と一致する', () => {
    for (let face = 1; face <= 6; face++) {
      expect(pipPositionsForFace(face)).toHaveLength(face);
    }
  });
});

describe('getPipColor', () => {
  it('出目1は赤', () => {
    expect(getPipColor(1)).toBe('red');
  });

  it('出目2〜6は黒', () => {
    for (let face = 2; face <= 6; face++) {
      expect(getPipColor(face)).toBe('black');
    }
  });
});

describe('rollSingleDice', () => {
  it('1〜6の整数を返す', () => {
    for (let i = 0; i < 100; i++) {
      const result = rollSingleDice();
      expect(result).toBeGreaterThanOrEqual(1);
      expect(result).toBeLessThanOrEqual(6);
      expect(Number.isInteger(result)).toBe(true);
    }
  });

  it('Math.random()の境界値で正しく動作する', () => {
    const mockRandom = vi.spyOn(Math, 'random');

    mockRandom.mockReturnValue(0);
    expect(rollSingleDice()).toBe(1);

    mockRandom.mockReturnValue(0.999999);
    expect(rollSingleDice()).toBe(6);

    mockRandom.mockReturnValue(0.5);
    expect(rollSingleDice()).toBe(4);

    mockRandom.mockRestore();
  });
});

describe('rollPair', () => {
  it('face_value_1, face_value_2, total を持つオブジェクトを返す', () => {
    const result = rollPair();
    expect(result).toHaveProperty('face_value_1');
    expect(result).toHaveProperty('face_value_2');
    expect(result).toHaveProperty('total');
  });

  it('各出目が1〜6の整数', () => {
    for (let i = 0; i < 100; i++) {
      const result = rollPair();
      expect(result.face_value_1).toBeGreaterThanOrEqual(1);
      expect(result.face_value_1).toBeLessThanOrEqual(6);
      expect(result.face_value_2).toBeGreaterThanOrEqual(1);
      expect(result.face_value_2).toBeLessThanOrEqual(6);
    }
  });

  it('totalがface_value_1 + face_value_2と一致する', () => {
    for (let i = 0; i < 100; i++) {
      const result = rollPair();
      expect(result.total).toBe(result.face_value_1 + result.face_value_2);
    }
  });

  it('合計値の範囲は2〜12', () => {
    for (let i = 0; i < 100; i++) {
      const result = rollPair();
      expect(result.total).toBeGreaterThanOrEqual(2);
      expect(result.total).toBeLessThanOrEqual(12);
    }
  });
});

describe('calculateTotal', () => {
  it('2つの出目の合計を返す', () => {
    expect(calculateTotal(1, 1)).toBe(2);
    expect(calculateTotal(6, 6)).toBe(12);
    expect(calculateTotal(3, 4)).toBe(7);
  });
});

describe('rotationForFace', () => {
  it('各出目に対して回転角度を返す', () => {
    expect(rotationForFace(1)).toEqual({ x: 0, y: 0 });
    expect(rotationForFace(2)).toEqual({ x: -90, y: 0 });
    expect(rotationForFace(3)).toEqual({ x: 0, y: -90 });
    expect(rotationForFace(4)).toEqual({ x: 0, y: 90 });
    expect(rotationForFace(5)).toEqual({ x: 90, y: 0 });
    expect(rotationForFace(6)).toEqual({ x: 0, y: 180 });
  });

  it('範囲外の出目はデフォルト値', () => {
    expect(rotationForFace(0)).toEqual({ x: 0, y: 0 });
    expect(rotationForFace(7)).toEqual({ x: 0, y: 0 });
  });

  it('対面のy回転の差が180度', () => {
    // 1(front)と6(back)は対面
    const rot1 = rotationForFace(1);
    const rot6 = rotationForFace(6);
    expect(Math.abs(rot6.y - rot1.y)).toBe(180);
  });
});

describe('easeOutBounce', () => {
  it('t=0で0を返す', () => {
    expect(easeOutBounce(0)).toBe(0);
  });

  it('t=1で1を返す', () => {
    expect(easeOutBounce(1)).toBeCloseTo(1, 5);
  });

  it('0〜1の範囲で0以上1以下を返す', () => {
    for (let i = 0; i <= 10; i++) {
      const t = i / 10;
      const result = easeOutBounce(t);
      expect(result).toBeGreaterThanOrEqual(0);
      expect(result).toBeLessThanOrEqual(1.001);
    }
  });

  it('単調非減少（大まかに）', () => {
    let prev = 0;
    // バウンスなのでローカルな非単調性はあるが、0.5以降は概ね増加
    for (let i = 5; i <= 10; i++) {
      const t = i / 10;
      const result = easeOutBounce(t);
      expect(result).toBeGreaterThanOrEqual(prev - 0.05);
      prev = result;
    }
  });
});
