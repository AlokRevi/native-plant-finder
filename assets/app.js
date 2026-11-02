/* Leaflet map and plant-search interface. */
"use strict";

// Leaflet expects coordinates in [latitude, longitude] order (GeoJSON uses the reverse).
const map = L.map("map", { zoomControl: false, minZoom: 3 }).setView([56.13, -106.35], 4);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
}).addTo(map);
L.control.zoom({ position: "bottomleft" }).addTo(map);
L.control.scale({ position: "bottomleft", imperial: false }).addTo(map);

const byId = (id) => document.getElementById(id);
const addressForm = byId("address-form");
const searchButton = byId("search-button");
const demoButton = byId("demo-button");
const locationStatus = byId("location-status");
const resultsStatus = byId("results-status");
const plantList = byId("plant-list");
const editFilters = byId("edit-filters");
const selectedArea = byId("selected-area");
const gardenDialog = byId("garden-dialog");
const gardenForm = byId("garden-form");
const aboutDialog = byId("about-dialog");
let selectedPlace = null;
let gardenMarker = null;
let lastFilters = {};
let nextOffset = null;
let resultGeneration = 0;
const moreButton = document.createElement("button");
moreButton.type = "button";
moreButton.textContent = "Show more plants";
moreButton.hidden = true;
plantList.after(moreButton);
moreButton.addEventListener("click", () => loadPlants(true));

function setLocationStatus(message, isError = false) {
  locationStatus.textContent = message;
  locationStatus.classList.toggle("error", isError);
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, { ...options, headers: { Accept: "application/json", ...options.headers } });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "The request did not succeed.");
  return data;
}

// Submit address lookups on button click or Enter.
// Public Nominatim does not permit implementing automatic search suggestions.
addressForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const address = byId("address-input").value.trim();
  searchButton.disabled = true;
  demoButton.disabled = true;
  setLocationStatus("Looking up your location…");
  try {
    const place = await requestJson("/api/geocode", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ q: address }) });
    choosePlace(place);
  } catch (error) {
    setLocationStatus(error.message, true);
  } finally {
    searchButton.disabled = false;
    demoButton.disabled = false;
  }
});

// The Oakville example uses fixed coordinates without an external lookup.
demoButton.addEventListener("click", async () => {
  demoButton.disabled = true;
  try {
    choosePlace(await requestJson("/api/demo-garden"));
  } catch (error) {
    setLocationStatus(error.message, true);
  } finally {
    demoButton.disabled = false;
  }
});

function choosePlace(place) {
  resultGeneration++;
  nextOffset = null;
  moreButton.hidden = true;
  selectedPlace = place;
  const point = [place.latitude, place.longitude];
  if (gardenMarker) map.removeLayer(gardenMarker);
  gardenMarker = L.marker(point).addTo(map);
  // Static popup text avoids embedding the external geocoder response as HTML.
  gardenMarker.bindPopup("Selected garden location");
  map.flyTo(point, 12, { duration: 1.2 });
  setLocationStatus(`Found: ${place.display_name}`);
  selectedArea.hidden = false;
  selectedArea.textContent = `Selected region: ${place.province || "Unknown"}`;
  editFilters.disabled = false;
  gardenForm.reset();
  lastFilters = {};
  resultsStatus.textContent = "Your location is ready. Tell us about your garden to refine the results.";
  plantList.replaceChildren();
  if (!gardenDialog.open) gardenDialog.showModal();
}

editFilters.addEventListener("click", () => {
  if (selectedPlace && !gardenDialog.open) gardenDialog.showModal();
});
byId("close-dialog").addEventListener("click", () => gardenDialog.close());
byId("skip-button").addEventListener("click", () => {
  gardenForm.reset();
  gardenDialog.close();
  lastFilters = {};
  loadPlants();
});
gardenForm.addEventListener("submit", (event) => {
  event.preventDefault();
  lastFilters = Object.fromEntries(new FormData(gardenForm).entries());
  gardenDialog.close();
  loadPlants();
});

byId("about-data-link").addEventListener("click", (event) => {
  event.preventDefault();
  aboutDialog.showModal();
});
byId("close-about").addEventListener("click", () => aboutDialog.close());
// Escape closes the dialog without submitting filters.

async function loadPlants(append = false) {
  if (!selectedPlace) return;
  const generation = append ? resultGeneration : ++resultGeneration;
  const search = new URLSearchParams({ province: selectedPlace.province, latitude: selectedPlace.latitude, longitude: selectedPlace.longitude, ...lastFilters, offset: append ? nextOffset : 0 });
  moreButton.disabled = true;
  resultsStatus.textContent = "Finding plants…";
  if (!append) { plantList.replaceChildren(); moreButton.hidden = true; }
  try {
    const result = await requestJson(`/api/plants?${search}`);
    if (generation !== resultGeneration) return;
    if (!result.supported) {
      resultsStatus.textContent = result.message;
      showEmpty("Outside the pilot region", "We currently recommend plants for Ontario gardens only. Try the Ontario demo garden to explore the catalogue.");
      return;
    }
    resultsStatus.textContent = `${result.count} of ${result.total} native plant records match. ${result.message} ${result.condition_note}`;
    selectedArea.textContent = `Selected region: ${result.region}`;
    nextOffset = result.next_offset;
    moreButton.hidden = nextOffset === null;
    if (result.count === 0) {
      showEmpty("No plants match every selection", "Try choosing “Any” for one or more conditions. Plants without information for a selected condition are excluded.");
      return;
    }
    result.plants.forEach(addPlantCard);
  } catch (error) {
    if (generation !== resultGeneration) return;
    moreButton.hidden = true;
    resultsStatus.textContent = "Unable to load plant recommendations.";
    showEmpty("Something went wrong", error.message);
  } finally {
    if (generation === resultGeneration) moreButton.disabled = false;
  }
}

function showEmpty(title, message) {
  const box = document.createElement("div");
  box.className = "empty-state";
  const icon = document.createElement("div");
  icon.className = "empty-illustration";
  icon.setAttribute("aria-hidden", "true");
  icon.textContent = "✿";
  const h3 = document.createElement("h3");
  h3.textContent = title;
  const p = document.createElement("p");
  p.textContent = message;
  box.append(icon, h3, p);
  plantList.append(box);
}

const pretty = {
  full: "Full sun", partial: "Part sun", shade: "Shade",
  sandy: "Sandy", loamy: "Loamy", clay: "Clay", dry: "Dry",
  average: "Average", moist: "Moist", herb: "Wildflower",
  shrub: "Shrub", tree: "Tree", annual: "Annual", biennial: "Biennial",
  perennial: "Perennial", wet: "Wet", grass: "Grass", sedge: "Sedge", fern: "Fern", vine: "Vine", graminoid: "Grass-like plant",
};

function addPlantCard(plant) {
  // Render record text with textContent to avoid interpreting it as HTML.
  const card = document.createElement("article");
  card.className = "plant-card";

  const imageContainer = document.createElement("div");
  imageContainer.className = "plant-art";
  if (plant.image) {
    const image = document.createElement("img");
    image.src = `/assets/illustrations/${encodeURIComponent(plant.image)}`;
    image.alt = `Stylized illustration of ${plant.common_name}, not an identification photograph`;
    image.loading = "lazy";
    imageContainer.append(image);
  } else {
    const placeholder = document.createElement("span");
    placeholder.textContent = "✿";
    placeholder.setAttribute("aria-label", "Plant image not available");
    placeholder.style.fontSize = "4rem";
    imageContainer.append(placeholder);
  }

  const detailsArea = document.createElement("div");
  detailsArea.className = "plant-body";
  const topRow = document.createElement("div");
  topRow.className = "plant-toprow";
  const category = document.createElement("span");
  category.className = "plant-category";
  category.textContent = pretty[plant.form] || plant.form || "Plant form not recorded";
  const cycle = document.createElement("span");
  cycle.className = "plant-cycle";
  cycle.textContent = pretty[plant.lifecycle] || plant.lifecycle || "Life cycle not recorded";
  topRow.append(category, cycle);

  const title = document.createElement("h3");
  title.textContent = plant.common_name;
  const scientific = document.createElement("p");
  scientific.className = "scientific";
  const emphasis = document.createElement("em");
  emphasis.textContent = plant.scientific_name;
  scientific.append(emphasis);

  const summary = document.createElement("p");
  summary.className = "plant-summary";
  summary.textContent = plant.summary;

  const extra = document.createElement("details");
  extra.className = "plant-details";
  const toggle = document.createElement("summary");
  toggle.textContent = "Full plant details";
  const description = document.createElement("p");
  description.textContent = plant.details;
  const conditions = document.createElement("p");
  conditions.className = "condition-line";
  const describe = values => values.length ? values.map(x => pretty[x] || x).join(" / ") : "Not recorded";
  conditions.textContent = `Sun: ${describe(plant.sun)} · Soil: ${describe(plant.soil)} · Moisture: ${describe(plant.moisture)}`;
  const irrigation = document.createElement("p");
  irrigation.className = "condition-line";
  irrigation.textContent = plant.drought_tolerant ? "Drought tolerant once established; establishment watering still needed." : "Check water needs, especially during dry weather.";
  const source = document.createElement("a");
  const sourceUrl = new URL(plant.source_url || "", window.location.origin);
  source.href = ["https:", "http:"].includes(sourceUrl.protocol) ? sourceUrl.href : "#";
  source.target = "_blank";
  source.rel = "noopener noreferrer";
  source.textContent = "Read the native-status source ↗";
  extra.append(toggle, description, conditions, irrigation, source);

  detailsArea.append(topRow, title, scientific, summary, extra);
  card.append(imageContainer, detailsArea);
  plantList.append(card);
}
