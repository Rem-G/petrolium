//**********SIDE NAV***************
$('.sidebar-head').click(function(){
    $('.ui.labeled.icon.sidebar').sidebar('toggle');
    $('.table_body').html('');
})

$(".station-btn").click(function(e){
    update_stations(e.target.id, "/station/");
});

function showPage() {
    document.getElementById("loader").style.display = "none";
    document.getElementById("stations_table").style.display = "block";
}

function showLoader() {
    document.getElementById("loader").style.display = "block";
    document.getElementById("stations_table").style.display = "none";
}

function checkIfLoaded(){
    if (document.getElementById("table_body").children.length > 0){
        showPage();
    }
    else{
        setTimeout(checkIfLoaded, 100);
    }
}

function update_stations(petrol_type, url) {
    showLoader();
    var bbox = ''
    map.getView().calculateExtent(map.getSize()).forEach(coor => {
        bbox += coor + ','
    });

    if (map.getView().getZoom() > 10){
        $('.table_body').html('').load(url+"?bbox="+bbox+"&petrol_type="+petrol_type);
    }
    else{
        $('.table_body').html('').load(url+"?error=zoom");
    }
    checkIfLoaded();
};
//**********************************


//**********DATA GETTER -> BBOX STRATEGY**********
var vectorSource = new ol.source.Vector({
    format: new ol.format.GeoJSON(),
    projection: 'EPSG:4326',
    strategy: ol.loadingstrategy.bbox,
    loader: function(extent, resolution, projection) {
        var proj = projection.getCode();
        var url = '/map/?in_bbox=' + extent.join(',');
        console.log(url);
        var xhr = new XMLHttpRequest();
        xhr.open('GET', url);
        var onError = function() {
            vectorSource.removeLoadedExtent(extent);
        }
        xhr.onerror = onError;
        xhr.onload = function() {
            if (xhr.status == 200) {
                vectorSource.clear();
                vectorSource.addFeatures(
                    vectorSource.getFormat().readFeatures(xhr.responseText, {dataProjection: 'EPSG:4326', featureProjection:'EPSG:3857'}));
            } else {
                onError();
            }
        }
        xhr.send();
    },
});

////***************************

var petrol_station_svg = '<svg width="40px" height="40px" aria-hidden="true" focusable="false" data-prefix="fas" data-icon="gas-pump" class="svg-inline--fa fa-gas-pump fa-w-16" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><path fill="currentColor" d="M336 448H16c-8.8 0-16 7.2-16 16v32c0 8.8 7.2 16 16 16h320c8.8 0 16-7.2 16-16v-32c0-8.8-7.2-16-16-16zm157.2-340.7l-81-81c-6.2-6.2-16.4-6.2-22.6 0l-11.3 11.3c-6.2 6.2-6.2 16.4 0 22.6L416 97.9V160c0 28.1 20.9 51.3 48 55.2V376c0 13.2-10.8 24-24 24s-24-10.8-24-24v-32c0-48.6-39.4-88-88-88h-8V64c0-35.3-28.7-64-64-64H96C60.7 0 32 28.7 32 64v352h288V304h8c22.1 0 40 17.9 40 40v27.8c0 37.7 27 72 64.5 75.9 43 4.3 79.5-29.5 79.5-71.7V152.6c0-17-6.8-33.3-18.8-45.3zM256 192H96V64h160v128z"></path></svg>';
var selected_petrol_station_svg = '<svg width="40px" height="40px" aria-hidden="true" focusable="false" data-prefix="fas" data-icon="gas-pump" class="svg-inline--fa fa-gas-pump fa-w-16" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><path fill="currentColor" d="M336 448H16c-8.8 0-16 7.2-16 16v32c0 8.8 7.2 16 16 16h320c8.8 0 16-7.2 16-16v-32c0-8.8-7.2-16-16-16zm157.2-340.7l-81-81c-6.2-6.2-16.4-6.2-22.6 0l-11.3 11.3c-6.2 6.2-6.2 16.4 0 22.6L416 97.9V160c0 28.1 20.9 51.3 48 55.2V376c0 13.2-10.8 24-24 24s-24-10.8-24-24v-32c0-48.6-39.4-88-88-88h-8V64c0-35.3-28.7-64-64-64H96C60.7 0 32 28.7 32 64v352h288V304h8c22.1 0 40 17.9 40 40v27.8c0 37.7 27 72 64.5 75.9 43 4.3 79.5-29.5 79.5-71.7V152.6c0-17-6.8-33.3-18.8-45.3zM256 192H96V64h160v128z"></path></svg>';


var iconStyle = new ol.style.Style({
    image: new ol.style.Icon({
            opacity: 0.6,
            src: 'data:image/svg+xml;utf8,' + petrol_station_svg,
        }),
    });

var PetroliumLayer = new ol.layer.Vector({
    source: vectorSource,
    style: function(feature, resolution) {
                iconStyle.getImage().setScale(1/Math.pow(resolution, 1/6));
                return iconStyle
            },
    minZoom: 10
});


//******CLUSTERS MARKERS*******
var clusterSource = new ol.source.Cluster({
    source: vectorSource,
});

var styleCache = {};

var StationsCluster = new ol.layer.Vector({
    source: clusterSource,
    style: function(feature) {
        var size = feature.get('features').length;
        var style = styleCache[size];
        if (!style) {
            style = new ol.style.Style({
                image: new ol.style.Circle({
                    radius: 10,
                    stroke: new ol.style.Stroke({
                    color: '#fff'
                    }),
                    fill: new ol.style.Fill({
                        color: '#3399CC'
                    })
                }),
                text: new ol.style.Text({
                    text: size.toString(),
                    fill: new ol.style.Fill({
                        color: '#fff'
                    })
                })
            });
            styleCache[size] = style;
        }
        return style;
    },
    maxZoom: 10,
    minZoom: 7
});
//***************************

//Mapbox access_token
var accessToken = 'pk.eyJ1IjoicGV0cm9saXVtIiwiYSI6ImNrZHliaHphcDFjcWcycnBpMTlpYmgycDMifQ.8Yn17qBucMsu4HelUb5VHg';

var map = new ol.Map({
    target: 'map',
    layers: [
        new ol.layer.Tile({
            source: new ol.source.XYZ({
                url: 'https://api.mapbox.com/styles/v1/mapbox/light-v10/tiles/256/{z}/{x}/{y}?access_token='+accessToken,
            })
        }),
        PetroliumLayer,
        StationsCluster,
    ],
    view: new ol.View({
        constrainResolution: true,
        center: [259817.27, 5439812.49],
        zoom: 11,
    })
});

var container = document.getElementById('popup');
var content_element = document.getElementById('popup-content');
var closer = document.getElementById('popup-closer');//Close popup

closer.onclick = function() {
    overlay.setPosition(undefined);
    closer.blur();
    return false;
};

var overlay = new ol.Overlay({
    element: container,
    autoPan: true,
    offset: [0, -10]
});
map.addOverlay(overlay);

var highlightStyle = new ol.style.Style({
    image: new ol.style.Icon({
            opacity: 0.7,
            src: 'data:image/svg+xml;utf8,' + selected_petrol_station_svg,
        }),
});

var fullscreen = new ol.control.FullScreen();
map.addControl(fullscreen);

map.on('click', function(evt){
    var feature = map.forEachFeatureAtPixel(evt.pixel,
        function(feature, layer) {
            return feature;
        });
    if (feature.get('id')) {
        var geometry = feature.getGeometry();
        var coord = geometry.getCoordinates();

        feature.setStyle(highlightStyle);
        var content = '<h3>' + feature.get('id') + '</h3>';
        content += '<h5>' + feature.get('ville') + '</h5>';
        
        content_element.innerHTML = content;
        overlay.setPosition(coord);
        
        console.info(feature.getProperties());
    }
});

var selected = null;

map.on('pointermove', function (e) {
    if (selected !== null) {
        selected.setStyle(undefined);
        selected = null;
    }

    map.forEachFeatureAtPixel(e.pixel, function (f) {
        if (f.get('id')) {
            selected = f;
            f.setStyle(highlightStyle);
            return true;
        }
    });
});


//******SEARCH BAR*******
function go_to(coordinates) {
    zoomView = new ol.View({
        center: ol.proj.transform(coordinates,"EPSG:3857","EPSG:3857"), zoom: 11 });
    map.setView(zoomView);
}

var geocoder = new Geocoder('nominatim', {
    provider: 'osm',
    lang: 'fr-FR',
    placeholder: 'Rechercher ...',
    limit: 5,
    debug: false,
    autoComplete: true,
    keepOpen: true,
    preventDefault: true
    });
map.addControl(geocoder);

geocoder.on('addresschosen', function(evt){
    var feature = evt.feature,
    coord = evt.coordinate,
    address = evt.address;
    go_to(coord);
});
//***************************


//*********GEOLOCATION*******
var geolocation = new ol.Geolocation({
    // enableHighAccuracy must be set to true to have the heading value.
    trackingOptions: {
        enableHighAccuracy: true,
    },
    projection: map.getView().getProjection(),
});

var accuracyFeature = new ol.Feature();
    geolocation.on('change:accuracyGeometry', function () {
    accuracyFeature.setGeometry(geolocation.getAccuracyGeometry());
});

var positionFeature = new ol.Feature();
positionFeature.setStyle(
    new ol.style.Style({
        image: new ol.style.Circle({
            radius: 6,
            fill: new ol.style.Fill({
                color: '#e37467',
            }),
            stroke: new ol.style.Stroke({
                color: '#fff',
                width: 2,
            }),
        }),
    })
);

geolocation.on('change:position', function () {
    var coordinates = geolocation.getPosition();
    positionFeature.setGeometry(coordinates ? new ol.geom.Point(coordinates) : null);
});

var GeoLayer = new ol.layer.Vector({
    source: new ol.source.Vector({
        features: [accuracyFeature, positionFeature],
    }),
});

document.getElementById('track').addEventListener('click', function () {
    if (geolocation.getTracking() == true){
        geolocation.setTracking(false);
        map.removeLayer(GeoLayer);
    }
    else{
        geolocation.setTracking(true);
        setTimeout(go_to(geolocation.getPosition()), 1000);
        map.addLayer(GeoLayer);
    }
});
//**************************************************