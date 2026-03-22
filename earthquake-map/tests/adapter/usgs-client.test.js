import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { buildQueryURL, fetchEarthquakes } from '../../src/adapter/usgs-client.js';

describe('buildQueryURL', () => {
  it('constructs a valid USGS API URL', () => {
    const filter = {
      start_date: new Date('2026-03-01T00:00:00Z'),
      end_date: new Date('2026-03-15T23:59:59Z'),
      minimum_magnitude: 4.5,
    };
    const url = buildQueryURL(filter);
    expect(url).toContain('https://earthquake.usgs.gov/fdsnws/event/1/query?');
    expect(url).toContain('format=geojson');
    expect(url).toContain('starttime=2026-03-01');
    expect(url).toContain('endtime=2026-03-15');
    expect(url).toContain('minmagnitude=4.5');
    expect(url).toContain('limit=20000');
    expect(url).toContain('orderby=time');
  });

  it('uses HTTPS protocol', () => {
    const filter = {
      start_date: new Date('2026-03-01T00:00:00Z'),
      end_date: new Date('2026-03-15T23:59:59Z'),
      minimum_magnitude: 1.0,
    };
    const url = buildQueryURL(filter);
    expect(url.startsWith('https://')).toBe(true);
  });
});

describe('fetchEarthquakes', () => {
  const SAMPLE_GEOJSON = {
    metadata: { count: 2 },
    features: [
      {
        id: 'eq1',
        properties: { mag: 3.1, place: 'Place A', time: 1711100000000, url: 'https://usgs.gov/eq1' },
        geometry: { coordinates: [100.0, 13.0, 5.0] },
      },
      {
        id: 'eq2',
        properties: { mag: 6.5, place: 'Place B', time: 1711200000000, url: 'https://usgs.gov/eq2' },
        geometry: { coordinates: [-118.0, 34.0, 15.0] },
      },
    ],
  };

  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns parsed events on success', async () => {
    fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(SAMPLE_GEOJSON),
    });

    const filter = {
      start_date: new Date('2026-03-01'),
      end_date: new Date('2026-03-15'),
      minimum_magnitude: 1.0,
    };
    const result = await fetchEarthquakes(filter);
    expect(result.events).toHaveLength(2);
    expect(result.metadata_count).toBe(2);
    expect(result.is_capped).toBe(false);
    expect(result.events[0].earthquake_id).toBe('eq1');
  });

  it('throws on HTTP error', async () => {
    fetch.mockResolvedValue({
      ok: false,
      status: 400,
    });

    const filter = {
      start_date: new Date('2026-03-01'),
      end_date: new Date('2026-03-15'),
      minimum_magnitude: 1.0,
    };
    await expect(fetchEarthquakes(filter)).rejects.toThrow('HTTP 400');
  });

  it('throws on unparseable response', async () => {
    fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.reject(new SyntaxError('bad json')),
    });

    const filter = {
      start_date: new Date('2026-03-01'),
      end_date: new Date('2026-03-15'),
      minimum_magnitude: 1.0,
    };
    await expect(fetchEarthquakes(filter)).rejects.toThrow('unparseable');
  });

  it('supports cancellation via AbortSignal', async () => {
    const abort_controller = new AbortController();
    fetch.mockImplementation(() => {
      abort_controller.abort();
      return Promise.reject(new DOMException('aborted', 'AbortError'));
    });

    const filter = {
      start_date: new Date('2026-03-01'),
      end_date: new Date('2026-03-15'),
      minimum_magnitude: 1.0,
    };
    await expect(fetchEarthquakes(filter, abort_controller.signal)).rejects.toThrow('cancelled');
  });

  it('reports is_capped when count reaches limit', async () => {
    const capped_geojson = {
      ...SAMPLE_GEOJSON,
      metadata: { count: 20000 },
    };
    fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(capped_geojson),
    });

    const filter = {
      start_date: new Date('2026-03-01'),
      end_date: new Date('2026-03-15'),
      minimum_magnitude: 0.0,
    };
    const result = await fetchEarthquakes(filter);
    expect(result.is_capped).toBe(true);
  });
});
