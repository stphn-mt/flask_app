var map = L.map('map').setView([51.530755, -0.131733], 17);

var bounds = [
    [51.52017, -0.14918], // Southwest corner
    [51.54126, -0.12262]    // Northeast corner
];

// Set maxBounds to restrict dragging outside the area
map.setMaxBounds(bounds);

L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    minZoom: 15,
    attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);

// //////////////////////////////
// This should work now with the data passed from Flask
// Fetch marker data from the Flask API
// Define marker icons based on filter_type
function getMarkerIcon(filterType, approved) {
    let iconClass = "fa-solid "; // Base FontAwesome class

    if (filterType === "Sport") {
        iconClass += "fa-person-running";
    } else if (filterType === "Support") {
        iconClass += "fa-plus";
    } else if (filterType === "Club") {
        iconClass += "fa-home";
    } else {
        iconClass += "fa-map-marker-alt"; // Default marker
    }

    let color = approved ? "blue" : "red"; // Blue for approved, red for non-approved

    return L.divIcon({
        className: "", // No special Leaflet styling needed
        html: `<i class="${iconClass}" style="color: ${color}; font-size: 24px;"></i>`,
        iconSize: [30, 30], // Adjust as needed
        iconAnchor: [15, 30], // Adjust as needed
    });
}

const markerClusterGroup = L.markerClusterGroup();

function fetchMarkers(query = "") {
    let url = "/api/markers";
    if (query) {
        url += `?query=${encodeURIComponent(query)}`;
    }

    console.log("Fetching markers from:", url);  // Debugging

    fetch(url)
        .then(response => response.json())
        .then(data => {
            markerClusterGroup.clearLayers();  // Clear previous markers
            
            data.forEach(marker => {
                let markerInstance = L.marker(
                    [marker.latitude, marker.longitude],
                    { icon: getMarkerIcon(marker.filter_type, marker.approved) }
                );
                //populate markers with correct data
                let popupContent = `
                    <b>${marker.event_name}</b><br>
                    ${marker.description}<br>
                    Approved: ${marker.approved ? '✅' : '❌'}<br>
                    ${marker.website}<br>
                    ${marker.address}<br>
                    ${marker.postcode}<br>
                    Created by:${marker.creator_name}<br>
                    Contact:${marker.email_to}<br>
                `;

                // add buttons if conditions met
                if (thisUserId === marker.creator || thisUserAccessLv === 1) {
                    popupContent += `
                        <button onclick="editMarker('${marker.id}', '${marker.event_name}', '${marker.description}', '${marker.filter_type}', '${marker.website}')">Edit</button>
                        <button onclick="deleteMarker(${marker.id})">Delete</button>
                    `;
                }
                if (thisUserAccessLv === 1) {
                    popupContent += `
                        <button onclick="approveMarker(${marker.id})">Approve</button>
                    `;
                } // add 'if marker approved don't show'

                markerInstance.bindPopup(popupContent);
                markerClusterGroup.addLayer(markerInstance);
            });

            map.addLayer(markerClusterGroup);  // Add clustered markers to the map
        })
        .catch(error => console.error('Error fetching markers:', error));
}
fetchMarkers();

function editMarker(markerId, eventName, description, filter_type, website) {
    document.getElementById('modification-form').style.display = 'block'; // Show the form when modify is clicked

    document.getElementById("marker_id").value = markerId
    document.getElementById("mod-event_name").value = eventName; // Populate form with original marker data
    document.getElementById("mod-description").value = description;
    document.getElementById("mod-filter_type").value = filter_type;
    document.getElementById("mod-website").value = website;

}

function deleteMarker(markerId) {
    if (confirm("Are you sure you want to delete this marker?")) {
        fetch(`/api/markers/${markerId}`, {
            method: "DELETE"
        })
        .then(response => response.json())
        .then(data => {
            alert(data.message);
            fetchMarkers();  // Refresh markers
        })
        .catch(error => console.error("Error deleting marker:", error));
    }
}
function approveMarker(markerId) {
    if (confirm("Are you sure you want to approve this marker?")) {
        fetch(`/approve/${markerId}`, {
            method: "PUT"
        })
        .then(response => response.json())
        .then(data => {
            alert(data.message);
            fetchMarkers();  // Refresh markers
        })
        .catch(error => console.error("Error approving marker:", error));
    }
}
// //////////////////////////////
// Handle search requests
document.querySelector('form').addEventListener('submit', function (e) {
    e.preventDefault();
    const query = document.getElementById('query').value;
    fetchMarkers(query);
}); // GET http request asynchronously from view function '/api/markers'. returns Promise

// Variable to store the current marker
var currentMarker = null;
