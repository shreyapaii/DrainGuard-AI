from drainguard import public_data
from drainguard.db import connect, infrastructure_counts, list_infrastructure_records


def make_conn(tmp_path):
    return connect(str(tmp_path / "test.db"))


def test_feature_point_uses_only_source_coordinates():
    assert public_data._feature_point({"x": 72.8, "y": 19.0}) == (19.0, 72.8)
    assert public_data._feature_point({"paths": [[[72.8, 19.0], [72.9, 19.1]]]}) == (19.0, 72.8)
    assert public_data._feature_point(None) == (None, None)


def test_import_mcgmgis_stormwater_with_mocked_real_shape(monkeypatch, tmp_path):
    conn = make_conn(tmp_path)

    def fake_service():
        return {
            "serviceDescription": "All Department GIS Layers",
            "copyrightText": "MCGM, Esri India",
        }

    def fake_layer(layer_id):
        if layer_id == public_data.MCGM_STORM_DRAINS_LAYER_ID:
            return {
                "name": "Storm Water Drains",
                "geometryType": "esriGeometryPolyline",
                "fields": [{"name": "OBJECTID", "type": "esriFieldTypeOID", "alias": "FID"}],
                "extent": {"spatialReference": {"wkid": 32643}},
            }
        return {
            "name": "Storm Water Manholes",
            "geometryType": "esriGeometryPoint",
            "fields": [{"name": "OBJECTID", "type": "esriFieldTypeOID", "alias": "FID"}],
            "extent": {"spatialReference": {"wkid": 32643}},
        }

    def fake_count(layer_id):
        return 1

    def fake_features(layer_id, *, limit, page_size=1000):
        if layer_id == public_data.MCGM_STORM_DRAINS_LAYER_ID:
            return [{
                "attributes": {
                    "OBJECTID": 1,
                    "US_NODE_ID": "1!!!",
                    "DS_NODE_ID": "2!!!",
                    "CONDUIT_LE": 8.2,
                },
                "geometry": {"paths": [[[72.83909123398863, 19.06393970003224],
                                         [72.83916917643138, 19.063936097133496]]]},
            }]
        return [{
            "attributes": {"OBJECTID": 2, "NODE_ID": "1", "GROUND_LEV": 28.6},
            "geometry": {"x": 72.85677260087633, "y": 19.063947337680972},
        }]

    monkeypatch.setattr(public_data, "get_mcgmgis_service_metadata", fake_service)
    monkeypatch.setattr(public_data, "get_mcgmgis_layer_metadata", fake_layer)
    monkeypatch.setattr(public_data, "get_mcgmgis_count", fake_count)
    monkeypatch.setattr(public_data, "query_mcgmgis_features", fake_features)
    monkeypatch.setattr(public_data, "utc_now", lambda: "2026-10-09T00:00:00+00:00")

    summary = public_data.import_mcgmgis_stormwater(conn, limit_per_layer=10)
    duplicate = public_data.import_mcgmgis_stormwater(conn, limit_per_layer=10)

    assert summary.inserted == 2
    assert duplicate.inserted == 0
    assert duplicate.duplicates == 2
    assert infrastructure_counts(conn) == {
        public_data.RECORD_TYPE_STORM_DRAIN: 1,
        public_data.RECORD_TYPE_STORM_MANHOLE: 1,
    }
    rows = list_infrastructure_records(conn)
    assert {row["record_type"] for row in rows} == {
        public_data.RECORD_TYPE_STORM_DRAIN,
        public_data.RECORD_TYPE_STORM_MANHOLE,
    }
