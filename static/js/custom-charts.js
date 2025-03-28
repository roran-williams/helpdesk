document.addEventListener("DOMContentLoaded", function () {
    let ctx = document.getElementById("myChart").getContext("2d");

    let myChart = new Chart(ctx, {
        type: "bar",  // Change to 'line', 'pie', etc. if needed
        data: {
            labels: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            datasets: [{
                label: "Ticket Resolutions",
                data: [12, 19, 3, 5, 2],  // Replace with dynamic data if needed
                backgroundColor: "rgba(54, 162, 235, 0.5)",
                borderColor: "rgba(54, 162, 235, 1)",
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
});
