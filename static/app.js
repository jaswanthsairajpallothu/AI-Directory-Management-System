// --- Tab Navigation ---
function showTab(tabName) {
  document.querySelectorAll('.tab-content').forEach(tab => {
    tab.classList.remove('active');
  });
  document.querySelectorAll('.tab-button').forEach(btn => {
    btn.classList.remove('active');
  });

  document.getElementById(tabName).classList.add('active');
  document.querySelector(`.tab-button[onclick="showTab('${tabName}')"]`).classList.add('active');
}

// --- WebSocket Connection ---
const list = document.getElementById('suggestion-list');
const wsProtocol = (location.protocol === 'https:' ? 'wss://' : 'ws://');
const ws = new WebSocket(wsProtocol + location.host + '/ws');

ws.onmessage = e => {
  const data = JSON.parse(e.data);
  const div = createSuggestionElement(data);
  list.prepend(div); // Add new suggestions to the top
};

ws.onopen = () => {
  console.log('WebSocket connected');
};

ws.onclose = () => {
  console.log('WebSocket disconnected. Attempting to reconnect...');
  setTimeout(setupWebSocket, 5000); // Try to reconnect every 5s
};

// --- API Calls & UI Rendering ---

/**
 * Creates a DOM element for a single suggestion
 */
function createSuggestionElement(data) {
  const div = document.createElement('div');
  div.className = 'suggestion';
  div.id = `suggestion-${btoa(data.path)}`; // Create a unique ID

  div.innerHTML = `
    <b>${data.suggested_category}</b> (conf: ${data.confidence.toFixed(2)})
    <code>${data.path}</code>
  `;

  const yes = document.createElement('button');
  yes.textContent = 'Accept';
  yes.className = 'btn-accept';

  const no = document.createElement('button');
  no.textContent = 'Reject';
  no.className = 'btn-reject';

  yes.onclick = () => act(data.path, true, div);
  no.onclick = () => act(data.path, false, div);

  div.append(yes, no);
  return div;
}

/**
 * Handles 'Accept' or 'Reject' actions
 */
async function act(path, accept, div) {
  const url = `/api/apply?path=${encodeURIComponent(path)}&accept=${accept}`;
  try {
    const res = await fetch(url, { method: 'POST' });
    if (res.ok) {
      div.remove();
    } else {
      const err = await res.json();
      alert(`Error: ${err.detail}`);
      if (res.status === 404) div.remove(); // Remove if file is already gone
    }
  } catch (e) {
    alert('Network error applying action.');
  }
}

/**
 * Loads suggestions that were made *before* the page was opened
 */
async function loadInitialSuggestions() {
  try {
    const res = await fetch('/api/suggestions');
    const suggestions = await res.json();
    list.innerHTML = ''; // Clear list
    suggestions.forEach(data => {
      list.append(createSuggestionElement(data));
    });
  } catch (e) {
    console.error('Failed to load suggestions:', e);
  }
}

/**
 * Loads and displays the system configuration
 */
async function loadConfig() {
  try {
    const res = await fetch('/api/config');
    const config = await res.json();

    document.getElementById('config-watched').textContent = JSON.stringify(config.watched_directories, null, 2);
    document.getElementById('config-categories').textContent = JSON.stringify(config.category_folders, null, 2);

    const extensions = {
      text: config.text_extensions,
      image: config.image_extensions
    };
    document.getElementById('config-extensions').textContent = JSON.stringify(extensions, null, 2);

    // Populate the dropdown in the training tab
    const labelSelect = document.getElementById('train-label');
    labelSelect.innerHTML = ''; // Clear default
    Object.keys(config.category_folders).forEach(category => {
      const option = document.createElement('option');
      option.value = category;
      option.textContent = category;
      labelSelect.append(option);
    });

  } catch (e) {
    console.error('Failed to load config:', e);
  }
}

// --- Model Training Tab Logic ---
const trainingList = document.getElementById('training-data-list');
const trainBtn = document.getElementById('train-btn');
const addSampleBtn = document.getElementById('add-sample-btn');
const trainText = document.getElementById('train-text');
const trainLabel = document.getElementById('train-label');
const trainStatus = document.getElementById('train-status');
const sampleCountEl = document.getElementById('sample-count');

let newSamples = []; // Holds samples added in this session

/**
 * Loads the current training data from the server
 */
async function loadTrainingData() {
  try {
    const res = await fetch('/api/training_data');
    const data = await res.json();
    trainingList.innerHTML = '';
    sampleCountEl.textContent = data.length;
    data.forEach(sample => {
      const [text, label] = sample;
      const div = document.createElement('div');
      div.className = 'training-sample';
      div.innerHTML = `<b>${label}</b>: <span>"${text}"</span>`;
      trainingList.prepend(div);
    });
  } catch (e) {
    console.error('Failed to load training data:', e);
  }
}

/**
 * Adds a new sample to the UI list (not yet sent to server)
 */
addSampleBtn.onclick = () => {
  const text = trainText.value;
  const label = trainLabel.value;

  if (!text.trim()) {
    alert('Please enter sample text.');
    return;
  }

  const sample = { text, label };
  newSamples.push(sample);

  // Add to UI
  const div = document.createElement('div');
  div.className = 'training-sample new';
  div.innerHTML = `<b>${label}</b>: <span>"${text}"</span> (new)`;
  trainingList.prepend(div);

  // Update count
  sampleCountEl.textContent = parseInt(sampleCountEl.textContent) + 1;

  // Clear inputs
  trainText.value = '';
};

/**
_ Handles the "Train New Model" button click
 */
trainBtn.onclick = async () => {
  if (newSamples.length === 0) {
    if (!confirm('You have not added new samples. Retrain with existing data?')) {
      return;
    }
  }

  trainStatus.textContent = 'Training...';
  trainBtn.disabled = true;

  try {
    const res = await fetch('/api/train', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newSamples)
    });

    if (res.ok) {
      const result = await res.json();
      trainStatus.textContent = `✅ Model trained with ${result.samples_trained} samples!`;
      newSamples = []; // Clear the new samples
      // Reload the training data to show a clean list
      await loadTrainingData();
    } else {
      const err = await res.json();
      trainStatus.textContent = `Error: ${err.detail}`;
    }

  } catch (e) {
    trainStatus.textContent = 'Error: Network request failed.';
  } finally {
    trainBtn.disabled = false;
  }
};

// --- Initial Page Load ---
document.addEventListener('DOMContentLoaded', () => {
  loadInitialSuggestions();
  loadConfig();
  loadTrainingData();
  showTab('suggestions');
});
