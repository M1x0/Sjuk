async function fetchJSON(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return await response.json();
}

function renderAgents(data) {
  const agents = data.agents || [];
  document.getElementById('agent-count').textContent = agents.length;
  const select = document.getElementById('agent-select');
  select.innerHTML = '';
  agents.forEach((agent) => {
    const option = document.createElement('option');
    option.value = agent.name;
    option.textContent = `${agent.name} (${agent.role})`;
    select.appendChild(option);
  });
}

function renderProjects(data) {
  const tbody = document.querySelector('#project-table tbody');
  tbody.innerHTML = '';
  const projects = data.projects || [];
  document.getElementById('project-count').textContent = projects.filter((p) => p.status === 'active').length;
  projects.forEach((project) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${project.name}</td>
      <td>${project.status}</td>
      <td>${Math.round(project.budget || 0)} kr</td>
      <td>${Math.round((project.progress || 0) * 100)} %</td>
    `;
    if (project.status === 'failed') {
      tr.classList.add('failed');
    }
    tbody.appendChild(tr);
  });
}

function renderFinance(data) {
  const history = data.history || [];
  const list = document.getElementById('finance-list');
  list.innerHTML = '';
  if (history.length) {
    document.getElementById('cash').textContent = `${Math.round(history[0].cash)} kr`;
  }
  history.forEach((entry) => {
    const li = document.createElement('li');
    const notes = entry.notes ? ` – ${entry.notes}` : '';
    li.textContent = `${new Date(entry.timestamp * 1000).toLocaleTimeString()} | Kassan: ${Math.round(entry.cash)} kr${notes}`;
    list.appendChild(li);
  });
}

function renderMessages(data) {
  const container = document.getElementById('messages');
  container.innerHTML = '';
  const messages = data.messages || [];
  messages.forEach((message) => {
    const div = document.createElement('div');
    div.classList.add('message');
    const meta = document.createElement('div');
    meta.classList.add('meta');
    meta.textContent = `${new Date(message.timestamp * 1000).toLocaleTimeString()} — ${message.sender} [${message.sender_role}]`;
    const body = document.createElement('div');
    body.textContent = message.content;
    div.appendChild(meta);
    div.appendChild(body);
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
  });
}

async function refresh() {
  try {
    const [agents, projects, finance, messages] = await Promise.all([
      fetchJSON('/api/agents'),
      fetchJSON('/api/projects'),
      fetchJSON('/api/finance'),
      fetchJSON('/api/messages?limit=80'),
    ]);
    renderAgents(agents);
    renderProjects(projects);
    renderFinance(finance);
    renderMessages(messages);
  } catch (error) {
    console.error('Dashboard refresh failed', error);
  }
}

setInterval(refresh, 4000);
refresh();

document.getElementById('interview-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const agent = document.getElementById('agent-select').value;
  const question = document.getElementById('question').value;
  if (!agent || !question) {
    return;
  }
  const response = await fetch('/api/interview', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ agent, question }),
  });
  if (!response.ok) {
    console.error('Interview failed');
    return;
  }
  const data = await response.json();
  document.getElementById('interview-response').textContent = `Svar: ${data.reply}`;
  document.getElementById('question').value = '';
  await refresh();
});
