/**
 * Frontend Application Logic
 * Blood Donation Network with Smart Matching
 * Real-time event handling, Leaflet spatial visualization, priority queue monitor,
 * and donor/hospital portals.
 */

let hospitals = [];
let donors = [];
let activeDonorId = "donor_anuj";
let map = null;
let mapMarkers = [];
let mapCircles = [];
let ws = null;
let currentUser = null;

// On Page Load
document.addEventListener("DOMContentLoaded", () => {
  initAuth();
  initWebSocket();
  initMap();
  loadInitialData();
  // Periodic poll fallback in case WS disconnects
  setInterval(refreshPeriodicData, 8000);
});

// Authentication System (Section 5.1 User Service)
function initAuth() {
  const saved = localStorage.getItem("blood_network_user");
  if (saved) {
    try {
      currentUser = JSON.parse(saved);
    } catch (e) {
      currentUser = null;
    }
  }

  // Default to Lead Author (Anuj Kumar) if no session exists yet
  if (!currentUser) {
    currentUser = {
      token: "demo_token_anuj",
      role: "donor",
      user: {
        id: "usr_anuj",
        name: "Anuj Kumar [24BAI70735]",
        email: "anuj@cu.ac.in",
        role: "donor",
        linked_entity_id: "donor_anuj"
      }
    };
  }

  updateAuthUI();
}

function updateAuthUI() {
  if (!currentUser) return;
  const nameEl = document.getElementById("user-display-name");
  const roleEl = document.getElementById("user-display-role");

  if (nameEl) nameEl.textContent = currentUser.user.name;
  if (roleEl) {
    roleEl.textContent = currentUser.role;
    roleEl.className = {
      "donor": "bg-rose-500 text-white text-[10px] px-1.5 py-0.2 rounded font-black uppercase",
      "hospital": "bg-sky-600 text-white text-[10px] px-1.5 py-0.2 rounded font-black uppercase",
      "admin": "bg-emerald-600 text-white text-[10px] px-1.5 py-0.2 rounded font-black uppercase"
    }[currentUser.role] || "bg-slate-700 text-white text-[10px] px-1.5 py-0.2 rounded font-bold uppercase";
  }

  // If user is a donor, ensure active persona points to their entity
  if (currentUser.role === "donor" && currentUser.user.linked_entity_id) {
    activeDonorId = currentUser.user.linked_entity_id;
  }
}

function openAuthModal() {
  const modal = document.getElementById("auth-modal");
  if (modal) modal.classList.remove("hidden");
  switchAuthTab("login");
}

function closeAuthModal() {
  const modal = document.getElementById("auth-modal");
  if (modal) modal.classList.add("hidden");
}

function switchAuthTab(tabName) {
  ["login", "reg-donor", "reg-hosp"].forEach(t => {
    const pane = document.getElementById(`auth-pane-${t}`);
    const btn = document.getElementById(`auth-btn-${t}`);
    if (pane) pane.classList.add("hidden");
    if (btn) {
      btn.className = "flex-1 py-3 text-center text-slate-600 hover:text-slate-900";
    }
  });

  const activePane = document.getElementById(`auth-pane-${tabName}`);
  const activeBtn = document.getElementById(`auth-btn-${tabName}`);
  if (activePane) activePane.classList.remove("hidden");
  if (activeBtn) {
    activeBtn.className = "flex-1 py-3 text-center border-b-2 border-rose-600 text-rose-700 bg-white font-bold";
  }
}

async function handleLoginSubmit(e) {
  e.preventDefault();
  const email = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;
  const errEl = document.getElementById("login-error-msg");
  errEl.classList.add("hidden");

  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });

    if (res.ok) {
      const data = await res.json();
      setAuthSession(data.session);
      closeAuthModal();
    } else {
      const err = await res.json();
      errEl.textContent = err.detail || "Authentication failed.";
      errEl.classList.remove("hidden");
    }
  } catch (err) {
    errEl.textContent = "Server communication error.";
    errEl.classList.remove("hidden");
  }
}

async function quickLoginDemo(email, password) {
  const emailInput = document.getElementById("login-email");
  const passInput = document.getElementById("login-password");
  if (emailInput && passInput) {
    emailInput.value = email;
    passInput.value = password;
  }
  const form = emailInput.closest("form");
  if (form) {
    form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
  }
}

async function handleDonorRegisterSubmit(e) {
  e.preventDefault();
  const name = document.getElementById("reg-donor-name").value.trim();
  const email = document.getElementById("reg-donor-email").value.trim();
  const password = document.getElementById("reg-donor-password").value;
  const phone = document.getElementById("reg-donor-phone").value.trim();
  const bloodGroup = document.getElementById("reg-donor-bg").value;
  const gender = document.getElementById("reg-donor-gender").value;
  const age = parseInt(document.getElementById("reg-donor-age").value, 10);
  const weight = parseFloat(document.getElementById("reg-donor-weight").value);
  const localityRaw = document.getElementById("reg-donor-locality").value;
  const [address, latStr, lonStr] = localityRaw.split("|");
  const healthEligible = document.getElementById("reg-donor-health").checked;
  const errEl = document.getElementById("reg-donor-error");
  errEl.classList.add("hidden");

  try {
    const res = await fetch("/api/auth/register/donor", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        email,
        password,
        phone,
        blood_group: bloodGroup,
        gender,
        age,
        weight_kg: weight,
        address,
        latitude: parseFloat(latStr),
        longitude: parseFloat(lonStr),
        health_eligible: healthEligible,
        is_available: true
      })
    });

    if (res.ok) {
      const data = await res.json();
      alert(`Welcome, ${name}! Your donor account has been registered.`);
      await loadDonors();
      setAuthSession(data.session);
      closeAuthModal();
      switchTab("donor");
    } else {
      const err = await res.json();
      errEl.textContent = err.detail || "Registration failed.";
      errEl.classList.remove("hidden");
    }
  } catch (err) {
    errEl.textContent = "Server communication error.";
    errEl.classList.remove("hidden");
  }
}

async function handleHospitalRegisterSubmit(e) {
  e.preventDefault();
  const name = document.getElementById("reg-hosp-name").value.trim();
  const email = document.getElementById("reg-hosp-email").value.trim();
  const password = document.getElementById("reg-hosp-password").value;
  const phone = document.getElementById("reg-hosp-phone").value.trim();
  const licenseNumber = document.getElementById("reg-hosp-license").value.trim();
  const hospitalType = document.getElementById("reg-hosp-type").value;
  const localityRaw = document.getElementById("reg-hosp-locality").value;
  const [address, latStr, lonStr] = localityRaw.split("|");
  const errEl = document.getElementById("reg-hosp-error");
  errEl.classList.add("hidden");

  try {
    const res = await fetch("/api/auth/register/hospital", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        email,
        password,
        phone,
        address,
        latitude: parseFloat(latStr),
        longitude: parseFloat(lonStr),
        hospital_type: hospitalType,
        license_number: licenseNumber
      })
    });

    if (res.ok) {
      const data = await res.json();
      alert(`Institution "${name}" registered successfully.`);
      await loadHospitals();
      setAuthSession(data.session);
      closeAuthModal();
      switchTab("hospital");
    } else {
      const err = await res.json();
      errEl.textContent = err.detail || "Registration failed.";
      errEl.classList.remove("hidden");
    }
  } catch (err) {
    errEl.textContent = "Server communication error.";
    errEl.classList.remove("hidden");
  }
}

function setAuthSession(session) {
  currentUser = session;
  localStorage.setItem("blood_network_user", JSON.stringify(session));
  updateAuthUI();

  if (session.role === "donor" && session.user.linked_entity_id) {
    selectDonorAndSwitch(session.user.linked_entity_id);
  } else if (session.role === "hospital") {
    switchTab("hospital");
    const hospSelect = document.getElementById("req-hospital");
    if (hospSelect && session.user.linked_entity_id) {
      hospSelect.value = session.user.linked_entity_id;
    }
  } else if (session.role === "admin") {
    switchTab("queue");
  }
}


// Tab Navigation
function switchTab(tabName) {
  document.querySelectorAll(".tab-pane").forEach(el => el.classList.add("hidden"));
  document.querySelectorAll(".tab-btn").forEach(el => el.classList.remove("active-tab"));

  const targetPane = document.getElementById(`tab-${tabName}`);
  const targetBtn = document.getElementById(`tab-btn-${tabName}`);

  if (targetPane) targetPane.classList.remove("hidden");
  if (targetBtn) targetBtn.classList.add("active-tab");

  if (tabName === "map") {
    setTimeout(() => {
      if (map) map.invalidateSize();
    }, 200);
  } else if (tabName === "queue") {
    loadQueueView();
  } else if (tabName === "events") {
    loadEvents();
  } else if (tabName === "donor") {
    loadDonorProfile(activeDonorId);
    loadDonorAlerts();
  }
}

// WebSocket Connection
function initWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/events`;
  const statusEl = document.getElementById("ws-status");

  try {
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      if (statusEl) {
        statusEl.textContent = "Live EventBus: Connected";
        statusEl.className = "font-medium text-emerald-300";
      }
    };

    ws.onmessage = (event) => {
      try {
        const sysEvent = JSON.parse(event.data);
        handleIncomingEvent(sysEvent);
      } catch (e) {
        console.error("WS Parse error", e);
      }
    };

    ws.onclose = () => {
      if (statusEl) {
        statusEl.textContent = "Live EventBus: Reconnecting...";
        statusEl.className = "font-medium text-amber-300";
      }
      setTimeout(initWebSocket, 3000);
    };

    ws.onerror = () => {
      if (statusEl) {
        statusEl.textContent = "Live EventBus: Offline";
        statusEl.className = "font-medium text-rose-300";
      }
    };
  } catch (err) {
    console.warn("WebSocket init error", err);
  }
}

function handleIncomingEvent(event) {
  prependEventToStream(event);
  // Auto-refresh relevant tabs
  loadRequests();
  loadQueueView();
  loadDonorAlerts();
  refreshStats();
}

// Map Initialization
function initMap() {
  const mapContainer = document.getElementById("leaflet-map");
  if (!mapContainer || map) return;

  // Center around Chandigarh Tricity
  map = L.map("leaflet-map").setView([30.7333, 76.7450], 11);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: '&copy; <a href="https://openstreetmap.org">OpenStreetMap</a> contributors'
  }).addTo(map);
}

function updateMapMarkers() {
  if (!map) return;

  // Clear existing markers & circles
  mapMarkers.forEach(m => map.removeLayer(m));
  mapCircles.forEach(c => map.removeLayer(c));
  mapMarkers = [];
  mapCircles = [];

  // Custom Icons
  const hospitalIcon = L.divIcon({
    html: '<div style="background-color:#dc2626; color:white; border-radius:50%; width:26px; height:26px; display:flex; align-items:center; justify-content:center; border:2px solid white; box-shadow:0 2px 4px rgba(0,0,0,0.3); font-weight:bold; font-size:12px;"><i class="fa-solid fa-hospital"></i></div>',
    className: 'custom-hosp-pin',
    iconSize: [26, 26],
    iconAnchor: [13, 13]
  });

  // Plot Hospitals
  hospitals.forEach(h => {
    const marker = L.marker([h.latitude, h.longitude], { icon: hospitalIcon }).addTo(map);
    marker.bindPopup(`
      <div class="space-y-1">
        <strong class="text-rose-800 text-sm font-bold">${h.name}</strong>
        <p class="text-xs text-slate-600">${h.hospital_type}</p>
        <p class="text-[11px] text-slate-500">${h.address} | Phone: ${h.phone}</p>
      </div>
    `);
    mapMarkers.push(marker);
  });

  // Plot Donors
  donors.forEach(d => {
    const isEligible = d.is_eligible && d.is_available;
    const color = isEligible ? "#10b981" : "#f59e0b";

    const donorIcon = L.divIcon({
      html: `<div style="background-color:${color}; color:white; border-radius:50%; width:20px; height:20px; display:flex; align-items:center; justify-content:center; border:2px solid white; box-shadow:0 1px 3px rgba(0,0,0,0.25); font-weight:bold; font-size:9px;">${d.blood_group}</div>`,
      className: 'custom-donor-pin',
      iconSize: [20, 20],
      iconAnchor: [10, 10]
    });

    const marker = L.marker([d.latitude, d.longitude], { icon: donorIcon }).addTo(map);
    marker.bindPopup(`
      <div class="space-y-1 text-xs">
        <strong class="text-slate-900">${d.name}</strong> (${d.blood_group})
        <p class="text-slate-600">${d.address}</p>
        <p><span class="font-semibold">Status:</span> ${d.cooldown_info ? d.cooldown_info.status_label : (d.is_available ? 'Available' : 'Unavailable')}</p>
        <button onclick="selectDonorAndSwitch('${d.id}')" class="mt-1 bg-rose-600 text-white text-[10px] px-2 py-0.5 rounded hover:bg-rose-700">View Persona</button>
      </div>
    `);
    mapMarkers.push(marker);
  });
}

function selectDonorAndSwitch(donorId) {
  activeDonorId = donorId;
  const selectEl = document.getElementById("active-donor-select");
  if (selectEl) selectEl.value = donorId;
  switchTab("donor");
}

// Initial Data Load
async function loadInitialData() {
  await Promise.all([
    loadHospitals(),
    loadDonors(),
    loadRequests(),
    loadQueueView(),
    loadEvents()
  ]);
  refreshStats();
}

async function refreshPeriodicData() {
  refreshStats();
}

async function refreshStats() {
  try {
    const res = await fetch("/api/health");
    if (!res.ok) return;
    const data = await res.json();
    document.getElementById("stat-donors").textContent = data.active_donors;
    document.getElementById("stat-queue").textContent = data.queue_size;
  } catch (e) {}
}

// Load Hospitals
async function loadHospitals() {
  try {
    const res = await fetch("/api/hospitals");
    hospitals = await res.json();
    const select = document.getElementById("req-hospital");
    select.innerHTML = hospitals.map(h => `<option value="${h.id}">${h.name} (${h.address})</option>`).join("");
    updateMapMarkers();
  } catch (err) {
    console.error("Failed loading hospitals", err);
  }
}

// Load Donors
async function loadDonors() {
  try {
    const res = await fetch("/api/donors");
    donors = await res.json();

    const select = document.getElementById("active-donor-select");
    select.innerHTML = donors.map(d => {
      const tag = d.id === "donor_anuj" ? " [Lead Author / O+]" : (d.id === "donor_shlok" ? " [Co-Author / O- Universal]" : "");
      return `<option value="${d.id}">${d.name} (${d.blood_group}, ${d.gender})${tag}</option>`;
    }).join("");

    if (donors.some(d => d.id === activeDonorId)) {
      select.value = activeDonorId;
    } else if (donors.length > 0) {
      activeDonorId = donors[0].id;
      select.value = activeDonorId;
    }

    loadDonorProfile(activeDonorId);
    updateMapMarkers();
  } catch (err) {
    console.error("Failed loading donors", err);
  }
}

// Donor Persona Switching
async function handleDonorSelect(donorId) {
  activeDonorId = donorId;
  await loadDonorProfile(donorId);
  loadDonorAlerts();
}

async function loadDonorProfile(donorId) {
  try {
    const res = await fetch(`/api/donors/${donorId}`);
    if (!res.ok) return;
    const donor = await res.json();

    document.getElementById("donor-card-name").textContent = donor.name;
    document.getElementById("donor-card-location").textContent = `${donor.address} (${donor.latitude.toFixed(3)}, ${donor.longitude.toFixed(3)})`;
    document.getElementById("donor-card-bg").textContent = donor.blood_group;
    document.getElementById("donor-card-meta").textContent = `${donor.gender}, ${donor.age} yrs`;
    document.getElementById("donor-card-weight").textContent = `${donor.weight_kg} kg`;
    document.getElementById("donor-card-donations").textContent = `${donor.total_donations} completed`;
    document.getElementById("donor-card-response").textContent = `${Math.round(donor.response_history_rate * 100)}% reliability`;

    // Cooldown status
    const cInfo = donor.cooldown_info;
    const badge = document.getElementById("donor-cooldown-badge");
    const bar = document.getElementById("donor-cooldown-bar");
    const desc = document.getElementById("donor-cooldown-desc");

    if (cInfo.in_cooldown) {
      badge.textContent = `Cooling Down (${cInfo.days_remaining}d left)`;
      badge.className = "px-2 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-800";
      const pct = Math.max(0, Math.min(100, Math.round(((cInfo.required_cooldown_days - cInfo.days_remaining) / cInfo.required_cooldown_days) * 100)));
      bar.style.width = `${pct}%`;
      bar.className = "bg-amber-500 h-2 rounded-full";
      desc.textContent = `Eligible on ${cInfo.next_eligible_date}. Cooldown rule: ${cInfo.required_cooldown_days} days for ${donor.gender}.`;
    } else {
      badge.textContent = "Ready to Donate";
      badge.className = "px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-100 text-emerald-800";
      bar.style.width = "100%";
      bar.className = "bg-emerald-500 h-2 rounded-full";
      desc.textContent = `Fully eligible under NBTC health criteria (${cInfo.required_cooldown_days}-day period fulfilled).`;
    }

    // Availability toggle
    const toggle = document.getElementById("donor-availability-toggle");
    toggle.checked = donor.is_available;
  } catch (err) {
    console.error("Error loading donor profile", err);
  }
}

async function handleToggleAvailability(isAvailable) {
  try {
    const res = await fetch(`/api/donors/${activeDonorId}/availability`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_available: isAvailable })
    });
    if (res.ok) {
      loadDonors();
    }
  } catch (e) {
    console.error("Failed toggling availability", e);
  }
}

// Hospital Blood Request Creation
async function handleCreateRequest(e) {
  e.preventDefault();
  const hospitalId = document.getElementById("req-hospital").value;
  const patientName = document.getElementById("req-patient").value;
  const bloodGroup = document.getElementById("req-blood-group").value;
  const units = parseInt(document.getElementById("req-units").value, 10);
  const urgency = document.querySelector('input[name="urgency"]:checked').value;
  const notes = document.getElementById("req-notes").value;

  try {
    const res = await fetch("/api/requests", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        patient_name: patientName,
        hospital_id: hospitalId,
        blood_group: bloodGroup,
        units_required: units,
        urgency: urgency,
        notes: notes
      })
    });

    if (res.ok) {
      const created = await res.json();
      document.getElementById("req-patient").value = "";
      document.getElementById("req-notes").value = "";
      loadRequests();
      loadQueueView();
      loadDonorAlerts();
      refreshStats();

      // Highlight dispatch on map if map is open
      if (map) {
        const hosp = hospitals.find(h => h.id === hospitalId);
        if (hosp) {
          const radiusMeters = urgency === "Critical" ? 50000 : (urgency === "Urgent" ? 30000 : 20000);
          const circleColor = urgency === "Critical" ? "#e11d48" : (urgency === "Urgent" ? "#f59e0b" : "#3b82f6");
          const circle = L.circle([hosp.latitude, hosp.longitude], {
            radius: radiusMeters,
            color: circleColor,
            fillColor: circleColor,
            fillOpacity: 0.12,
            weight: 2,
            dashArray: "4, 6"
          }).addTo(map);
          mapCircles.push(circle);
          map.setView([hosp.latitude, hosp.longitude], 11);
        }
      }
    } else {
      const err = await res.json();
      alert("Error creating request: " + err.detail);
    }
  } catch (err) {
    console.error("Request creation failed", err);
  }
}

// Load Blood Requests
async function loadRequests() {
  try {
    const res = await fetch("/api/requests");
    const requests = await res.json();
    const container = document.getElementById("requests-list");

    if (!requests || requests.length === 0) {
      container.innerHTML = `<div class="text-center py-10 text-slate-400">No active blood requests. Create one above to initiate smart matching!</div>`;
      return;
    }

    container.innerHTML = requests.map(req => {
      const urgencyBadge = {
        "Critical": "bg-rose-100 text-rose-800 border-rose-300",
        "Urgent": "bg-amber-100 text-amber-800 border-amber-300",
        "Normal": "bg-blue-100 text-blue-800 border-blue-300"
      }[req.urgency] || "bg-slate-100 text-slate-800";

      const statusBadge = {
        "Queued": "bg-purple-100 text-purple-800",
        "Matching": "bg-sky-100 text-sky-800 animate-pulse",
        "Notifying": "bg-amber-100 text-amber-800 font-bold",
        "Accepted": "bg-emerald-100 text-emerald-800 font-bold",
        "Fulfilled": "bg-slate-100 text-slate-700",
        "Cancelled": "bg-red-100 text-red-700"
      }[req.status] || "bg-slate-100";

      // Match breakdown
      let matchesHtml = "";
      if (req.matched_donors && req.matched_donors.length > 0) {
        matchesHtml = `
          <div class="mt-3 pt-3 border-t border-slate-100">
            <div class="flex items-center justify-between text-xs font-semibold text-slate-700 mb-2">
              <span>Top Smart-Matched Donors (${req.matched_donors.length} found):</span>
              <span class="text-[10px] text-slate-500">Ranked by Blood Compatibility &bull; Distance &bull; Availability &bull; Response History</span>
            </div>
            <div class="space-y-1.5">
              ${req.matched_donors.slice(0, 4).map(m => {
                const isAlerted = req.current_alerted_donor_ids.includes(m.donor_id);
                const isAccepted = req.accepted_donor_id === m.donor_id;
                let donorBadge = isAccepted
                  ? `<span class="bg-emerald-600 text-white px-2 py-0.5 rounded text-[10px] font-bold"><i class="fa-solid fa-check"></i> Accepted Donor</span>`
                  : (isAlerted ? `<span class="bg-amber-500 text-white px-2 py-0.5 rounded text-[10px]"><i class="fa-solid fa-bell"></i> Alerted</span>` : `<span class="text-slate-400 text-[10px]">Candidate</span>`);

                return `
                  <div class="flex items-center justify-between text-xs bg-slate-50 px-2.5 py-1.5 rounded border border-slate-100">
                    <div class="flex items-center space-x-2">
                      <span class="font-mono text-slate-400 font-bold">#${m.rank}</span>
                      <strong class="text-slate-800">${m.donor_name}</strong>
                      <span class="bg-rose-50 text-rose-700 font-bold px-1.5 py-0.2 rounded text-[10px]">${m.donor_blood_group}</span>
                      <span class="text-slate-500 text-[11px]">&bull; ${m.distance_km} km</span>
                    </div>
                    <div class="flex items-center space-x-2">
                      <span class="text-[11px] text-slate-600 font-medium">Score: <strong class="text-slate-900">${Math.round(m.total_score * 100)}%</strong></span>
                      ${donorBadge}
                    </div>
                  </div>
                `;
              }).join("")}
            </div>
          </div>
        `;
      }

      // Complete donation button if Accepted
      let actionBtn = "";
      if (req.status === "Accepted") {
        actionBtn = `
          <button onclick="handleCompleteDonation('${req.id}')" class="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold px-3 py-1.5 rounded shadow transition flex items-center space-x-1.5">
            <i class="fa-solid fa-check-circle"></i>
            <span>Mark Donation Completed (Start Cooldown)</span>
          </button>
        `;
      }

      return `
        <div class="border border-slate-200 rounded-xl p-4 bg-white shadow-sm hover:border-slate-300 transition">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div class="flex items-center space-x-3">
              <span class="w-10 h-10 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 font-black flex items-center justify-center text-sm">
                ${req.blood_group}
              </span>
              <div>
                <div class="flex items-center space-x-2">
                  <h3 class="font-bold text-slate-800 text-sm">${req.patient_name}</h3>
                  <span class="border px-2 py-0.2 rounded text-[10px] font-bold ${urgencyBadge}">${req.urgency}</span>
                  <span class="px-2 py-0.2 rounded text-[10px] font-semibold ${statusBadge}">${req.status}</span>
                </div>
                <p class="text-xs text-slate-500">${req.hospital_name} &bull; ${req.units_required} Unit(s) required &bull; ${req.notes || "No extra clinical notes"}</p>
              </div>
            </div>
            <div class="flex items-center space-x-2">
              ${actionBtn}
            </div>
          </div>
          ${matchesHtml}
        </div>
      `;
    }).join("");
  } catch (err) {
    console.error("Failed loading requests", err);
  }
}

// Complete Donation Action
async function handleCompleteDonation(requestId) {
  try {
    const res = await fetch(`/api/requests/${requestId}/complete`, {
      method: "POST"
    });
    if (res.ok) {
      loadRequests();
      loadDonors();
      loadQueueView();
      loadDonorAlerts();
    }
  } catch (err) {
    console.error("Failed completing donation", err);
  }
}

// Load Donor Alerts
async function loadDonorAlerts() {
  try {
    const res = await fetch(`/api/donors/${activeDonorId}`);
    if (!res.ok) return;
    const donor = await res.json();
    const container = document.getElementById("donor-alerts-list");
    const notifications = donor.notifications || [];

    // Update notification badge count in tabs
    const pendingCount = notifications.filter(n => n.status === "Delivered" || n.status === "Pending").length;
    const badgeCountEl = document.getElementById("donor-badge-count");
    if (badgeCountEl) {
      if (pendingCount > 0) {
        badgeCountEl.textContent = pendingCount;
        badgeCountEl.classList.remove("hidden");
      } else {
        badgeCountEl.classList.add("hidden");
      }
    }

    if (notifications.length === 0) {
      container.innerHTML = `<div class="text-center py-12 text-slate-400">No match alerts for ${donor.name} yet. Trigger a request to evaluate!</div>`;
      return;
    }

    // Sort newest first
    notifications.sort((a, b) => new Date(b.sent_at) - new Date(a.sent_at));

    container.innerHTML = notifications.map(notif => {
      const isPending = notif.status === "Delivered" || notif.status === "Pending";
      const isCritical = notif.urgency === "Critical";

      let actionButtons = "";
      if (isPending) {
        actionButtons = `
          <div class="flex items-center gap-2 mt-3 pt-2 border-t border-slate-100">
            <button onclick="respondToAlert('${notif.id}', true)" class="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs px-3.5 py-1.5 rounded-lg shadow transition flex items-center space-x-1.5">
              <i class="fa-solid fa-thumbs-up"></i>
              <span>Accept Request</span>
            </button>
            <button onclick="respondToAlert('${notif.id}', false)" class="bg-rose-50 hover:bg-rose-100 text-rose-700 font-semibold text-xs px-3 py-1.5 rounded-lg border border-rose-200 transition flex items-center space-x-1.5">
              <i class="fa-solid fa-thumbs-down"></i>
              <span>Decline (Escalate to Next)</span>
            </button>
            <button onclick="simulateTimeout('${notif.id}')" class="bg-slate-100 hover:bg-slate-200 text-slate-600 text-xs px-2.5 py-1.5 rounded-lg transition" title="Simulate 5-minute unanswered timeout">
              <i class="fa-solid fa-clock"></i> Simulate Timeout
            </button>
          </div>
        `;
      } else {
        const statusColors = {
          "Accepted": "text-emerald-700 font-bold",
          "Declined": "text-rose-700 font-semibold",
          "Timed Out": "text-amber-700 italic"
        }[notif.status] || "text-slate-600";
        actionButtons = `
          <div class="mt-2 text-xs ${statusColors}">
            Response: ${notif.status} at ${new Date(notif.responded_at || notif.sent_at).toLocaleTimeString()}
          </div>
        `;
      }

      const urgencyBanner = isCritical ? "border-l-4 border-l-rose-600 bg-rose-50/30" : "border-l-4 border-l-amber-500 bg-white";

      return `
        <div class="border border-slate-200 rounded-xl p-4 shadow-sm ${urgencyBanner}">
          <div class="flex items-center justify-between text-xs mb-1">
            <span class="font-bold text-slate-800 flex items-center space-x-2">
              <i class="fa-solid fa-paper-plane text-rose-600"></i>
              <span>${notif.channel} Alert &bull; ${notif.hospital_name}</span>
            </span>
            <span class="text-slate-400 text-[11px]">${new Date(notif.sent_at).toLocaleTimeString()}</span>
          </div>
          <p class="text-xs text-slate-700 font-medium my-1.5">${notif.message}</p>
          <div class="text-[11px] text-slate-500 flex items-center space-x-3">
            <span>Blood Needed: <strong class="text-rose-700">${notif.blood_group_needed}</strong></span>
            <span>Distance: <strong>${notif.distance_km} km</strong></span>
            <span>Urgency: <strong>${notif.urgency}</strong></span>
          </div>
          ${actionButtons}
        </div>
      `;
    }).join("");
  } catch (err) {
    console.error("Failed loading donor alerts", err);
  }
}

// Respond to Alert
async function respondToAlert(notificationId, accept) {
  try {
    const res = await fetch(`/api/alerts/${notificationId}/respond`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ accept: accept })
    });
    if (res.ok) {
      loadDonorAlerts();
      loadRequests();
      loadDonors();
      loadQueueView();
    }
  } catch (err) {
    console.error("Failed responding to alert", err);
  }
}

// Simulate Alert Timeout
async function simulateTimeout(notificationId) {
  try {
    const res = await fetch(`/api/alerts/${notificationId}/timeout`, {
      method: "POST"
    });
    if (res.ok) {
      loadDonorAlerts();
      loadRequests();
      loadQueueView();
    }
  } catch (err) {
    console.error("Failed simulating timeout", err);
  }
}

// Load Priority Queue View
async function loadQueueView() {
  try {
    const res = await fetch("/api/queue");
    const data = await res.json();
    const tbody = document.getElementById("queue-table-body");
    const items = data.queue || [];

    if (items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-center py-8 text-slate-400">Priority queue is currently empty. All blood requests processed!</td></tr>`;
      return;
    }

    tbody.innerHTML = items.map((item, idx) => {
      const urgencyBadge = {
        "Critical": "bg-rose-100 text-rose-800 font-bold",
        "Urgent": "bg-amber-100 text-amber-800 font-bold",
        "Normal": "bg-blue-100 text-blue-800 font-bold"
      }[item.urgency] || "bg-slate-100";

      return `
        <tr class="hover:bg-slate-50 transition">
          <td class="py-2.5 px-3 font-mono font-bold text-slate-900">#${idx + 1}</td>
          <td class="py-2.5 px-3"><span class="px-2 py-0.5 rounded text-[11px] ${urgencyBadge}">${item.urgency} (Rank ${item.urgency_rank})</span></td>
          <td class="py-2.5 px-3 font-semibold text-slate-800">${item.patient_name} <span class="text-slate-500 font-normal">at ${item.hospital_name}</span></td>
          <td class="py-2.5 px-3 font-bold text-rose-700">${item.blood_group}</td>
          <td class="py-2.5 px-3 text-slate-600 font-mono">${item.wait_seconds}s waiting</td>
          <td class="py-2.5 px-3 text-slate-400 text-[11px]">${new Date(item.created_at).toLocaleTimeString()}</td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.error("Failed loading priority queue", err);
  }
}

// Process Next Queue Item
async function processNextQueueItem() {
  try {
    const res = await fetch("/api/queue/process_next", { method: "POST" });
    const data = await res.json();
    if (data.status === "empty") {
      alert("Queue is empty. No requests waiting.");
    } else {
      loadQueueView();
      loadRequests();
      loadDonorAlerts();
    }
  } catch (err) {
    console.error("Failed processing next queue item", err);
  }
}

// Load Events Stream
async function loadEvents() {
  try {
    const res = await fetch("/api/events");
    const events = await res.json();
    const stream = document.getElementById("events-stream");

    if (!events || events.length === 0) {
      stream.innerHTML = `<div class="text-center py-10 text-slate-400">Listening for live system events...</div>`;
      return;
    }

    stream.innerHTML = "";
    events.forEach(e => prependEventToStream(e));
  } catch (err) {
    console.error("Failed loading events", err);
  }
}

function prependEventToStream(event) {
  const stream = document.getElementById("events-stream");
  if (!stream) return;

  const typeConfig = {
    "RequestCreated": { color: "bg-purple-100 text-purple-800 border-purple-200", icon: "fa-plus-circle" },
    "DonorMatched": { color: "bg-sky-100 text-sky-800 border-sky-200", icon: "fa-magnifying-glass-chart" },
    "DonorAlerted": { color: "bg-amber-100 text-amber-800 border-amber-200", icon: "fa-bell" },
    "DonorAccepted": { color: "bg-emerald-100 text-emerald-800 border-emerald-200", icon: "fa-check-circle" },
    "DonorDeclined": { color: "bg-rose-100 text-rose-800 border-rose-200", icon: "fa-circle-xmark" },
    "NoResponseTimeout": { color: "bg-orange-100 text-orange-800 border-orange-200", icon: "fa-hourglass-end" },
    "DonationCompleted": { color: "bg-teal-100 text-teal-800 border-teal-200", icon: "fa-droplet" }
  }[event.event_type] || { color: "bg-slate-100 text-slate-800 border-slate-200", icon: "fa-circle-info" };

  const eventCard = document.createElement("div");
  eventCard.className = `p-3 rounded-lg border text-xs bg-white shadow-xs flex items-start justify-between gap-3`;
  eventCard.innerHTML = `
    <div class="flex items-start space-x-2.5">
      <span class="px-2 py-0.5 rounded text-[10px] font-bold border flex items-center space-x-1 ${typeConfig.color}">
        <i class="fa-solid ${typeConfig.icon}"></i>
        <span>${event.event_type}</span>
      </span>
      <div>
        <p class="font-semibold text-slate-800">${event.description}</p>
        <div class="text-[10px] text-slate-500 font-mono mt-0.5">${JSON.stringify(event.payload)}</div>
      </div>
    </div>
    <span class="text-slate-400 text-[10px] shrink-0">${new Date(event.timestamp).toLocaleTimeString()}</span>
  `;

  // Prepend to stream
  if (stream.firstChild) {
    stream.insertBefore(eventCard, stream.firstChild);
  } else {
    stream.appendChild(eventCard);
  }
}

// Benchmark Suite Execution
async function runSystemBenchmark() {
  const btn = document.getElementById("btn-run-benchmark");
  const resultsBox = document.getElementById("benchmark-results-box");
  const tableBody = document.getElementById("benchmark-table-body");

  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>Evaluating...</span>`;

  try {
    const res = await fetch("/api/system/benchmark", { method: "POST" });
    const data = await res.json();

    document.getElementById("bm-avg-latency").textContent = `${data.average_match_time_ms} ms`;
    document.getElementById("bm-donors-eval").textContent = `${data.donors_evaluated} Donors`;
    document.getElementById("bm-heap-status").textContent = "PASS";

    tableBody.innerHTML = data.tests.map(t => `
      <tr class="hover:bg-slate-50">
        <td class="py-2.5 px-3 font-bold text-slate-900">${t.scenario}</td>
        <td class="py-2.5 px-3"><span class="px-2 py-0.5 rounded text-[10px] font-bold ${t.urgency === 'Critical' ? 'bg-rose-100 text-rose-800' : (t.urgency === 'Urgent' ? 'bg-amber-100 text-amber-800' : 'bg-blue-100 text-blue-800')}">${t.urgency}</span></td>
        <td class="py-2.5 px-3 font-bold text-rose-700">${t.blood_group}</td>
        <td class="py-2.5 px-3 text-slate-600">${t.hospital}</td>
        <td class="py-2.5 px-3 font-semibold text-slate-800">${t.matches_found} Candidates</td>
        <td class="py-2.5 px-3 font-mono font-bold text-emerald-700">${t.time_to_match_ms} ms</td>
        <td class="py-2.5 px-3 font-mono text-slate-800">${Math.round(t.top_match_score * 100)}%</td>
      </tr>
    `).join("");

    resultsBox.classList.remove("hidden");
    loadRequests();
    loadQueueView();
  } catch (err) {
    console.error("Benchmark failed", err);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-play"></i> <span>Run Full Benchmark</span>`;
  }
}

// Reset System Data
async function resetSystemData(donorCount) {
  try {
    const res = await fetch("/api/system/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ donor_count: donorCount })
    });
    if (res.ok) {
      loadInitialData();
      alert(`System reset successfully with ${donorCount} donors.`);
    }
  } catch (err) {
    console.error("Reset failed", err);
  }
}
