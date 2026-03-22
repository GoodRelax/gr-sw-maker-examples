import { describe, it, expect } from 'vitest';
import { createEarthquakeEvent, parseGeoJSON } from '../../src/domain/earthquake-model.js';

const SAMPLE_FEATURE = {
  id: 'us7000abc1',
  properties: {
    mag: 5.2,
    place: '10km NE of Tokyo, Japan',
    time: 1711100000000,
    url: 'https://earthquake.usgs.gov/earthquakes/eventpage/us7000abc1',
  },
  geometry: {
    coordinates: [139.75, 35.68, 10.5],
  },
};

describe('createEarthquakeEvent', () => {
  it('maps all fields from a USGS GeoJSON feature', () => {
    const event = createEarthquakeEvent(SAMPLE_FEATURE);
    expect(event.earthquake_id).toBe('us7000abc1');
    expect(event.magnitude).toBe(5.2);
    expect(event.location_name).toBe('10km NE of Tokyo, Japan');
    expect(event.depth_km).toBe(10.5);
    expect(event.event_time_utc).toEqual(new Date(1711100000000));
    expect(event.latitude).toBe(35.68);
    expect(event.longitude).toBe(139.75);
    expect(event.usgs_detail_url).toBe(
      'https://earthquake.usgs.gov/earthquakes/eventpage/us7000abc1'
    );
  });

  it('defaults location_name to Unknown location when place is null', () => {
    const feature = {
      ...SAMPLE_FEATURE,
      properties: { ...SAMPLE_FEATURE.properties, place: null },
    };
    const event = createEarthquakeEvent(feature);
    expect(event.location_name).toBe('Unknown location');
  });
});

describe('parseGeoJSON', () => {
  it('parses a valid GeoJSON response', () => {
    const geojson = {
      metadata: { count: 1 },
      features: [SAMPLE_FEATURE],
    };
    const { events, metadata_count } = parseGeoJSON(geojson);
    expect(events).toHaveLength(1);
    expect(metadata_count).toBe(1);
    expect(events[0].earthquake_id).toBe('us7000abc1');
  });

  it('throws on invalid GeoJSON (missing features)', () => {
    expect(() => parseGeoJSON({})).toThrow('Invalid GeoJSON');
    expect(() => parseGeoJSON(null)).toThrow('Invalid GeoJSON');
  });

  it('uses events.length when metadata.count is missing', () => {
    const geojson = {
      features: [SAMPLE_FEATURE, SAMPLE_FEATURE],
    };
    const { metadata_count } = parseGeoJSON(geojson);
    expect(metadata_count).toBe(2);
  });
});
