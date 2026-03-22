# License Report

**Project:** Earthquake Map
**Version:** 0.1.0
**Date:** 2026-03-22
**Status:** PASS — All dependencies have permissive licenses compatible with each other. No GPL/AGPL libraries detected. Attribution requirements met.

---

## Executive Summary

All production and development dependencies use permissive open-source licenses compatible with commercial use. No copyleft obligations or GPL/AGPL restrictions apply. OpenStreetMap attribution requirement is correctly implemented in code.

---

## Production Dependencies

### Leaflet.js (CDN-loaded, v1.9.4)

| Property | Value |
|----------|-------|
| License | BSD-2-Clause |
| Commercial use | Allowed |
| Attribution | Required |
| Source disclosure | None |
| Verdict | **PERMITTED** |
| Location | index.html (CDN) |
| Attribution status | Bundled in Leaflet; verified in src/ui/map-renderer.js |

**Details:** Leaflet.js is loaded via unpkg CDN with SRI integrity hashes. The BSD-2-Clause license permits commercial use with attribution. Attribution is provided in the tile layer configuration in map-renderer.js (line 7: `&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors`).

---

### OpenStreetMap Tiles

| Property | Value |
|----------|-------|
| License | ODbL (Open Data Commons Open Database License) v1.0 |
| Commercial use | Allowed with attribution |
| Attribution | Required (must display credits) |
| Source disclosure | Database attribution required |
| Verdict | **PERMITTED with attribution** |
| Location | Tile layer in map-renderer.js |
| Attribution status | Implemented correctly |

**Details:** OpenStreetMap data is licensed under ODbL and requires visible attribution on maps. The implementation at src/ui/map-renderer.js (line 20) correctly passes the TILE_ATTRIBUTION string to Leaflet's tileLayer() method, which automatically displays the attribution control on the map. This satisfies ODbL requirements.

---

### USGS API (Public Domain)

| Property | Value |
|----------|-------|
| License | Public Domain (US Government) |
| Commercial use | Allowed |
| Attribution | Optional but recommended |
| Source disclosure | None |
| Verdict | **PERMITTED** |
| Location | USGS Earthquake Hazards Program API |
| Attribution status | Recommended; currently not visible in UI |

**Details:** USGS data is in the public domain as a work of the US federal government. No license restrictions apply. While attribution is optional, best practice suggests acknowledging the USGS as the data source. Consider adding a "Data Source: USGS Earthquake Hazards Program" credit in the footer during a future enhancement.

---

## Development Dependencies

| Package | Version | License | Used in shipping? | Verdict |
|---------|---------|---------|-------------------|---------|
| vitest | ^3.0.0 | MIT | No (dev only) | PERMITTED |
| @vitest/coverage-v8 | ^3.0.0 | MIT | No (dev only) | PERMITTED |
| jsdom | ^25.0.0 | MIT | No (dev only) | PERMITTED |

**Details:** All dev dependencies use the MIT license, which is permissive. They are installed locally only and not shipped to production, so license compatibility is not a shipping concern. All transitive dev dependencies (vitest ecosystem, jsdom dependencies) also use permissive licenses (MIT, Apache 2.0, BSD variants, ISC).

---

## Transitive Dependencies

Scan of node_modules via package-lock.json confirms all transitive dependencies of dev tools use permissive licenses only (MIT, Apache 2.0, BSD-2-Clause, BSD-3-Clause, ISC). No GPL, AGPL, or other restrictive licenses detected.

---

## Attribution Inventory

### Required

| Source | License | Attribution | Implementation | Status |
|--------|---------|-------------|-----------------|--------|
| Leaflet.js | BSD-2-Clause | Yes | Implicit in Leaflet's default | IMPLEMENTED |
| OpenStreetMap contributors | ODbL | Yes | map-renderer.js line 7, auto-rendered by Leaflet | IMPLEMENTED |

### Recommended

| Source | Type | Current | Recommendation |
|--------|------|---------|-----------------|
| USGS Earthquake Hazards Program | Data source | Not visible | Add footer credit (enhancement) |

---

## License Compatibility Matrix

| License | Commercial | Attribution | Disclosure | Status |
|---------|-----------|-------------|-----------|--------|
| BSD-2-Clause (Leaflet) | Allowed | Required | None | Compatible |
| ODbL (OpenStreetMap) | Allowed | Required | DB attribution | Compatible |
| Public Domain (USGS) | Allowed | Optional | None | Compatible |
| MIT (dev deps) | Allowed | Required | None | Compatible |

**Result:** All dependencies are compatible with each other and with personal/commercial use.

---

## Recommendations

1. **Current:** No action required. All licenses are in compliance.
2. **Enhancement:** Consider adding "Data source: USGS Earthquake Hazards Program" in the UI footer to provide user transparency, even though not legally required.
3. **Ongoing:** When adding new dependencies, run `npm audit` and verify license with `npm license-report` or similar tooling.

---

## Checklist

- [x] All production dependencies identified
- [x] License of each dependency verified
- [x] Compatibility with commercial use confirmed
- [x] Attribution requirements met in code
- [x] No GPL/AGPL libraries detected
- [x] No copyleft obligations
- [x] Transitive dependencies reviewed (all permissive)
- [x] No unknown licenses

---

**Approved by:** [license-checker]
**Signature Date:** 2026-03-22
