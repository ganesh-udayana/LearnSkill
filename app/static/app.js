// PathPulse AI - Client Application Logic

let currentRoadmap = null;
let currentView = 'timeline';
let savedRoadmaps = [];

function apiFetch(url, options = {}) {
  const token = localStorage.getItem('pathpulse_token') || sessionStorage.getItem('pathpulse_token');
  const headers = new Headers(options.headers || {});
  if (token) headers.set('Authorization', `Bearer ${token}`);
  return fetch(url, { ...options, headers });
}

// App Settings in LocalStorage
let appSettings = {
  provider: localStorage.getItem('pathpulse_provider') || 'smart_fallback',
  apiKey: localStorage.getItem('pathpulse_api_key') || '',
};

// Initialize App
document.addEventListener('DOMContentLoaded', async () => {
  setupEventListeners();
  loadSettings();
  await loadSavedRoadmaps();
  // Start each session with a fresh goal; saved plans remain available in My Roadmaps.
  showGeneratorScreen();
});

function setupEventListeners() {
  // Skill level card selection
  document.querySelectorAll('.skill-level-card').forEach(card => {
    card.addEventListener('click', function () {
      document.querySelectorAll('.skill-level-card').forEach(c => {
        c.classList.remove('border-indigo-600', 'bg-indigo-50/50', 'ring-2', 'ring-indigo-500');
        c.classList.add('border-slate-200');
      });
      this.classList.remove('border-slate-200');
      this.classList.add('border-indigo-600', 'bg-indigo-50/50', 'ring-2', 'ring-indigo-500');
      const radio = this.querySelector('input[type="radio"]');
      if (radio) radio.checked = true;
    });
  });

  // Learning style cards selection
  document.querySelectorAll('.style-card').forEach(card => {
    card.addEventListener('click', function () {
      document.querySelectorAll('.style-card').forEach(c => {
        c.classList.remove('border-indigo-600', 'bg-indigo-50/40', 'border-2');
        c.classList.add('border-slate-200', 'border');
      });
      this.classList.remove('border-slate-200', 'border');
      this.classList.add('border-indigo-600', 'bg-indigo-50/40', 'border-2');
      const radio = this.querySelector('input[type="radio"]');
      if (radio) radio.checked = true;
    });
  });

  // Checkin pace selection
  document.querySelectorAll('.pace-option').forEach(card => {
    card.addEventListener('click', function () {
      document.querySelectorAll('.pace-option').forEach(c => {
        c.classList.remove('border-indigo-600', 'bg-indigo-50/50', 'border-2');
        c.classList.add('border');
      });
      this.classList.remove('border');
      this.classList.add('border-indigo-600', 'bg-indigo-50/50', 'border-2');
      const radio = this.querySelector('input[type="radio"]');
      if (radio) radio.checked = true;
    });
  });

  // Adjust pace selection
  document.querySelectorAll('.adjust-pace-card').forEach(card => {
    card.addEventListener('click', function () {
      document.querySelectorAll('.adjust-pace-card').forEach(c => {
        c.classList.remove('border-amber-500', 'bg-amber-50/50', 'border-2');
        c.classList.add('border-slate-200', 'border');
      });
      this.classList.remove('border-slate-200', 'border');
      this.classList.add('border-amber-500', 'bg-amber-50/50', 'border-2');
      const radio = this.querySelector('input[type="radio"]');
      if (radio) radio.checked = true;
    });
  });

  // Close dropdown on outside click
  document.addEventListener('click', (e) => {
    const dropdown = document.getElementById('roadmapsDropdown');
    const btn = document.getElementById('savedRoadmapsBtn');
    if (dropdown && !dropdown.contains(e.target) && btn && !btn.contains(e.target)) {
      dropdown.classList.add('hidden');
    }
  });
}

function updateHoursDisplay(val) {
  document.getElementById('hoursDisplay').innerText = `${val} hrs/wk`;
}

function applyPreset(goal, level, hours, weeks, style) {
  document.getElementById('goalInput').value = goal;
  
  // Set skill level
  const levelRadio = document.querySelector(`input[name="skillLevel"][value="${level}"]`);
  if (levelRadio) {
    levelRadio.checked = true;
    levelRadio.closest('.skill-level-card').click();
  }

  // Set hours
  document.getElementById('hoursPerWeek').value = hours;
  updateHoursDisplay(hours);

  // Set timeframe
  document.getElementById('timeframeWeeks').value = weeks;

  // Set style
  const styleRadio = document.querySelector(`input[name="learningStyle"][value="${style}"]`);
  if (styleRadio) {
    styleRadio.checked = true;
    styleRadio.closest('.style-card').click();
  }
}

// -------------------------------------------------------------
// NAVIGATION & VIEW SWITCHING
// -------------------------------------------------------------
function showGeneratorScreen() {
  document.getElementById('generatorScreen').classList.remove('hidden');
  document.getElementById('dashboardScreen').classList.add('hidden');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showDashboardScreen() {
  document.getElementById('generatorScreen').classList.add('hidden');
  document.getElementById('dashboardScreen').classList.remove('hidden');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function switchView(viewName) {
  currentView = viewName;
  const tabs = {
    timeline: document.getElementById('tabTimeline'),
    kanban: document.getElementById('tabKanban'),
    summary: document.getElementById('tabSummary'),
  };
  const views = {
    timeline: document.getElementById('timelineView'),
    kanban: document.getElementById('kanbanView'),
    summary: document.getElementById('summaryView'),
  };

  Object.keys(tabs).forEach(k => {
    if (k === viewName) {
      tabs[k].className = 'px-3 py-1.5 text-xs font-bold rounded-lg bg-indigo-600 text-white shadow-sm flex items-center space-x-1.5 transition';
      views[k].classList.remove('hidden');
    } else {
      tabs[k].className = 'px-3 py-1.5 text-xs font-bold rounded-lg text-slate-600 hover:bg-slate-100 flex items-center space-x-1.5 transition';
      views[k].classList.add('hidden');
    }
  });

  const labels = {
    timeline: 'Timeline Stepper View',
    kanban: 'Kanban Progress Board',
    summary: 'Phase Curriculum Summary',
  };
  document.getElementById('activeViewLabel').innerText = labels[viewName] || 'View';

  if (viewName === 'kanban') renderKanban();
  if (viewName === 'summary') renderPhaseSummary();
  if (viewName === 'timeline') renderTimeline();
}

// -------------------------------------------------------------
// SAVED ROADMAPS API & LOCAL STORAGE
// -------------------------------------------------------------
async function loadSavedRoadmaps() {
  try {
    const res = await apiFetch('/api/roadmaps');
    if (res.ok) {
      savedRoadmaps = await res.json();
      renderSavedRoadmapsDropdown();
    }
  } catch (err) {
    console.error('Failed to load saved roadmaps:', err);
  }
}

function toggleRoadmapsDropdown() {
  const dd = document.getElementById('roadmapsDropdown');
  dd.classList.toggle('hidden');
}

function renderSavedRoadmapsDropdown() {
  const container = document.getElementById('roadmapsListContainer');
  if (!container) return;

  if (savedRoadmaps.length === 0) {
    container.innerHTML = '<div class="p-3 text-center text-slate-400">No saved roadmaps yet.</div>';
    return;
  }

  container.innerHTML = savedRoadmaps.map(rm => `
    <div class="px-3 py-2 hover:bg-slate-50 flex items-center justify-between group cursor-pointer" onclick="loadRoadmap('${rm.id}')">
      <div class="truncate pr-2">
        <div class="font-bold text-slate-800 truncate">${escapeHtml(rm.goal)}</div>
        <div class="text-[10px] text-slate-400 flex items-center space-x-1">
          <span>${rm.progress_percentage || 0}%</span>
          <span>•</span>
          <span>${rm.target_timeframe_weeks} wks</span>
          <span>•</span>
          <span class="capitalize">${rm.learning_style || 'project'}</span>
        </div>
      </div>
      <button onclick="event.stopPropagation(); deleteRoadmap('${rm.id}')" class="opacity-0 group-hover:opacity-100 p-1 text-slate-400 hover:text-rose-600 rounded transition" title="Delete">
        <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
      </button>
    </div>
  `).join('');

  if (window.lucide) window.lucide.createIcons();
}

async function loadRoadmap(roadmapId) {
  try {
    const res = await apiFetch(`/api/roadmaps/${roadmapId}`);
    if (res.ok) {
      currentRoadmap = await res.json();
      document.getElementById('roadmapsDropdown').classList.add('hidden');
      renderRoadmapDashboard();
      showDashboardScreen();
    }
  } catch (err) {
    console.error('Error loading roadmap:', err);
  }
}

async function deleteRoadmap(roadmapId) {
  if (!confirm('Are you sure you want to delete this roadmap?')) return;
  try {
    const res = await apiFetch(`/api/roadmaps/${roadmapId}`, { method: 'DELETE' });
    if (res.ok) {
      await loadSavedRoadmaps();
      if (currentRoadmap && currentRoadmap.id === roadmapId) {
        if (savedRoadmaps.length > 0) {
          loadRoadmap(savedRoadmaps[0].id);
        } else {
          currentRoadmap = null;
          showGeneratorScreen();
        }
      }
    }
  } catch (err) {
    console.error('Error deleting roadmap:', err);
  }
}

// -------------------------------------------------------------
// ROADMAP GENERATION
// -------------------------------------------------------------
async function submitGenerateRoadmap() {
  const goal = document.getElementById('goalInput').value.trim();
  if (!goal) {
    alert('Please enter a learning goal.');
    return;
  }

  const skillLevel = document.querySelector('input[name="skillLevel"]:checked')?.value || 'beginner';
  const hoursPerWeek = parseInt(document.getElementById('hoursPerWeek').value, 10) || 10;
  const targetTimeframe = parseInt(document.getElementById('timeframeWeeks').value, 10) || 12;
  const learningStyle = document.querySelector('input[name="learningStyle"]:checked')?.value || 'project-based';

  const btn = document.getElementById('generateBtn');
  const originalHtml = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `
    <i data-lucide="loader-2" class="w-5 h-5 animate-spin"></i>
    <span>AI Mentor Synthesizing Roadmap...</span>
  `;
  if (window.lucide) window.lucide.createIcons();

  const payload = {
    goal: goal,
    skill_level: skillLevel,
    hours_per_week: hoursPerWeek,
    target_timeframe_weeks: targetTimeframe,
    learning_style: learningStyle,
    api_key: appSettings.apiKey || null,
    ai_provider: appSettings.provider || 'gemini',
  };

  try {
    const res = await apiFetch('/api/roadmaps/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to generate roadmap');
    }

    currentRoadmap = await res.json();
    await loadSavedRoadmaps();
    renderRoadmapDashboard();
    showDashboardScreen();

    // Trigger celebratory confetti
    if (window.confetti) {
      window.confetti({ particleCount: 75, spread: 70, origin: { y: 0.6 } });
    }
  } catch (err) {
    alert('Generation error: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalHtml;
    if (window.lucide) window.lucide.createIcons();
  }
}

// -------------------------------------------------------------
// RENDER DASHBOARD & COMPONENTS
// -------------------------------------------------------------
function renderRoadmapDashboard() {
  if (!currentRoadmap) return;

  // 1. Meta & Header Info
  document.getElementById('dashGoalTitle').innerText = currentRoadmap.goal;
  document.getElementById('dashGoalBadge').innerText = `${currentRoadmap.skill_level} · ${currentRoadmap.learning_style}`;
  document.getElementById('dashPaceText').innerText = `${currentRoadmap.hours_per_week} hrs/wk · ${currentRoadmap.target_timeframe_weeks} weeks`;
  
  // Style pill
  const styleBadge = document.getElementById('dashStyleBadge');
  const isProject = currentRoadmap.learning_style === 'project-based';
  styleBadge.innerHTML = isProject
    ? `<i data-lucide="hammer" class="w-3.5 h-3.5 text-indigo-600"></i><span>Project-Based</span>`
    : `<i data-lucide="book-open" class="w-3.5 h-3.5 text-violet-600"></i><span>Theory-First</span>`;

  // Style buttons
  const projBtn = document.getElementById('styleToggleProject');
  const theoryBtn = document.getElementById('styleToggleTheory');
  if (isProject) {
    projBtn.className = 'px-2.5 py-1 text-xs font-bold rounded-md bg-white text-indigo-700 shadow-sm transition';
    theoryBtn.className = 'px-2.5 py-1 text-xs font-bold rounded-md text-slate-600 hover:text-slate-900 transition';
  } else {
    theoryBtn.className = 'px-2.5 py-1 text-xs font-bold rounded-md bg-white text-violet-700 shadow-sm transition';
    projBtn.className = 'px-2.5 py-1 text-xs font-bold rounded-md text-slate-600 hover:text-slate-900 transition';
  }

  // Progress bar & metrics
  const pct = currentRoadmap.progress_percentage || 0;
  document.getElementById('dashProgressPct').innerText = `${pct}%`;
  document.getElementById('dashProgressBar').style.width = `${pct}%`;
  document.getElementById('dashMilestonesCount').innerText = `${currentRoadmap.completed_milestones || 0} of ${currentRoadmap.total_milestones || 0} Milestones completed`;
  
  // Streaks & Badges count
  const streak = currentRoadmap.current_streak_days || 1;
  document.getElementById('streakCount').innerText = streak;
  document.getElementById('modalStreakDays').innerText = streak;
  const badges = currentRoadmap.badges_earned || [];
  document.getElementById('badgeCount').innerText = badges.length;

  // Mentor Advice
  if (currentRoadmap.mentor_advice) {
    document.getElementById('mentorAdviceText').innerText = currentRoadmap.mentor_advice;
    document.getElementById('mentorAdviceBox').classList.remove('hidden');
  }

  // Change log button visibility
  const changeLogBtn = document.getElementById('viewChangeLogBtn');
  if (currentRoadmap.adjustment_logs && currentRoadmap.adjustment_logs.length > 0) {
    changeLogBtn.classList.remove('hidden');
    changeLogBtn.innerText = `View Mentor Change Log (${currentRoadmap.adjustment_logs.length})`;
  } else {
    changeLogBtn.classList.add('hidden');
  }

  // Render the current view
  if (currentView === 'timeline') renderTimeline();
  else if (currentView === 'kanban') renderKanban();
  else if (currentView === 'summary') renderPhaseSummary();

  if (window.lucide) window.lucide.createIcons();
}

// -------------------------------------------------------------
// VIEW 1: TIMELINE / STEPPER RENDER
// -------------------------------------------------------------
function renderTimeline() {
  const container = document.getElementById('milestonesList');
  if (!container || !currentRoadmap) return;

  container.innerHTML = currentRoadmap.milestones.map((m, idx) => {
    const isDone = m.status === 'done';
    const isInProgress = m.status === 'in_progress';
    
    // Status node styles
    let nodeClass = 'node-not_started';
    let nodeIcon = `${idx + 1}`;
    if (isDone) {
      nodeClass = 'node-done';
      nodeIcon = '<i data-lucide="check" class="w-4 h-4 text-white"></i>';
    } else if (isInProgress) {
      nodeClass = 'node-in_progress';
      nodeIcon = '<i data-lucide="play" class="w-3.5 h-3.5 text-white fill-white"></i>';
    }

    // Status pill style
    let statusPill = `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-600">Not Started</span>`;
    if (isDone) {
      statusPill = `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 flex items-center space-x-1"><span>✓ Completed</span></span>`;
    } else if (isInProgress) {
      statusPill = `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-100 text-indigo-700 animate-pulse">● In Progress</span>`;
    }

    // Resources HTML with stretch-feature Quality Ranking badges
    const resourcesHtml = (m.resources || []).map(r => {
      // Level badges
      const levelColors = {
        beginner: 'bg-emerald-50 text-emerald-700 border-emerald-200',
        intermediate: 'bg-blue-50 text-blue-700 border-blue-200',
        advanced: 'bg-purple-50 text-purple-700 border-purple-200',
      };
      const levelClass = levelColors[r.level?.toLowerCase()] || 'bg-slate-50 text-slate-600 border-slate-200';

      return `
        <a href="${escapeHtml(r.url)}" target="_blank" rel="noopener noreferrer" class="flex flex-col sm:flex-row sm:items-center justify-between p-2.5 bg-slate-50 hover:bg-indigo-50/50 border border-slate-200 hover:border-indigo-300 rounded-xl transition group">
          <div class="flex items-center space-x-2.5">
            <span class="p-1.5 bg-white rounded-lg border border-slate-200 text-slate-700 group-hover:text-indigo-600 shrink-0">
              <i data-lucide="${r.type === 'video' ? 'play-circle' : (r.type === 'course' ? 'graduation-cap' : 'book')}" class="w-4 h-4"></i>
            </span>
            <div>
              <div class="font-bold text-slate-800 text-xs group-hover:text-indigo-600 transition flex items-center space-x-1">
                <span>${escapeHtml(r.title)}</span>
                <i data-lucide="external-link" class="w-3 h-3 text-slate-400 group-hover:text-indigo-500"></i>
              </div>
              <div class="text-[10px] text-slate-400 flex items-center space-x-1.5 mt-0.5">
                <span class="font-medium text-slate-500">${escapeHtml(r.platform || 'Free Resource')}</span>
                <span>•</span>
                <span class="capitalize">${escapeHtml(r.type || 'tutorial')}</span>
              </div>
            </div>
          </div>

          <div class="flex items-center space-x-1.5 mt-2 sm:mt-0">
            <span class="px-2 py-0.5 rounded text-[9px] font-bold border uppercase ${levelClass}">${escapeHtml(r.level || 'Beginner')}</span>
            <span class="px-2 py-0.5 rounded text-[9px] font-medium bg-white border border-slate-200 text-slate-600">⏱️ ${escapeHtml(r.estimated_time || '3 hrs')}</span>
          </div>
        </a>
      `;
    }).join('');

    // Checklist HTML
    const checklistHtml = (m.checklist || []).map((item, cIdx) => `
      <label class="flex items-start space-x-2 text-xs text-slate-700 cursor-pointer hover:text-slate-900">
        <input type="checkbox" onchange="toggleChecklistItem('${m.id}', ${cIdx}, this.checked)" class="mt-0.5 rounded text-indigo-600 focus:ring-indigo-500 rounded border-slate-300">
        <span>${escapeHtml(item)}</span>
      </label>
    `).join('');

    return `
      <div class="relative flex items-start space-x-4 sm:space-x-6 card-print">
        
        <!-- Sequential Timeline Node -->
        <button onclick="cycleMilestoneStatus('${m.id}')" title="Click to cycle status (Not Started -> In Progress -> Done)" class="relative z-10 w-9 h-9 rounded-full flex items-center justify-center font-bold text-xs text-white shrink-0 cursor-pointer transition transform hover:scale-110 ${nodeClass}">
          ${nodeIcon}
        </button>

        <!-- Milestone Card Body -->
        <div class="flex-1 bg-white rounded-2xl border ${isInProgress ? 'border-indigo-300 ring-2 ring-indigo-50 shadow-md' : 'border-slate-200 shadow-sm'} p-5 space-y-4">
          
          <!-- Header: Phase, Title, Duration, Status Toggle -->
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
            <div>
              <div class="text-[11px] font-bold text-indigo-600 uppercase tracking-wider">${escapeHtml(m.phase)}</div>
              <h3 class="text-base font-bold text-slate-900 mt-0.5">${escapeHtml(m.title)}</h3>
            </div>

            <div class="flex items-center space-x-2 self-start sm:self-auto">
              <span class="px-2.5 py-1 rounded-md text-xs font-semibold bg-slate-50 text-slate-600 border border-slate-200">
                🗓️ ${m.duration_days} days (${m.duration_hours} hrs)
              </span>
              
              <!-- Quick Status Selector -->
              <div class="relative inline-block">
                <button onclick="cycleMilestoneStatus('${m.id}')" class="cursor-pointer transition hover:opacity-80">
                  ${statusPill}
                </button>
              </div>
            </div>
          </div>

          <!-- Description -->
          <p class="text-xs sm:text-sm text-slate-600 leading-relaxed">
            ${escapeHtml(m.description)}
          </p>

          <!-- Deliverable (Project-based feature) -->
          ${m.project_deliverable ? `
            <div class="p-3 bg-indigo-50/50 rounded-xl border border-indigo-100 flex items-start space-x-2.5">
              <div class="p-1 bg-white rounded-md text-indigo-600 border border-indigo-200 shrink-0">
                <i data-lucide="package-check" class="w-4 h-4"></i>
              </div>
              <div>
                <div class="text-[11px] font-bold text-indigo-900 uppercase tracking-wider">Milestone Deliverable</div>
                <div class="text-xs text-slate-700 mt-0.5 font-medium">${escapeHtml(m.project_deliverable)}</div>
              </div>
            </div>
          ` : ''}

          <!-- Checklist Grid -->
          ${(m.checklist && m.checklist.length > 0) ? `
            <div class="space-y-1.5 pt-1">
              <div class="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Key Skills Checklist</div>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                ${checklistHtml}
              </div>
            </div>
          ` : ''}

          <!-- Free Resources Section -->
          <div class="space-y-2 pt-1">
            <div class="text-[11px] font-bold text-slate-500 uppercase tracking-wider flex items-center justify-between">
              <span>Free Curated Resources</span>
              <span class="text-[10px] text-slate-400 font-normal">Ranked & Time-Estimated</span>
            </div>
            <div class="space-y-2">
              ${resourcesHtml}
            </div>
          </div>

          <!-- Stretch Feature: Milestone Notes / Journal -->
          <div class="pt-2 border-t border-slate-100">
            <div class="flex items-center justify-between mb-1.5">
              <button onclick="toggleNotesEditor('${m.id}')" class="text-[11px] font-bold text-slate-500 hover:text-indigo-600 flex items-center space-x-1">
                <i data-lucide="pencil" class="w-3 h-3"></i>
                <span>${m.notes ? 'Edit My Journal / Notes' : '+ Add Milestone Reflection / Notes'}</span>
              </button>
              ${m.notes ? `<span class="text-[10px] text-emerald-600 font-semibold">✓ Note Recorded</span>` : ''}
            </div>

            <div id="notesSection_${m.id}" class="${m.notes ? '' : 'hidden'} space-y-2 mt-2">
              <textarea id="notesInput_${m.id}" rows="2" placeholder="Record what you built, breakthroughs, or roadblocks..." class="w-full p-2.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500">${escapeHtml(m.notes || '')}</textarea>
              <div class="flex justify-end">
                <button onclick="saveMilestoneNotes('${m.id}')" class="px-3 py-1 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-[11px] font-semibold transition">
                  Save Notes
                </button>
              </div>
            </div>
          </div>

        </div>

      </div>
    `;
  }).join('');

  if (window.lucide) window.lucide.createIcons();
}

// -------------------------------------------------------------
// VIEW 2: KANBAN BOARD RENDER
// -------------------------------------------------------------
function renderKanban() {
  if (!currentRoadmap) return;
  const notStarted = currentRoadmap.milestones.filter(m => m.status === 'not_started');
  const inProgress = currentRoadmap.milestones.filter(m => m.status === 'in_progress');
  const done = currentRoadmap.milestones.filter(m => m.status === 'done');

  document.getElementById('kanbanNotStartedCount').innerText = notStarted.length;
  document.getElementById('kanbanInProgressCount').innerText = inProgress.length;
  document.getElementById('kanbanDoneCount').innerText = done.length;

  const renderCol = (list, targetNext, nextLabel, nextColor) => {
    if (list.length === 0) {
      return `<div class="p-4 text-center text-xs text-slate-400 bg-white/60 rounded-xl border border-dashed border-slate-200">No items</div>`;
    }
    return list.map(m => `
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-2.5">
        <div class="text-[10px] font-bold text-indigo-600 uppercase tracking-wider">${escapeHtml(m.phase)}</div>
        <h5 class="text-xs font-bold text-slate-900">${escapeHtml(m.title)}</h5>
        <div class="text-[11px] text-slate-500 line-clamp-2">${escapeHtml(m.description)}</div>
        
        <div class="flex items-center justify-between pt-2 border-t border-slate-100 text-[10px]">
          <span class="text-slate-400">⏱️ ${m.duration_days}d</span>
          ${targetNext ? `
            <button onclick="updateMilestoneStatus('${m.id}', '${targetNext}')" class="px-2 py-1 ${nextColor} text-white font-bold rounded-md transition shadow-xs">
              ${nextLabel}
            </button>
          ` : `
            <button onclick="updateMilestoneStatus('${m.id}', 'in_progress')" class="px-2 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-md transition">
              Reopen
            </button>
          `}
        </div>
      </div>
    `).join('');
  };

  document.getElementById('kanbanNotStartedList').innerHTML = renderCol(notStarted, 'in_progress', 'Start →', 'bg-indigo-600 hover:bg-indigo-700');
  document.getElementById('kanbanInProgressList').innerHTML = renderCol(inProgress, 'done', 'Done ✓', 'bg-emerald-600 hover:bg-emerald-700');
  document.getElementById('kanbanDoneList').innerHTML = renderCol(done, null, '', '');
}

// -------------------------------------------------------------
// VIEW 3: PHASE SUMMARY RENDER
// -------------------------------------------------------------
function renderPhaseSummary() {
  if (!currentRoadmap) return;
  const container = document.getElementById('summaryView');

  // Group milestones by phase
  const phasesMap = {};
  currentRoadmap.milestones.forEach(m => {
    if (!phasesMap[m.phase]) {
      phasesMap[m.phase] = [];
    }
    phasesMap[m.phase].push(m);
  });

  container.innerHTML = Object.keys(phasesMap).map((phaseName, pIdx) => {
    const items = phasesMap[phaseName];
    const totalHours = items.reduce((acc, m) => acc + (m.duration_hours || 0), 0);
    const totalDays = items.reduce((acc, m) => acc + (m.duration_days || 0), 0);
    const completedCount = items.filter(m => m.status === 'done').length;
    const phasePct = Math.round((completedCount / items.length) * 100);

    return `
      <div class="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4 flex flex-col justify-between">
        <div class="space-y-2">
          <div class="flex items-center justify-between">
            <span class="px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded text-[10px] font-bold uppercase">Phase ${pIdx + 1}</span>
            <span class="text-xs font-bold ${phasePct === 100 ? 'text-emerald-600' : 'text-slate-600'}">${phasePct}% Done</span>
          </div>

          <h4 class="text-sm font-bold text-slate-900">${escapeHtml(phaseName)}</h4>

          <div class="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
            <div class="bg-indigo-600 h-1.5 rounded-full" style="width: ${phasePct}%"></div>
          </div>

          <div class="pt-2 text-xs text-slate-500 space-y-1">
            <div class="flex justify-between">
              <span>Milestones:</span>
              <span class="font-semibold text-slate-700">${completedCount} / ${items.length}</span>
            </div>
            <div class="flex justify-between">
              <span>Time Commitment:</span>
              <span class="font-semibold text-slate-700">${totalDays} days (~${totalHours} hrs)</span>
            </div>
          </div>
        </div>

        <div class="pt-3 border-t border-slate-100">
          <div class="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">Topics Included:</div>
          <ul class="text-[11px] text-slate-700 space-y-1">
            ${items.map(m => `<li class="flex items-center space-x-1.5 truncate">
              <span class="w-1.5 h-1.5 rounded-full ${m.status === 'done' ? 'bg-emerald-500' : 'bg-slate-300'}"></span>
              <span class="truncate">${escapeHtml(m.title)}</span>
            </li>`).join('')}
          </ul>
        </div>
      </div>
    `;
  }).join('');
}

// -------------------------------------------------------------
// STATUS TOGGLING & NOTES
// -------------------------------------------------------------
async function cycleMilestoneStatus(milestoneId) {
  if (!currentRoadmap) return;
  const m = currentRoadmap.milestones.find(item => item.id === milestoneId);
  if (!m) return;

  const nextStatus = m.status === 'not_started' ? 'in_progress' : (m.status === 'in_progress' ? 'done' : 'not_started');
  await updateMilestoneStatus(milestoneId, nextStatus);
}

async function updateMilestoneStatus(milestoneId, newStatus) {
  try {
    const res = await fetch(`/api/roadmaps/${currentRoadmap.id}/milestones/${milestoneId}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus }),
    });

    if (res.ok) {
      currentRoadmap = await res.json();
      renderRoadmapDashboard();

      // Confetti on milestone completion
      if (newStatus === 'done' && window.confetti) {
        window.confetti({ particleCount: 50, spread: 60, origin: { y: 0.7 } });
      }
    }
  } catch (err) {
    console.error('Failed to update status:', err);
  }
}

function toggleNotesEditor(milestoneId) {
  const el = document.getElementById(`notesSection_${milestoneId}`);
  if (el) el.classList.toggle('hidden');
}

async function saveMilestoneNotes(milestoneId) {
  const notesText = document.getElementById(`notesInput_${milestoneId}`)?.value || '';
  try {
    const res = await fetch(`/api/roadmaps/${currentRoadmap.id}/milestones/${milestoneId}/notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notes: notesText }),
    });
    if (res.ok) {
      currentRoadmap = await res.json();
      renderRoadmapDashboard();
      alert('Note saved to roadmap!');
    }
  } catch (err) {
    console.error('Failed to save notes:', err);
  }
}

function toggleChecklistItem(milestoneId, idx, checked) {
  // Save checkbox status in localStorage
  const key = `chk_${currentRoadmap.id}_${milestoneId}_${idx}`;
  localStorage.setItem(key, checked ? 'true' : 'false');
}

// -------------------------------------------------------------
// PROGRESS CHECK-IN FLOW
// -------------------------------------------------------------
function openCheckinModal() {
  if (!currentRoadmap) return;
  const select = document.getElementById('checkinMilestoneSelect');
  select.innerHTML = currentRoadmap.milestones.map(m => `
    <option value="${m.id}" ${m.status === 'in_progress' ? 'selected' : ''}>
      ${escapeHtml(m.title)} (${m.status.replace('_', ' ').toUpperCase()})
    </option>
  `).join('');

  document.getElementById('checkinStruggles').value = '';
  document.getElementById('checkinNotes').value = '';
  document.getElementById('checkinModal').classList.remove('hidden');
}

function closeCheckinModal() {
  document.getElementById('checkinModal').classList.add('hidden');
}

async function submitCheckin() {
  if (!currentRoadmap) return;
  const milestoneId = document.getElementById('checkinMilestoneSelect').value;
  const status = document.querySelector('input[name="checkinStatus"]:checked')?.value || 'done';
  const pace = document.querySelector('input[name="checkinPace"]:checked')?.value || 'on_track';
  const struggles = document.getElementById('checkinStruggles').value.trim();
  const notes = document.getElementById('checkinNotes').value.trim();

  const btn = document.getElementById('submitCheckinBtn');
  btn.disabled = true;
  btn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i><span>Saving...</span>`;
  if (window.lucide) window.lucide.createIcons();

  try {
    const res = await fetch(`/api/roadmaps/${currentRoadmap.id}/checkin`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        milestone_id: milestoneId,
        status: status,
        pace: pace,
        struggling_topics: struggles || null,
        notes: notes || null,
      }),
    });

    if (res.ok) {
      currentRoadmap = await res.json();
      closeCheckinModal();
      renderRoadmapDashboard();

      if (window.confetti && status === 'done') {
        window.confetti({ particleCount: 70, spread: 70, origin: { y: 0.6 } });
      }

      // If user indicated they are behind or struggling, proactively trigger AI adjustment prompt
      if (pace === 'behind' || struggles) {
        if (confirm(`You marked yourself as '${pace}' with '${struggles || 'challenges'}'. Would you like PathPulse AI to automatically adjust and reorganize your remaining roadmap?`)) {
          openAdjustModal(pace, struggles);
        }
      }
    }
  } catch (err) {
    alert('Check-in error: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="check" class="w-4 h-4"></i><span>Save & Check-In</span>`;
    if (window.lucide) window.lucide.createIcons();
  }
}

// -------------------------------------------------------------
// AI ROADMAP ADJUSTMENT (WHAT CHANGED & WHY)
// -------------------------------------------------------------
function openAdjustModal(defaultPace = 'behind', defaultStruggles = '') {
  const paceRadio = document.querySelector(`input[name="adjustPace"][value="${defaultPace}"]`);
  if (paceRadio) {
    paceRadio.checked = true;
    paceRadio.closest('.adjust-pace-card')?.click();
  }
  document.getElementById('adjustStruggles').value = defaultStruggles;
  document.getElementById('adjustFeedback').value = '';
  document.getElementById('adjustModal').classList.remove('hidden');
}

function closeAdjustModal() {
  document.getElementById('adjustModal').classList.add('hidden');
}

async function submitRoadmapAdjustment() {
  if (!currentRoadmap) return;
  const pace = document.querySelector('input[name="adjustPace"]:checked')?.value || 'behind';
  const struggles = document.getElementById('adjustStruggles').value.trim();
  const feedback = document.getElementById('adjustFeedback').value.trim();

  const btn = document.getElementById('submitAdjustBtn');
  btn.disabled = true;
  btn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i><span>Mentor Re-planning...</span>`;
  if (window.lucide) window.lucide.createIcons();

  try {
    const res = await fetch(`/api/roadmaps/${currentRoadmap.id}/adjust`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        pace: pace,
        struggling_topics: struggles || null,
        general_feedback: feedback || null,
        api_key: appSettings.apiKey || null,
        ai_provider: appSettings.provider || 'gemini',
      }),
    });

    if (!res.ok) throw new Error('Failed to adjust roadmap');

    currentRoadmap = await res.json();
    closeAdjustModal();
    renderRoadmapDashboard();
    openAdjustmentHistoryModal(); // Automatically showcase WHAT changed and WHY!
  } catch (err) {
    alert('Adjustment error: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="refresh-cw" class="w-4 h-4"></i><span>Re-Plan Roadmap</span>`;
    if (window.lucide) window.lucide.createIcons();
  }
}

function openAdjustmentHistoryModal() {
  if (!currentRoadmap) return;
  const container = document.getElementById('historyListContainer');
  const logs = currentRoadmap.adjustment_logs || [];

  if (logs.length === 0) {
    container.innerHTML = `<div class="p-4 text-center text-slate-400">No adjustments recorded yet.</div>`;
  } else {
    container.innerHTML = logs.map((l, idx) => `
      <div class="py-3 space-y-2">
        <div class="flex items-center justify-between">
          <span class="px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded text-[10px] font-bold uppercase">
            ${l.pace.toUpperCase()} ADAPTATION
          </span>
          <span class="text-[10px] text-slate-400">${new Date(l.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
        </div>

        <div class="font-bold text-slate-900">${escapeHtml(l.summary)}</div>
        <p class="text-slate-600 italic bg-slate-50 p-2.5 rounded-lg border border-slate-100">
          "${escapeHtml(l.reasons)}"
        </p>

        ${(l.details && l.details.length > 0) ? `
          <div class="space-y-1">
            <div class="text-[10px] font-bold text-slate-500 uppercase">Specific Modifications:</div>
            <ul class="list-disc list-inside text-slate-700 space-y-0.5">
              ${l.details.map(d => `<li>${escapeHtml(d)}</li>`).join('')}
            </ul>
          </div>
        ` : ''}
      </div>
    `).join('');
  }

  document.getElementById('historyModal').classList.remove('hidden');
}

function closeAdjustmentHistoryModal() {
  document.getElementById('historyModal').classList.add('hidden');
}

// -------------------------------------------------------------
// LEARNING STYLE TOGGLING (PROJECT-BASED VS THEORY-FIRST)
// -------------------------------------------------------------
async function toggleStyleMode(newStyle) {
  if (!currentRoadmap || currentRoadmap.learning_style === newStyle) return;

  const confirmMsg = `Switching learning style to ${newStyle.toUpperCase()} will rebuild milestones to emphasize ${newStyle === 'project-based' ? 'hands-on projects' : 'deep theory and CS principles'}. Proceed?`;
  if (!confirm(confirmMsg)) return;

  try {
    const res = await fetch(`/api/roadmaps/${currentRoadmap.id}/toggle-style`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        learning_style: newStyle,
        api_key: appSettings.apiKey || null,
        ai_provider: appSettings.provider || 'gemini',
      }),
    });

    if (res.ok) {
      currentRoadmap = await res.json();
      renderRoadmapDashboard();
      if (window.confetti) {
        window.confetti({ particleCount: 40, spread: 60 });
      }
    }
  } catch (err) {
    alert('Failed to switch style: ' + err.message);
  }
}

// -------------------------------------------------------------
// BADGES & STREAKS GAMIFICATION
// -------------------------------------------------------------
function openBadgesModal() {
  if (!currentRoadmap) return;
  const container = document.getElementById('badgesContainer');
  const earned = currentRoadmap.badges_earned || [];

  const allBadges = [
    { name: 'Roadmap Initiated 🎯', desc: 'Crafted your tailored learning plan' },
    { name: 'First Step Taken ⚡', desc: 'Completed your first learning milestone' },
    { name: 'Halfway Hero 🚀', desc: 'Reached 50% roadmap completion' },
    { name: 'Resilient Learner 🛡️', desc: 'Adjusted and conquered after falling behind' },
    { name: 'Reflective Scholar 📝', desc: 'Recorded thoughts in milestone journal' },
    { name: 'Style Explorer 🔄', desc: 'Explored multiple learning styles' },
    { name: 'Mastery Unlocked 🎓', desc: '100% roadmap completed!' },
  ];

  container.innerHTML = allBadges.map(b => {
    const isEarned = earned.includes(b.name);
    return `
      <div class="p-3 rounded-xl border ${isEarned ? 'bg-amber-50/70 border-amber-200' : 'bg-slate-50 border-slate-100 opacity-50'} flex items-start space-x-2.5">
        <div class="text-xl shrink-0">${isEarned ? '🏆' : '🔒'}</div>
        <div>
          <div class="font-bold text-slate-900 ${isEarned ? 'text-amber-900' : 'text-slate-500'}">${escapeHtml(b.name)}</div>
          <div class="text-[10px] text-slate-500 mt-0.5">${escapeHtml(b.desc)}</div>
        </div>
      </div>
    `;
  }).join('');

  document.getElementById('badgesModal').classList.remove('hidden');
}

function closeBadgesModal() {
  document.getElementById('badgesModal').classList.add('hidden');
}

// -------------------------------------------------------------
// SETTINGS MODAL
// -------------------------------------------------------------
function openSettingsModal() {
  document.getElementById('settingProvider').value = appSettings.provider;
  document.getElementById('settingApiKey').value = appSettings.apiKey;
  document.getElementById('settingsModal').classList.remove('hidden');
}

function closeSettingsModal() {
  document.getElementById('settingsModal').classList.add('hidden');
}

function saveSettings() {
  const provider = document.getElementById('settingProvider').value;
  const key = document.getElementById('settingApiKey').value.trim();
  appSettings.provider = provider;
  appSettings.apiKey = key;
  localStorage.setItem('pathpulse_provider', provider);
  localStorage.setItem('pathpulse_api_key', key);
  closeSettingsModal();
  alert('Settings saved!');
}

function loadSettings() {
  const prov = localStorage.getItem('pathpulse_provider');
  const key = localStorage.getItem('pathpulse_api_key');
  if (prov) appSettings.provider = prov;
  if (key) appSettings.apiKey = key;
}

// -------------------------------------------------------------
// SHARING & EXPORT
// -------------------------------------------------------------
function openShareModal() {
  if (!currentRoadmap) return;
  const shareUrl = `${window.location.origin}/api/roadmaps/${currentRoadmap.id}/share`;
  document.getElementById('shareUrlInput').value = shareUrl;
  document.getElementById('shareModal').classList.remove('hidden');
}

function closeShareModal() {
  document.getElementById('shareModal').classList.add('hidden');
}

function copyShareUrl() {
  const input = document.getElementById('shareUrlInput');
  input.select();
  navigator.clipboard.writeText(input.value);
  const btn = document.getElementById('copyShareBtn');
  btn.innerText = 'Copied!';
  setTimeout(() => { btn.innerText = 'Copy'; }, 2000);
}

function exportMarkdown() {
  if (!currentRoadmap) return;
  window.open(`/api/roadmaps/${currentRoadmap.id}/export/markdown`, '_blank');
}

// -------------------------------------------------------------
// HELPERS
// -------------------------------------------------------------
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
