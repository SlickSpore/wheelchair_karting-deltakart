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

function shutdown() {
    bar.textContent = "Shutting Down!";
    fetch('/core_shutdown',  {method:'POST'})
}

function edit() {
    bar.textContent = "Shutting Down!";
    fetch('/core_shutdown',  {method:'POST'})
}

function prst_1(){
    bar.textContent = "Selected Preset 1, Reload System to Apply Changes"
    fetch('/preset_1')
}
function prst_2(){
    bar.textContent = "Selected Preset 2, Reload System to Apply Changes"
    fetch('/preset_2')
}
function prst_3(){
    bar.textContent = "Selected Preset 3, Reload System to Apply Changes"
    fetch('/preset_3')
}
function prst_4(){
    bar.textContent = "Selected Preset 4, Reload System to Apply Changes"
    fetch('/preset_4')
}
function prst_5(){
    bar.textContent = "Selected Preset 5, Reload System to Apply Changes"
    fetch('/preset_5')
}