document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const voiceBtn = document.getElementById('voice-command-btn');
    const assistantResponse = document.getElementById('assistant-response');
    
    // Connect to Socket.IO
    const socket = io();
    
    // Room elements
    const rooms = {
        kitchen: {
            element: document.getElementById('kitchen-room'),
            lightImg: document.getElementById('kitchen-light-img'),
            lightGlow: document.getElementById('kitchen-light-glow')
        },
        dining: {
            element: document.getElementById('dining-room'),
            lightImg: document.getElementById('dining-light-img'),
            lightGlow: document.getElementById('dining-light-glow')
        },
        living_room: {
            element: document.getElementById('living-room'),
            lightImg: document.getElementById('living-room-light-img'),
            lightGlow: document.getElementById('living-room-light-glow')
        }
    };
    
    // Update light states from server
    socket.on('update_lights', function(state) {
        updateLightUI('kitchen', state.kitchen_light);
        updateLightUI('dining', state.dining_light);
        updateLightUI('living_room', state.living_room_light);
    });
    
    // Update assistant response
    socket.on('assistant_response', function(data) {
        assistantResponse.innerHTML = `<p>${data.text}</p>`;
        assistantResponse.scrollTop = assistantResponse.scrollHeight;
    });
    
    // Listening status
    socket.on('listening_status', function(data) {
        if (data.status === 'listening') {
            voiceBtn.classList.add('listening');
            assistantResponse.innerHTML = '<p>Listening... Speak now</p>';
        } else if (data.status === 'processing') {
            assistantResponse.innerHTML = '<p>Processing your command...</p>';
        } else {
            voiceBtn.classList.remove('listening');
        }
    });
    
    // Voice command button
    voiceBtn.addEventListener('click', function() {
        if (!('webkitSpeechRecognition' in window)) {
            alert('Your browser does not support speech recognition. Please use Chrome or Edge.');
            return;
        }
        
        const recognition = new webkitSpeechRecognition();
        recognition.lang = 'en-US';
        recognition.interimResults = false;
        
        recognition.start();
        
        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            sendCommand(transcript);
        };
        
        recognition.onerror = function(event) {
            assistantResponse.innerHTML = `<p>Error: ${event.error}</p>`;
            voiceBtn.classList.remove('listening');
        };
    });
    
    // Helper functions
    function updateLightUI(light, isOn) {
        const room = rooms[light];
        if (room) {
            room.lightImg.src = isOn ? '/static/images/bulb-on.png' : '/static/images/bulb-off.png';
            room.lightGlow.style.display = isOn ? 'block' : 'none';
            room.element.classList.toggle('light-on', isOn);
        }
    }
    
    function sendCommand(command) {
        fetch('/command', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ command: command.toLowerCase() })
        });
    }
    
    // Initialize UI
    Object.values(rooms).forEach(room => {
        room.lightGlow.style.display = 'none';
    });
});