import os
from types import SimpleNamespace

import numpy as np
import pytest
from osgeo import gdal
from qgis.core import QgsCoordinateReferenceSystem, QgsProject, QgsRasterLayer, QgsRasterRange
from qgis.gui import QgsMapLayerComboBox

from AcATaMa.core import map as core_map
from AcATaMa.core.map import (
    Map,
    auto_symbology_classification_render,
    get_map_fingerprint,
    get_user_nodata_ranges,
    get_valid_pixel_counts,
    in_nodata_ranges,
)
from AcATaMa.utils import others_utils
from AcATaMa.utils.others_utils import (
    get_nodata_format,
    get_pixel_count_by_pixel_values,
    get_pixel_count_by_pixel_values_parallel,
    get_pixel_count_by_pixel_values_qgis_native,
    get_pixel_count_by_pixel_values_sequential,
)
from AcATaMa.utils.qgis_utils import load_layer


@pytest.fixture
def qgis_processing():
    """Register the QGIS native processing algorithms, as in the QGIS desktop application"""
    pytest.importorskip("processing")
    from processing.core.Processing import Processing
    from qgis.analysis import QgsNativeAlgorithms
    from qgis.core import QgsApplication

    Processing.initialize()
    if QgsApplication.processingRegistry().providerById("native") is None:
        QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())


def test_pixel_count_without_dask_uses_qgis_native(monkeypatch):
    # Given: Dask is unavailable and QGIS native counting can produce a result
    layer = object()
    expected_pixel_count = {1: 2}
    others_utils.storage_pixel_count_by_pixel_values.clear()
    monkeypatch.setattr(others_utils, "dask_is_available", lambda: False)
    monkeypatch.setattr(
        others_utils,
        "get_pixel_count_by_pixel_values_parallel",
        lambda _layer, _band, _pixel_values, _nodata: pytest.fail("Dask path must be skipped"),
    )
    monkeypatch.setattr(
        others_utils,
        "get_pixel_count_by_pixel_values_qgis_native",
        lambda _layer, _band, _pixel_values, _nodata: expected_pixel_count,
    )
    monkeypatch.setattr(
        others_utils,
        "get_pixel_count_by_pixel_values_sequential",
        lambda _layer, _band, _pixel_values, _nodata: pytest.fail("Sequential path must not be needed"),
    )

    # When: pixel counts are requested through the dispatcher
    pixel_count = others_utils.get_pixel_count_by_pixel_values(layer, band=1)

    # Then: the QGIS native result is returned without touching Dask
    assert pixel_count == expected_pixel_count


def test_pixel_count_without_dask_falls_back_to_sequential_when_native_fails(monkeypatch):
    # Given: Dask is unavailable and QGIS native counting returns no result
    layer = object()
    expected_pixel_count = {1: 2}
    others_utils.storage_pixel_count_by_pixel_values.clear()
    monkeypatch.setattr(others_utils, "dask_is_available", lambda: False)
    monkeypatch.setattr(
        others_utils,
        "get_pixel_count_by_pixel_values_qgis_native",
        lambda _layer, _band, _pixel_values, _nodata: None,
    )
    monkeypatch.setattr(
        others_utils,
        "get_pixel_count_by_pixel_values_sequential",
        lambda _layer, _band, _pixel_values, _nodata: expected_pixel_count,
    )

    # When: pixel counts are requested through the dispatcher
    pixel_count = others_utils.get_pixel_count_by_pixel_values(layer, band=1)

    # Then: the sequential result is returned
    assert pixel_count == expected_pixel_count


def test_pixel_count_without_nodata_sequential(plugin, restore_config_file):
    # restore
    input_yml_path = pytest.tests_data_dir / "test_pixel_count_acatama.yaml"
    restore_config_file(input_yml_path)

    pixel_count = get_pixel_count_by_pixel_values_sequential(
        plugin.dockwidget.QCBox_ThematicMap.currentLayer(), band=2, nodata=None
    )

    assert pixel_count == {
        0: 3227,
        34: 11,
        35: 44,
        36: 22,
        37: 49,
        38: 17,
        40: 2,
        42: 1,
        43: 1,
        44: 79,
        45: 5,
        46: 468,
        47: 57,
        49: 3,
        51: 1,
        52: 15,
        53: 24,
    }


def test_pixel_count_without_nodata_parallel(plugin, restore_config_file):
    # restore
    input_yml_path = pytest.tests_data_dir / "test_pixel_count_acatama.yaml"
    restore_config_file(input_yml_path)

    pixel_count = get_pixel_count_by_pixel_values_parallel(
        plugin.dockwidget.QCBox_ThematicMap.currentLayer(), band=2, nodata=None
    )

    assert pixel_count == {
        0: 3227,
        34: 11,
        35: 44,
        36: 22,
        37: 49,
        38: 17,
        40: 2,
        42: 1,
        43: 1,
        44: 79,
        45: 5,
        46: 468,
        47: 57,
        49: 3,
        51: 1,
        52: 15,
        53: 24,
    }


def test_pixel_count_without_nodata_qgis_native(plugin, restore_config_file, qgis_processing):
    # restore
    input_yml_path = pytest.tests_data_dir / "test_pixel_count_acatama.yaml"
    restore_config_file(input_yml_path)

    pixel_count = get_pixel_count_by_pixel_values_qgis_native(
        plugin.dockwidget.QCBox_ThematicMap.currentLayer(), band=2, nodata=None
    )

    assert pixel_count == {
        0: 3227,
        34: 11,
        35: 44,
        36: 22,
        37: 49,
        38: 17,
        40: 2,
        42: 1,
        43: 1,
        44: 79,
        45: 5,
        46: 468,
        47: 57,
        49: 3,
        51: 1,
        52: 15,
        53: 24,
    }


def test_pixel_count_with_nodata_sequential(plugin, restore_config_file):
    # restore
    input_yml_path = pytest.tests_data_dir / "test_pixel_count_acatama_nodata.yaml"
    restore_config_file(input_yml_path)
    sampling_design = plugin.dockwidget.sampling_design_window

    pixel_count = get_pixel_count_by_pixel_values_sequential(
        plugin.dockwidget.QCBox_ThematicMap.currentLayer(),
        band=int(sampling_design.QCBox_band_SamplingMap_StraRS.currentText()),
        nodata=get_nodata_format(sampling_design.nodata_SamplingMap_StraRS.text()),
    )

    assert pixel_count == {1: 10423, 2: 418, 5: 8822}


def test_pixel_count_with_nodata_parallel(plugin, restore_config_file):
    # restore
    input_yml_path = pytest.tests_data_dir / "test_pixel_count_acatama_nodata.yaml"
    restore_config_file(input_yml_path)
    sampling_design = plugin.dockwidget.sampling_design_window

    pixel_count = get_pixel_count_by_pixel_values_parallel(
        plugin.dockwidget.QCBox_ThematicMap.currentLayer(),
        band=int(sampling_design.QCBox_band_SamplingMap_StraRS.currentText()),
        nodata=get_nodata_format(sampling_design.nodata_SamplingMap_StraRS.text()),
    )

    assert pixel_count == {1: 10423, 2: 418, 5: 8822}


def test_pixel_count_with_nodata_qgis_native(plugin, restore_config_file, qgis_processing):
    # restore
    input_yml_path = pytest.tests_data_dir / "test_pixel_count_acatama_nodata.yaml"
    restore_config_file(input_yml_path)
    sampling_design = plugin.dockwidget.sampling_design_window

    pixel_count = get_pixel_count_by_pixel_values_qgis_native(
        plugin.dockwidget.QCBox_ThematicMap.currentLayer(),
        band=int(sampling_design.QCBox_band_SamplingMap_StraRS.currentText()),
        nodata=get_nodata_format(sampling_design.nodata_SamplingMap_StraRS.text()),
    )

    assert pixel_count == {1: 10423, 2: 418, 5: 8822}


def test_pixel_count_and_auto_symbology(plugin, tmpdir):
    # copy and unset the nodata
    layer_unsetnodata = tmpdir.join("test_layer_with_nodata.tif")
    gdal.Translate(str(layer_unsetnodata), str(pytest.tests_data_dir / "test_layer_with_nodata.tif"))
    os.system(f"gdal_edit.py '{layer_unsetnodata}' -unsetnodata")

    layer = load_layer(str(layer_unsetnodata))
    auto_symbology_classification_render(layer, 1)
    pixel_count = get_pixel_count_by_pixel_values(layer, band=1, nodata=None)

    assert pixel_count == {-2147483647: 15785, 1: 10423, 2: 418, 5: 8822}


def test_sequential_pixel_count_includes_the_values_not_in_the_symbology(plugin, make_raster, monkeypatch):
    """The population of the analysis has all the pixel values of the map, also the ones without symbology,
    with every counting method"""
    layer = make_raster([[1, 1], [2, 2]], styled_values=[1])
    monkeypatch.setattr(others_utils, "dask_is_available", lambda: False)
    monkeypatch.setattr(others_utils, "get_pixel_count_by_pixel_values_qgis_native", lambda *args: None)
    others_utils.clear_pixel_counts(layer, 1, None)
    combo_box = QgsMapLayerComboBox()
    combo_box.setLayer(layer)

    assert Map(combo_box, band=1).get_pixel_counts() == {1: 2, 2: 2}
    assert get_pixel_count_by_pixel_values_sequential(layer, 1, [1, 3], None) == {1: 2, 2: 2, 3: 0}


def test_restored_pixel_counts_are_counted_again_for_the_population(plugin, make_raster):
    """The pixel counts restored from a configuration only have the values of the symbology"""
    layer = make_raster([[1, 1], [2, 2]], styled_values=[1])
    others_utils.set_pixel_counts(layer, 1, None, {1: 2}, complete=False)

    # enough for the stratified sampling table of the symbology
    assert get_pixel_count_by_pixel_values(layer, 1, [1], None) == {1: 2}
    # but not for the population of the analysis
    assert get_valid_pixel_counts(layer, 1) == {1: 2, 2: 2}
    assert (layer, 1, None) in others_utils.complete_pixel_counts
    assert get_pixel_count_by_pixel_values(layer, 1, [1], None) == {1: 2, 2: 2}

    others_utils.clear_pixel_counts(layer, 1, None)
    assert (layer, 1, None) not in others_utils.storage_pixel_count_by_pixel_values
    assert (layer, 1, None) not in others_utils.complete_pixel_counts


def test_valid_pixel_counts_fail_when_the_pixels_cannot_be_counted(plugin, make_raster, monkeypatch):
    layer = make_raster([[1, 2]])
    monkeypatch.setattr(core_map, "get_pixel_count_by_pixel_values", lambda *args, **kwargs: None)
    with pytest.raises(RuntimeError, match="Failed to count the pixels"):
        get_valid_pixel_counts(layer, 1)


def test_valid_pixels_exclude_the_nodata_of_the_layer(plugin, make_raster):
    """The valid area for the spacing of the systematic sampling is the population of the analysis, also
    without the no data of the layer when the no data of AcATaMa is not set"""
    sampling_design = plugin.dockwidget.sampling_design_window
    layer = make_raster([[0, 0], [0, 1]], nodata=0)
    plugin.dockwidget.QCBox_ThematicMap.setLayer(layer)
    plugin.dockwidget.nodata_ThematicMap.setText("")
    assert sampling_design.get_total_valid_pixels() == 1
    assert get_valid_pixel_counts(layer, 1) == {1: 1}

    layer = make_raster([[0, 0], [0, 1]], name="map without nodata")
    plugin.dockwidget.QCBox_ThematicMap.setLayer(layer)
    plugin.dockwidget.nodata_ThematicMap.setText("")
    assert sampling_design.get_total_valid_pixels() == 4
    plugin.dockwidget.nodata_ThematicMap.setText("0")
    assert sampling_design.get_total_valid_pixels() == 1


def test_stored_pixel_counts_and_fingerprints_follow_the_data_of_the_layer(plugin, make_raster):
    """The stored pixel counts and fingerprints are computed again when the data source of the layer changes"""
    layer = make_raster([[1, 1], [1, 1]], name="before")
    other_layer = make_raster([[2, 2], [1, 2]], name="after")
    assert get_valid_pixel_counts(layer, 1) == {1: 4}
    fingerprint = get_map_fingerprint(layer, 1)

    layer.setDataSource(other_layer.source(), layer.name(), "gdal")
    assert get_valid_pixel_counts(layer, 1) == {1: 1, 2: 3}
    assert get_map_fingerprint(layer, 1) == get_map_fingerprint(other_layer, 1) != fingerprint


def test_map_fingerprint(plugin, make_raster):
    """The fingerprint identifies the pixel values and the georeferencing of the map, not its file or data type"""
    top_bottom, left_right = np.ones((4, 4)), np.ones((4, 4))
    top_bottom[2:, :] = 2
    left_right[:, 2:] = 2
    fingerprint = get_map_fingerprint(make_raster(top_bottom, name="top bottom"), 1)
    # the same pixel counts by value in other places
    assert get_map_fingerprint(make_raster(left_right, name="left right"), 1) != fingerprint
    # a copy with another name and data type
    assert get_map_fingerprint(make_raster(top_bottom, name="copy", data_type=gdal.GDT_UInt16), 1) == fingerprint
    # the same bytes are not the same values
    negative = get_map_fingerprint(make_raster([[-1, 1]], name="int16", data_type=gdal.GDT_Int16), 1)
    assert get_map_fingerprint(make_raster([[65535, 1]], name="uint16", data_type=gdal.GDT_UInt16), 1) != negative
    # custom CRSs (without authority identifier) in other places
    crs_1 = "+proj=tmerc +lat_0=4 +lon_0=-73 +k=1 +x_0=1000000 +y_0=1000000 +ellps=GRS80 +units=m +no_defs"
    crs_2 = "+proj=tmerc +lat_0=4 +lon_0=-77 +k=1 +x_0=1000000 +y_0=1000000 +ellps=GRS80 +units=m +no_defs"
    custom_1 = get_map_fingerprint(make_raster(top_bottom, name="custom 1", crs=crs_1), 1)
    custom_2 = get_map_fingerprint(make_raster(top_bottom, name="custom 2", crs=crs_2), 1)
    assert custom_1 != custom_2
    assert len({fingerprint, custom_1, custom_2}) == 3


def test_stored_pixel_counts_follow_the_nodata_of_the_layer(plugin, make_raster, monkeypatch, qgis_processing):
    """The QGIS native counts exclude the no data of the layer, so they are counted again when it changes"""
    layer = make_raster([[0, 0], [1, 1]], nodata=0, name="with nodata")
    monkeypatch.setattr(others_utils, "dask_is_available", lambda: False)
    assert get_valid_pixel_counts(layer, 1) == {1: 2}
    layer.dataProvider().setUseSourceNoDataValue(1, False)
    assert get_valid_pixel_counts(layer, 1) == {0: 2, 1: 2}


def test_stored_pixel_counts_and_fingerprints_follow_the_files_referenced_by_the_layer(plugin, make_raster, tmp_path):
    """A VRT doesn't change when the files that it references change"""
    source_layer = make_raster([[1, 1], [1, 1]], name="source")
    vrt_path = str(tmp_path / "map.vrt")
    gdal.BuildVRT(vrt_path, [source_layer.source()]).FlushCache()
    layer = QgsRasterLayer(vrt_path, "vrt")
    QgsProject.instance().addMapLayer(layer)
    assert get_valid_pixel_counts(layer, 1) == {1: 4}
    fingerprint = get_map_fingerprint(layer, 1)

    dataset = gdal.Open(source_layer.source(), gdal.GA_Update)
    dataset.GetRasterBand(1).WriteArray(np.array([[1, 2], [2, 2]], dtype=np.uint8))
    dataset = None
    assert get_valid_pixel_counts(layer, 1) == {1: 1, 2: 3}
    assert get_map_fingerprint(layer, 1) != fingerprint


@pytest.mark.parametrize(("authid", "identified_by_definition"), [("USER:100000", True), ("EPSG:32618", False)])
def test_map_fingerprint_with_a_user_crs(plugin, make_raster, authid, identified_by_definition):
    """A user CRS is identified by its definition, which can be changed keeping its identifier (in the user CRS
    database of the profile, so the CRS of the layer is replaced here)"""
    layer = make_raster([[1, 2]], name="user crs")
    fingerprints = []
    for longitude in (-73, -77):
        wkt = QgsCoordinateReferenceSystem.fromProj(f"+proj=tmerc +lat_0=4 +lon_0={longitude} +ellps=GRS80").toWkt()
        layer.crs = lambda wkt=wkt: SimpleNamespace(authid=lambda: authid, toWkt=lambda: wkt)
        fingerprints.append(get_map_fingerprint(layer, 1))
    assert (fingerprints[0] != fingerprints[1]) == identified_by_definition


def test_stored_pixel_counts_and_fingerprints_follow_the_files_of_nested_vrts(plugin, make_raster, tmp_path):
    """The files referenced by a VRT that references another VRT"""
    source_layer = make_raster([[1, 1], [1, 1]], name="source")
    inner_vrt, outer_vrt = str(tmp_path / "inner.vrt"), str(tmp_path / "outer.vrt")
    gdal.BuildVRT(inner_vrt, [source_layer.source()]).FlushCache()
    gdal.BuildVRT(outer_vrt, [inner_vrt]).FlushCache()
    layer = QgsRasterLayer(outer_vrt, "outer vrt")
    QgsProject.instance().addMapLayer(layer)
    assert get_valid_pixel_counts(layer, 1) == {1: 4}
    fingerprint = get_map_fingerprint(layer, 1)

    dataset = gdal.Open(source_layer.source(), gdal.GA_Update)
    dataset.GetRasterBand(1).WriteArray(np.array([[1, 2], [2, 2]], dtype=np.uint8))
    dataset = None
    assert get_valid_pixel_counts(layer, 1) == {1: 1, 2: 3}
    assert get_map_fingerprint(layer, 1) != fingerprint


def test_map_fingerprint_follows_the_georeferencing_of_the_auxiliary_file(plugin, make_raster):
    """With the GDAL PAM enabled, the georeferencing of a raster can be in its auxiliary file"""
    pam_enabled = gdal.GetConfigOption("GDAL_PAM_ENABLED")
    gdal.SetConfigOption("GDAL_PAM_ENABLED", "YES")
    try:
        layer = make_raster([[1, 2], [2, 2]], name="georeferenced by pam")
        fingerprint = get_map_fingerprint(layer, 1)
        with open(layer.source() + ".aux.xml", "w") as aux_file:
            aux_file.write("<PAMDataset><GeoTransform>600000, 1, 0, 1000000, 0, -1</GeoTransform></PAMDataset>")
        assert get_map_fingerprint(layer, 1) != fingerprint
        assert "600000," in get_map_fingerprint(layer, 1)
    finally:
        gdal.SetConfigOption("GDAL_PAM_ENABLED", pam_enabled)


def test_user_nodata_ranges_with_the_semantics_of_the_provider(plugin, make_raster):
    """A no data range whose endpoint is near (not equal) to a class value contains it for the provider"""
    layer = make_raster([[1, 1], [3, 3]], name="user nodata range")
    layer.dataProvider().setUserNoDataValue(1, [QgsRasterRange(1.0000000000000002, 2)])
    assert QgsRasterRange(1.0000000000000002, 2).contains(1)
    assert in_nodata_ranges(1, get_user_nodata_ranges(layer, 1))
    assert get_valid_pixel_counts(layer, 1) == {3: 2}


def test_files_of_the_datasets(plugin, make_raster, tmp_path):
    """All the files of the datasets referenced, also by a VRT named .xml, and None for the web services"""
    source_layer = make_raster([[1, 1], [1, 1]], name="source")
    inner_vrt, outer_vrt = str(tmp_path / "inner.xml"), str(tmp_path / "outer.vrt")
    gdal.BuildVRT(inner_vrt, [source_layer.source()]).FlushCache()
    gdal.BuildVRT(outer_vrt, [inner_vrt]).FlushCache()
    assert {outer_vrt, inner_vrt, source_layer.source()} <= others_utils.get_dataset_files(outer_vrt)

    # a tile service (not contacted to open it) and a VRT that references it
    service = str(tmp_path / "service.xml")
    with open(service, "w") as service_file:
        service_file.write(
            "<GDAL_WMS><Service name='TMS'><ServerUrl>http://127.0.0.1:9/${z}/${x}/${y}.png</ServerUrl></Service>"
            "<DataWindow><UpperLeftX>-20037508.34</UpperLeftX><UpperLeftY>20037508.34</UpperLeftY>"
            "<LowerRightX>20037508.34</LowerRightX><LowerRightY>-20037508.34</LowerRightY><TileLevel>1</TileLevel>"
            "<TileCountX>1</TileCountX><TileCountY>1</TileCountY><YOrigin>top</YOrigin></DataWindow>"
            "<Projection>EPSG:3857</Projection><BlockSizeX>256</BlockSizeX><BlockSizeY>256</BlockSizeY>"
            "<BandsCount>1</BandsCount></GDAL_WMS>"
        )
    assert gdal.Open(service).GetDriver().ShortName == "WMS"
    assert others_utils.get_dataset_files(service) is None
    service_vrt = str(tmp_path / "service.vrt")
    gdal.BuildVRT(service_vrt, [service]).FlushCache()
    assert others_utils.get_dataset_files(service_vrt) is None
    assert others_utils.get_dataset_files("/vsicurl/http://127.0.0.1:9/map.tif") is None


def test_stored_pixel_counts_follow_the_files_of_a_vrt_named_xml(plugin, make_raster, tmp_path):
    source_layer = make_raster([[1, 1], [1, 1]], name="source")
    inner_vrt, outer_vrt = str(tmp_path / "inner.xml"), str(tmp_path / "outer.vrt")
    gdal.BuildVRT(inner_vrt, [source_layer.source()]).FlushCache()
    gdal.BuildVRT(outer_vrt, [inner_vrt]).FlushCache()
    layer = QgsRasterLayer(outer_vrt, "outer vrt")
    QgsProject.instance().addMapLayer(layer)
    assert get_valid_pixel_counts(layer, 1) == {1: 4}
    dataset = gdal.Open(source_layer.source(), gdal.GA_Update)
    dataset.GetRasterBand(1).WriteArray(np.array([[1, 2], [2, 2]], dtype=np.uint8))
    dataset = None
    assert get_valid_pixel_counts(layer, 1) == {1: 1, 2: 3}


def test_datasets_whose_pixel_values_are_not_only_in_their_files(plugin, make_raster, tmp_path):
    """The data of a GeoPackage (e.g. in its WAL file), a Zarr or the datasets that a VRT references by a name that is
    not a file (e.g. a subdataset or a database) can change without changing the files listed by GDAL, so they are
    not identified by their files and the data computed from them are never reused"""
    source_layer = make_raster([[1, 1], [1, 1]], name="source")
    geopackage = str(tmp_path / "map.gpkg")
    gdal.Translate(geopackage, source_layer.source(), format="GPKG", creationOptions=["RASTER_TABLE=map"]).FlushCache()
    zarr = str(tmp_path / "map.zarr")
    gdal.Translate(zarr, source_layer.source(), format="Zarr").FlushCache()
    for vrt_name, vrt_source in (("geopackage.vrt", geopackage), ("subdataset.vrt", f"GPKG:{geopackage}:map")):
        gdal.BuildVRT(str(tmp_path / vrt_name), [vrt_source]).FlushCache()
    for dataset in (geopackage, zarr, str(tmp_path / "geopackage.vrt"), str(tmp_path / "subdataset.vrt")):
        assert gdal.Open(dataset) is not None
        assert others_utils.get_dataset_files(dataset) is None
    layer = QgsRasterLayer(geopackage, "geopackage")
    QgsProject.instance().addMapLayer(layer)
    assert layer.isValid()
    assert others_utils.get_layer_data(layer, 1) is None
    # while the files of a GeoTIFF identify it
    assert others_utils.get_dataset_files(source_layer.source()) == {source_layer.source()}


def test_stored_pixel_counts_follow_the_files_of_an_inline_vrt(plugin, make_raster, tmp_path):
    """A VRT can define a source as an inline VRT, whose files are not listed by GDAL"""
    source_layer = make_raster([[1, 1], [1, 1]], name="source")
    vrt = tmp_path / "inline.vrt"
    vrt.write_text(
        '<VRTDataset rasterXSize="2" rasterYSize="2"><GeoTransform>500000, 1, 0, 1000000, 0, -1</GeoTransform>'
        '<VRTRasterBand dataType="Byte" band="1"><SimpleSource><VRTDataset rasterXSize="2" rasterYSize="2">'
        '<VRTRasterBand dataType="Byte" band="1"><SimpleSource><SourceFilename relativeToVRT="1">source.tif'
        "</SourceFilename><SourceBand>1</SourceBand></SimpleSource></VRTRasterBand></VRTDataset>"
        "<SourceBand>1</SourceBand></SimpleSource></VRTRasterBand></VRTDataset>"
    )
    assert source_layer.source() in others_utils.get_dataset_files(str(vrt))
    layer = QgsRasterLayer(str(vrt), "inline vrt")
    QgsProject.instance().addMapLayer(layer)
    assert get_valid_pixel_counts(layer, 1) == {1: 4}
    fingerprint = get_map_fingerprint(layer, 1)

    dataset = gdal.Open(source_layer.source(), gdal.GA_Update)
    dataset.GetRasterBand(1).WriteArray(np.array([[1, 2], [2, 2]], dtype=np.uint8))
    dataset = None
    assert get_valid_pixel_counts(layer, 1) == {1: 1, 2: 3}
    assert get_map_fingerprint(layer, 1) != fingerprint


def test_computed_vrts_are_not_identified_by_their_files(plugin, make_raster, tmp_path):
    """The pixel values of a warped, processed or derived VRT can depend on other files (e.g. in the arguments of
    the processing) or code, so the data computed from them are never reused, also inside another VRT"""
    source_layer = make_raster([[1, 1], [1, 1]], name="source")
    make_raster([[1, 1], [1, 1]], name="gain")
    make_raster([[0, 0], [0, 0]], name="offset")
    processed = tmp_path / "processed.vrt"
    processed.write_text(
        '<VRTDataset subClass="VRTProcessedDataset">'
        '<Input><SourceFilename relativeToVRT="1">source.tif</SourceFilename></Input>'
        '<ProcessingSteps><Step><Algorithm>LocalScaleOffset</Algorithm><Argument name="relativeToVRT">true</Argument>'
        '<Argument name="gain_dataset_filename_1">gain.tif</Argument>'
        '<Argument name="gain_dataset_band_1">1</Argument>'
        '<Argument name="offset_dataset_filename_1">offset.tif</Argument>'
        '<Argument name="offset_dataset_band_1">1</Argument>'
        '</Step></ProcessingSteps><VRTRasterBand dataType="Byte" band="1" subClass="VRTProcessedRasterBand"/>'
        "</VRTDataset>"
    )
    derived = tmp_path / "derived.vrt"
    derived.write_text(
        '<VRTDataset rasterXSize="2" rasterYSize="2"><GeoTransform>500000, 1, 0, 1000000, 0, -1</GeoTransform>'
        '<VRTRasterBand dataType="Byte" band="1" subClass="VRTDerivedRasterBand"><PixelFunctionType>sum'
        '</PixelFunctionType><SimpleSource><SourceFilename relativeToVRT="1">source.tif</SourceFilename>'
        "<SourceBand>1</SourceBand></SimpleSource></VRTRasterBand></VRTDataset>"
    )
    warped = str(tmp_path / "warped.vrt")
    gdal.Warp(warped, source_layer.source(), format="VRT").FlushCache()
    mosaic = str(tmp_path / "mosaic.vrt")
    gdal.BuildVRT(mosaic, [str(derived)]).FlushCache()
    for vrt in (str(processed), str(derived), warped, mosaic):
        assert gdal.Open(vrt) is not None
        assert others_utils.get_dataset_files(vrt) is None
    # a static VRT of the same source is identified by its files
    static = str(tmp_path / "static.vrt")
    gdal.BuildVRT(static, [source_layer.source()]).FlushCache()
    assert others_utils.get_dataset_files(static) == {static, source_layer.source()}
