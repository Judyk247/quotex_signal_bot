// static/dashboard.js

document.addEventListener("DOMContentLoaded", () => {
    const signalTableBody = document.querySelector("#signals-table tbody");
    const lastUpdated = document.getElementById("last-update");

    // Function to fetch signals from backend
    async function fetchSignals() {
        try {
            const response = await fetch("/get_signals");
            const data = await response.json();

            // Clear old rows
            signalTableBody.innerHTML = "";

            // Populate table with signals from Quotex stream
            data.signals.forEach(signal => {
                const row = document.createElement("tr");

                // Symbol
                const symbolCell = document.createElement("td");
                symbolCell.textContent = signal.symbol || "N/A";
                row.appendChild(symbolCell);

                // Direction / Signal
                const directionCell = document.createElement("td");
                const direction = signal.signal || signal.direction || "Hold";
                directionCell.textContent = direction;
                directionCell.classList.add(direction.toLowerCase());
                row.appendChild(directionCell);

                // Timeframe
                const timeframeCell = document.createElement("td");
                timeframeCell.textContent = signal.timeframe || "-";
                row.appendChild(timeframeCell);

                // Signal Time (from backend)
                const timeCell = document.createElement("td");
                timeCell.textContent = signal.time || new Date().toISOString().slice(0,19).replace("T"," ");
                row.appendChild(timeCell);

                // Dashboard Received Time
                const receivedCell = document.createElement("td");
                receivedCell.textContent = new Date().toISOString().slice(0,19).replace("T"," ");
                row.appendChild(receivedCell);

                // Confidence
                const confidenceCell = document.createElement("td");
                confidenceCell.textContent = signal.confidence ? `${signal.confidence}%` : "-";
                row.appendChild(confidenceCell);

                signalTableBody.appendChild(row);
            });

            // Update last refresh timestamp
            const now = new Date();
            lastUpdated.textContent = `Last updated: ${now.toLocaleTimeString()}`;
        } catch (error) {
            console.error("Error fetching signals:", error);
        }
    }

    // Initial fetch
    fetchSignals();

    // Auto-refresh every 60 seconds
    setInterval(fetchSignals, 60000);

    // Socket.IO listener for new signals (real-time from Quotex)
    const socket = io();
    socket.on("new_signal", function(data) {
        const row = signalTableBody.insertRow();

        row.insertCell(0).innerText = data.symbol || "N/A";
        row.insertCell(1).innerText = data.signal || "Hold";
        row.cells[1].classList.add((data.signal || "hold").toLowerCase());
        row.insertCell(2).innerText = data.timeframe || "-";
        row.insertCell(3).innerText = data.time || new Date().toISOString().slice(0,19).replace("T"," ");
        row.insertCell(4).innerText = new Date().toISOString().slice(0,19).replace("T"," ");
        row.insertCell(5).innerText = data.confidence ? `${data.confidence}%` : "-";

        lastUpdated.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;

        // Keep only the 50 most recent signals
        while (signalTableBody.rows.length > 50) {
            signalTableBody.deleteRow(0);
        }
    });
});
