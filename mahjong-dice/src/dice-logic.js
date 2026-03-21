/**
 * @file dice-logic.js
 * @description Entity層 — サイコロのドメインロジック（純粋関数）
 * テスト用にES Modulesとしてexport。本番用index.htmlには同一ロジックをインライン化。
 */

/**
 * @typedef {{ face_value_1: number, face_value_2: number, total: number }} RollResult
 */

/**
 * サイコロの出目に対応する pip（ドット）の位置を返す。
 * 3x3グリッドの位置: 0=左上, 1=上中, 2=右上, 3=左中, 4=中央, 5=右中, 6=左下, 7=下中, 8=右下
 * @param {number} faceValue - 出目（1〜6）
 * @returns {number[]} pip が表示される位置のインデックス配列
 */
export function pipPositionsForFace(faceValue) {
  const pipMap = {
    1: [4],
    2: [2, 6],
    3: [2, 4, 6],
    4: [0, 2, 6, 8],
    5: [0, 2, 4, 6, 8],
    6: [0, 2, 3, 5, 6, 8],
  };
  return pipMap[faceValue] || [];
}

/**
 * 出目に応じた pip の色を返す。麻雀サイコロでは1の目が赤。
 * @param {number} faceValue - 出目（1〜6）
 * @returns {string} 色名（"red" または "black"）
 */
export function getPipColor(faceValue) {
  return faceValue === 1 ? 'red' : 'black';
}

/**
 * 1〜6 のランダムな整数を返す。
 * @returns {number}
 */
export function rollSingleDice() {
  return Math.floor(Math.random() * 6) + 1;
}

/**
 * サイコロ2個を振り、結果を返す。
 * @returns {RollResult}
 */
export function rollPair() {
  const faceValue1 = rollSingleDice();
  const faceValue2 = rollSingleDice();
  return {
    face_value_1: faceValue1,
    face_value_2: faceValue2,
    total: faceValue1 + faceValue2,
  };
}

/**
 * 2個の出目の合計を計算する。
 * @param {number} faceValue1 - サイコロ1の出目
 * @param {number} faceValue2 - サイコロ2の出目
 * @returns {number} 合計値
 */
export function calculateTotal(faceValue1, faceValue2) {
  return faceValue1 + faceValue2;
}

/**
 * 出目に対応する3D回転角度を返す。
 * 標準サイコロ面配置: 正面=1, 背面=6, 右=3, 左=4, 上=2, 下=5
 * @param {number} faceValue - 出目（1〜6）
 * @returns {{ x: number, y: number }} 回転角度（度）
 */
export function rotationForFace(faceValue) {
  const rotations = {
    1: { x: 0, y: 0 },
    2: { x: -90, y: 0 },
    3: { x: 0, y: -90 },
    4: { x: 0, y: 90 },
    5: { x: 90, y: 0 },
    6: { x: 0, y: 180 },
  };
  return rotations[faceValue] || { x: 0, y: 0 };
}

/**
 * easeOutBounce イージング関数。
 * @param {number} t - 進行度（0〜1）
 * @returns {number} イージング適用後の値
 */
export function easeOutBounce(t) {
  if (t < 1 / 2.75) {
    return 7.5625 * t * t;
  } else if (t < 2 / 2.75) {
    t -= 1.5 / 2.75;
    return 7.5625 * t * t + 0.75;
  } else if (t < 2.5 / 2.75) {
    t -= 2.25 / 2.75;
    return 7.5625 * t * t + 0.9375;
  } else {
    t -= 2.625 / 2.75;
    return 7.5625 * t * t + 0.984375;
  }
}
