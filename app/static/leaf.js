var map = L.map('map').setView([51.530755, -0.131733], 13);

L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    minZoom: 15,
    attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);

// //////////////////////////////
// This should work now with the data passed from Flask
// Fetch marker data from the Flask API
function fetchMarkers(query = "") {
    let url = "/api/markers";
    if (query) {
        url += `?query=${encodeURIComponent(query)}`;
    }

    console.log("Fetching markers from:", url);  // Debugging

    fetch(url)
        .then(response => response.json())
        .then(data => {
            console.log("Marker data received:", data); // Debugging

            map.eachLayer(layer => {
                if (layer instanceof L.Marker) {
                    map.removeLayer(layer);
                }
            });

            data.forEach(marker => {
                var markerInstance = L.marker([marker.latitude, marker.longitude]).addTo(map);
                markerInstance.bindPopup(`
                    <b>${marker.event_name}</b><br>
                    ${marker.description}<br>
                    ${marker.approved}<br>
                    ${marker.website}<br>
                    ${marker.address}<br>
                    ${marker.postcode}<br>
                    <button onclick="editMarker(${marker.id})">Edit</button>
                    <button onclick="deleteMarker(${marker.id})">Delete</button>
                `);
            });
        })
        .catch(error => console.error('Error fetching markers:', error));
}
fetchMarkers();

function editMarker(markerId) {
    let newName = prompt("Enter new event name:");
    let newDescription = prompt("Enter new event description:");

    fetch(`/api/markers/${markerId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            event_name: newName,
            description: newDescription,
        })
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message);
        fetchMarkers();  // Refresh markers
    })
    .catch(error => console.error("Error updating marker:", error));
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

// //////////////////////////////
// Handle search requests
document.querySelector('form').addEventListener('submit', function (e) {
    e.preventDefault();
    const query = document.getElementById('query').value;
    fetchMarkers(query);
}); // GET http request asynchronously from view function '/api/markers'. returns Promise

// Variable to store the current marker
var currentMarker = null;

// Add a click event listener to the map
map.on('click', function (e) {
    var lat = e.latlng.lat;
    var lng = e.latlng.lng;

    // Remove the previous marker if it exists
    if (currentMarker) {
        map.removeLayer(currentMarker);
    }

    // Create a new marker and add it to the map
    currentMarker = L.marker([lat, lng]).addTo(map);

    // Store the coordinates in hidden form inputs
    document.querySelector('[name="latitude"]').value = lat;
    document.querySelector('[name="longitude"]').value = lng;

    // Show the form
    document.getElementById('form-container').style.display = 'block';
});