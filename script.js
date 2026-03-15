// Detectar si estamos en localhost o en GitHub Pages
const isLocal = location.hostname === "localhost" || location.hostname === "127.0.0.1";

// Endpoints automáticos
const API_URL = isLocal
    ? "http://localhost:3000/api/datos"
    : "https://agrario-api.onrender.com/api/datos";

const HEALTH_URL = isLocal
    ? "http://localhost:3000/api/health"
    : "https://agrario-api.onrender.com/api/health";

// ========= Fetch datos =========

async function cargarDatos() {
    try {
        console.log("📡 Cargando desde:", API_URL);

        const resp = await fetch(API_URL);
        const data = await resp.json();

        renderTabla(data);
        renderIndicadores(data);
        renderGraficas(data);

    } catch (error) {
        console.error("Error cargando datos:", error);
    }
}

async function verificarBackend() {
    try {
        const resp = await fetch(HEALTH_URL);
        const data = await resp.json();
        console.log("💚 Backend OK:", data);
    } catch (e) {
        console.warn("⚠️ Backend no responde");
    }
}

verificarBackend();
cargarDatos();


// ========= Render tabla =========

function renderTabla(data) {
    const tbody = document.querySelector("#tablaDatos tbody");
    tbody.innerHTML = "";

    data.forEach(item => {
        tbody.innerHTML += `
            <tr>
                <td>${item.id}</td>
                <td>${item.aseguradora}</td>
                <td>${item.estado}</td>
                <td>${item.fecha}</td>
                <td>${item.valor}</td>
            </tr>
        `;
    });
}


// ========= Indicadores =========

function renderIndicadores(data) {
    const totalRevisados = data.length;
    const totalAprobados = data.filter(x => x.estado === "Aprobado").length;
    const totalNegados = data.filter(x => x.estado === "Negado").length;

    document.getElementById("totalRevisados").innerText = totalRevisados;
    document.getElementById("totalAprobados").innerText = totalAprobados;
    document.getElementById("totalNegados").innerText = totalNegados;
}


// ========= Gráficas =========

function renderGraficas(data) {

    const estados = contar(data, "estado");
    const aseguradoras = contar(data, "aseguradora");

    new Chart(document.getElementById("chartEstados"), {
        type: "doughnut",
        data: {
            labels: Object.keys(estados),
            datasets: [{
                data: Object.values(estados)
            }]
        }
    });

    new Chart(document.getElementById("chartAseguradoras"), {
        type: "bar",
        data: {
            labels: Object.keys(aseguradoras),
            datasets: [{
                data: Object.values(aseguradoras)
            }]
        }
    });
}


// ========= Utils =========

function contar(arr, campo) {
    return arr.reduce((acc, item) => {
        acc[item[campo]] = (acc[item[campo]] || 0) + 1;
        return acc;
    }, {});
}
