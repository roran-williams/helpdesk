document.addEventListener("DOMContentLoaded", function () {
    const ticketData = [
        { date: "2025-03-21", opened: 10, in_progress: 5, resolved: 3 },
        { date: "2025-03-22", opened: 15, in_progress: 8, resolved: 5 },
        { date: "2025-03-23", opened: 12, in_progress: 7, resolved: 10 },
        { date: "2025-03-24", opened: 20, in_progress: 12, resolved: 8 },
        { date: "2025-03-25", opened: 18, in_progress: 10, resolved: 15 },
    ];

    const labels = ticketData.map(item => item.date);
    const openedData = ticketData.map(item => item.opened);
    const inProgressData = ticketData.map(item => item.in_progress);
    const resolvedData = ticketData.map(item => item.resolved);

    const ctx = document.getElementById("ticketTrendChart").getContext("2d");

    new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Opened Tickets",
                    data: openedData,
                    borderColor: "#FF5733",
                    backgroundColor: "rgba(255, 87, 51, 0.2)",
                    fill: true,
                },
                {
                    label: "In Progress",
                    data: inProgressData,
                    borderColor: "#FFC300",
                    backgroundColor: "rgba(255, 195, 0, 0.2)",
                    fill: true,
                },
                {
                    label: "Resolved Tickets",
                    data: resolvedData,
                    borderColor: "#33FF57",
                    backgroundColor: "rgba(51, 255, 87, 0.2)",
                    fill: true,
                },
            ],
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: true,
                    position: "top",
                },
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: "Date",
                    },
                },
                y: {
                    title: {
                        display: true,
                        text: "Number of Tickets",
                    },
                    beginAtZero: true,
                },
            },
        },
    });
});
