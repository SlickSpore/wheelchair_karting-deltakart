// Written By Ettore Caccioli 17/04/2026 © Wheelchair Karting

bar = document.getElementById("status_bar")

let running = true;

async function statusLoop() {
    while (running) {
        try {
            const response = await fetch('/status');
            const data = await response.json();

            bar.textContent = data.web_message;
    
        } catch (error) {
            console.error(error);
        }

        await new Promise(resolve => setTimeout(resolve, 1000));
    }
}

function start() {
    running = true
    fetch('/core_start', {method:'POST'});
    statusLoop();
}

function stop() {
    fetch('/core_stop',  {method:'POST'})
    running = false;
    bar.textContent = "Kart Stopped!"
}