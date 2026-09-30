/**
 * ZONATA — Universal SaaS Schedule & Planning Workspace
 * Production planning layer connecting AI CEO, missions, TaskMaker, processes,
 * workforce, financial deadlines, and robotic desktop execution.
 */

(function() {
  'use strict';

  class ScheduleWorkspaceManager {
    constructor() {
      this.currentView = 'month'; // 'month' | 'week' | 'day' | 'timeline' | 'agenda'
      this.currentDate = new Date();
      this.typeFilter = 'all';
      this.priorityFilter = 'all';
      this.schedules = [];
      this.recommendations = [];
      this.loading = false;
      this.selectedItem = null;
    }

    async render(containerId = 'view-schedule') {
      const container = document.getElementById(containerId);
      if (!container) return;

      this.loading = true;
      this.renderLoading(container);

      try {
        await Promise.all([
          this.fetchSchedules(),
          this.fetchRecommendations()
        ]);
        this.renderWorkspace(container);
      } catch (err) {
        console.error('[ScheduleWorkspace] Error loading schedules:', err);
        container.innerHTML = `
          <div style="padding:40px; text-align:center;">
            <h3>Unable to load Universal Schedule</h3>
            <p style="color:var(--text-muted);">${err.message || 'Check network connection'}</p>
            <button class="btn-primary" onclick="window.ScheduleWorkspace.render()">Retry</button>
          </div>
        `;
      } finally {
        this.loading = false;
      }
    }

    async fetchSchedules() {
      const companyId = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : null;
      let url = '/api/schedules';
      const params = [];
      if (companyId) params.push(`company_id=${encodeURIComponent(companyId)}`);
      if (this.typeFilter !== 'all') params.push(`item_type=${encodeURIComponent(this.typeFilter)}`);
      if (this.priorityFilter !== 'all') params.push(`priority=${encodeURIComponent(this.priorityFilter)}`);
      if (params.length > 0) url += '?' + params.join('&');

      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        this.schedules = data.schedules || [];
      }
    }

    async fetchRecommendations() {
      const companyId = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : null;
      const url = companyId ? `/api/schedules/recommendations?company_id=${encodeURIComponent(companyId)}` : '/api/schedules/recommendations';
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        this.recommendations = data.recommendations || [];
      }
    }

    renderLoading(container) {
      container.innerHTML = `
        <div style="padding:40px; text-align:center;">
          <div class="status-pulse-dot" style="margin:0 auto 12px; width:14px; height:14px;"></div>
          <div style="font-size:14px; color:var(--text-secondary);">Loading Universal SaaS Schedule...</div>
        </div>
      `;
    }

    renderWorkspace(container) {
      const dateTitle = this.getDateDisplayTitle();
      const companyContextName = window.CurrentCompanyContext && window.CurrentCompanyContext.getCompanyName 
        ? window.CurrentCompanyContext.getCompanyName() 
        : 'All Authorized Companies';

      container.innerHTML = `
        <div class="schedule-workspace-layout" style="display:flex; flex-direction:column; gap:20px; max-width:1440px; margin:0 auto; padding-bottom:60px;">
          
          <!-- 1. Executive Schedule Header -->
          <div class="schedule-header-card" style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px 24px; display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px;">
            <div>
              <div style="display:flex; align-items:center; gap:10px; margin-bottom:6px;">
                <span class="badge badge-blue" style="font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">Universal Planning</span>
                <span style="font-size:12px; color:var(--accent-emerald); font-weight:600; display:inline-flex; align-items:center; gap:6px;">
                  <span class="status-pulse-dot" style="background:var(--accent-emerald);"></span>
                  Autonomous Collision Detection Active
                </span>
              </div>
              <h1 style="font-size:24px; font-weight:700; color:var(--text-primary); margin:0 0 4px 0; display:flex; align-items:center; gap:12px;">
                <span>Universal Schedule</span>
                <span style="font-size:13px; font-weight:500; color:var(--text-muted); background:var(--bg-surface-hover); padding:3px 10px; border-radius:var(--radius-sm); border:1px solid var(--border-color);">
                  ${companyContextName}
                </span>
              </h1>
              <p style="font-size:13px; color:var(--text-secondary); margin:0;">
                SaaS-wide operating schedule synchronizing AI CEO, workforce shifts, mission milestones, and robotic desktop runs.
              </p>
            </div>

            <!-- Top Actions -->
            <div style="display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
              <button class="btn-secondary" onclick="window.ScheduleWorkspace.openRecommendationsModal()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>
                AI CEO Suggestions (${this.recommendations.length})
              </button>
              <button class="btn-primary" onclick="window.ScheduleWorkspace.openCreateModal()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                + New Schedule Item
              </button>
            </div>
          </div>

          <!-- 2. Natural Language Quick Scheduler -->
          <div class="nl-scheduler-card" style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:16px 20px;">
            <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
              <span style="font-size:16px;">⚡</span>
              <span style="font-size:13px; font-weight:700; color:var(--text-primary);">Natural Language Quick Scheduler</span>
              <span style="font-size:12px; color:var(--text-muted);">(e.g. "Review Q3 marketing budget next Monday at 10am" or "Night audit process run tomorrow 2am")</span>
            </div>
            <div style="display:flex; gap:10px; flex-wrap:wrap;">
              <input type="text" id="nlScheduleInput" class="form-input" style="flex:1; min-width:260px; padding:10px 14px; font-size:13.5px;" placeholder="Type scheduling prompt in plain English..." onkeydown="if(event.key==='Enter') window.ScheduleWorkspace.parseNaturalLanguage()" />
              <button class="btn-secondary" style="white-space:nowrap; padding:0 18px;" onclick="window.ScheduleWorkspace.parseNaturalLanguage()">
                Parse & Schedule
              </button>
            </div>
          </div>

          <!-- 3. Navigation, Filters & View Selectors Toolbar -->
          <div class="schedule-toolbar" style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:14px 18px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px;">
            
            <!-- Left: Date Navigator -->
            <div style="display:flex; align-items:center; gap:10px;">
              <div class="btn-group" style="display:flex; border:1px solid var(--border-color); border-radius:var(--radius-md); overflow:hidden;">
                <button class="btn-secondary" style="border:none; border-radius:0; padding:6px 12px;" onclick="window.ScheduleWorkspace.navigateDate(-1)" title="Previous">
                  ◀
                </button>
                <button class="btn-secondary" style="border:none; border-radius:0; padding:6px 12px; font-weight:600;" onclick="window.ScheduleWorkspace.navigateToday()">
                  Today
                </button>
                <button class="btn-secondary" style="border:none; border-radius:0; padding:6px 12px;" onclick="window.ScheduleWorkspace.navigateDate(1)" title="Next">
                  ▶
                </button>
              </div>
              <h2 style="font-size:16px; font-weight:700; color:var(--text-primary); margin:0;">
                ${dateTitle}
              </h2>
            </div>

            <!-- Center: Filters -->
            <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
              <select class="form-input" style="padding:6px 10px; font-size:12.5px; width:auto;" onchange="window.ScheduleWorkspace.setTypeFilter(this.value)">
                <option value="all" ${this.typeFilter==='all'?'selected':''}>All 15 Item Types</option>
                <option value="meeting" ${this.typeFilter==='meeting'?'selected':''}>Executive Meetings</option>
                <option value="mission_milestone" ${this.typeFilter==='mission_milestone'?'selected':''}>Mission Milestones</option>
                <option value="deadline" ${this.typeFilter==='deadline'?'selected':''}>Deadlines</option>
                <option value="process_run" ${this.typeFilter==='process_run'?'selected':''}>Process Runs</option>
                <option value="budget_review" ${this.typeFilter==='budget_review'?'selected':''}>Budget Reviews</option>
                <option value="approval_deadline" ${this.typeFilter==='approval_deadline'?'selected':''}>Approval Deadlines</option>
                <option value="coworker_task" ${this.typeFilter==='coworker_task'?'selected':''}>Coworker Tasks</option>
                <option value="ai_workforce_shift" ${this.typeFilter==='ai_workforce_shift'?'selected':''}>Workforce Shifts</option>
                <option value="customer_touchpoint" ${this.typeFilter==='customer_touchpoint'?'selected':''}>Customer Touchpoints</option>
                <option value="report_generation" ${this.typeFilter==='report_generation'?'selected':''}>Report Generations</option>
                <option value="reminder" ${this.typeFilter==='reminder'?'selected':''}>Reminders</option>
                <option value="maintenance" ${this.typeFilter==='maintenance'?'selected':''}>Maintenance</option>
                <option value="compliance_audit" ${this.typeFilter==='compliance_audit'?'selected':''}>Compliance Audits</option>
                <option value="desktop_automation" ${this.typeFilter==='desktop_automation'?'selected':''}>Desktop Automation</option>
                <option value="strategic_review" ${this.typeFilter==='strategic_review'?'selected':''}>Strategic Reviews</option>
              </select>

              <select class="form-input" style="padding:6px 10px; font-size:12.5px; width:auto;" onchange="window.ScheduleWorkspace.setPriorityFilter(this.value)">
                <option value="all" ${this.priorityFilter==='all'?'selected':''}>All Priorities</option>
                <option value="LOW" ${this.priorityFilter==='LOW'?'selected':''}>Low Priority</option>
                <option value="MEDIUM" ${this.priorityFilter==='MEDIUM'?'selected':''}>Medium Priority</option>
                <option value="HIGH" ${this.priorityFilter==='HIGH'?'selected':''}>High Priority</option>
                <option value="URGENT" ${this.priorityFilter==='URGENT'?'selected':''}>Urgent</option>
              </select>
            </div>

            <!-- Right: 5 Calendar Views Pill Group -->
            <div class="view-pill-group" style="display:flex; border:1px solid var(--border-color); border-radius:var(--radius-md); overflow:hidden;">
              ${[
                { id: 'month', label: 'Month' },
                { id: 'week', label: 'Week' },
                { id: 'day', label: 'Day' },
                { id: 'timeline', label: 'Timeline / Gantt' },
                { id: 'agenda', label: 'Agenda' }
              ].map(v => `
                <button 
                  class="btn-view-toggle ${this.currentView === v.id ? 'active' : ''}" 
                  style="border:none; border-radius:0; padding:6px 12px; font-size:12.5px; font-weight:600; background:${this.currentView===v.id?'var(--accent-blue)':'transparent'}; color:${this.currentView===v.id?'#fff':'var(--text-secondary)'}; cursor:pointer;" 
                  onclick="window.ScheduleWorkspace.switchView('${v.id}')">
                  ${v.label}
                </button>
              `).join('')}
            </div>
          </div>

          <!-- 4. Active View Canvas -->
          <div class="schedule-canvas-container" style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px; min-height:480px;">
            ${this.renderActiveViewContent()}
          </div>
        </div>
      `;
    }

    getDateDisplayTitle() {
      const opts = { month: 'long', year: 'numeric' };
      if (this.currentView === 'day') {
        return this.currentDate.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
      }
      return this.currentDate.toLocaleDateString(undefined, opts);
    }

    switchView(viewId) {
      this.currentView = viewId;
      this.render();
    }

    setTypeFilter(val) {
      this.typeFilter = val;
      this.render();
    }

    setPriorityFilter(val) {
      this.priorityFilter = val;
      this.render();
    }

    navigateDate(delta) {
      if (this.currentView === 'month' || this.currentView === 'timeline') {
        this.currentDate.setMonth(this.currentDate.getMonth() + delta);
      } else if (this.currentView === 'week') {
        this.currentDate.setDate(this.currentDate.getDate() + (delta * 7));
      } else {
        this.currentDate.setDate(this.currentDate.getDate() + delta);
      }
      this.render();
    }

    navigateToday() {
      this.currentDate = new Date();
      this.render();
    }

    renderActiveViewContent() {
      switch (this.currentView) {
        case 'week':
          return this.renderWeekView();
        case 'day':
          return this.renderDayView();
        case 'timeline':
          return this.renderTimelineView();
        case 'agenda':
          return this.renderAgendaView();
        case 'month':
        default:
          return this.renderMonthView();
      }
    }

    // =========================================================================
    // View 1: Month View
    // =========================================================================
    renderMonthView() {
      const year = this.currentDate.getFullYear();
      const month = this.currentDate.getMonth();
      const firstDay = new Date(year, month, 1).getDay();
      const totalDays = new Date(year, month + 1, 0).getDate();

      const daysOfWeek = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

      let cellsHtml = '';
      // Empty leading cells
      for (let i = 0; i < firstDay; i++) {
        cellsHtml += `<div class="calendar-day-cell empty" style="min-height:90px; background:var(--bg-surface-hover); opacity:0.3; border:1px solid var(--border-color); border-radius:var(--radius-sm);"></div>`;
      }

      const today = new Date();
      for (let d = 1; d <= totalDays; d++) {
        const cellDate = new Date(year, month, d);
        const isToday = cellDate.toDateString() === today.toDateString();
        
        // Find matching schedules for this day
        const dayStartTs = new Date(year, month, d, 0, 0, 0).getTime() / 1000;
        const dayEndTs = new Date(year, month, d, 23, 59, 59).getTime() / 1000;

        const dayItems = this.schedules.filter(s => s.start_time >= dayStartTs && s.start_time <= dayEndTs);

        cellsHtml += `
          <div class="calendar-day-cell ${isToday ? 'today' : ''}" style="min-height:90px; border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:6px; background:${isToday ? 'rgba(37,99,235,0.06)' : 'var(--bg-surface)'}; display:flex; flex-direction:column; gap:4px; overflow:hidden;">
            <div style="display:flex; justify-content:space-between; align-items:center; font-size:12px; font-weight:700; color:${isToday ? 'var(--accent-blue)' : 'var(--text-secondary)'};">
              <span>${d}</span>
              ${dayItems.length > 0 ? `<span style="font-size:10px; background:var(--bg-surface-hover); padding:1px 5px; border-radius:10px;">${dayItems.length}</span>` : ''}
            </div>
            <div class="day-events-list" style="display:flex; flex-direction:column; gap:3px; overflow-y:auto; max-height:80px;">
              ${dayItems.map(item => this.renderEventPill(item)).join('')}
            </div>
          </div>
        `;
      }

      return `
        <div class="horizontal-scroll-container">
          <div class="month-calendar-grid" style="display:grid; grid-template-columns:repeat(7, minmax(110px, 1fr)); gap:6px;">
            ${daysOfWeek.map(w => `
              <div style="text-align:center; font-size:12px; font-weight:700; color:var(--text-muted); padding:6px 0; text-transform:uppercase;">
                ${w}
              </div>
            `).join('')}
            ${cellsHtml}
          </div>
        </div>
      `;
    }

    // =========================================================================
    // View 2: Week View
    // =========================================================================
    renderWeekView() {
      const startOfWeek = new Date(this.currentDate);
      startOfWeek.setDate(this.currentDate.getDate() - this.currentDate.getDay());

      const weekDays = [];
      for (let i = 0; i < 7; i++) {
        const d = new Date(startOfWeek);
        d.setDate(startOfWeek.getDate() + i);
        weekDays.push(d);
      }

      return `
        <div class="horizontal-scroll-container">
          <div style="display:grid; grid-template-columns:repeat(7, minmax(130px, 1fr)); gap:8px;">
            ${weekDays.map(d => {
              const dayStart = new Date(d.getFullYear(), d.getMonth(), d.getDate(), 0, 0, 0).getTime() / 1000;
              const dayEnd = new Date(d.getFullYear(), d.getMonth(), d.getDate(), 23, 59, 59).getTime() / 1000;
              const dayItems = this.schedules.filter(s => s.start_time >= dayStart && s.start_time <= dayEnd);
              const isToday = d.toDateString() === new Date().toDateString();

              return `
                <div class="week-column" style="border:1px solid var(--border-color); border-radius:var(--radius-md); padding:10px; background:${isToday ? 'rgba(37,99,235,0.04)' : 'var(--bg-surface)'};">
                  <div style="text-align:center; border-bottom:1px solid var(--border-color); padding-bottom:8px; margin-bottom:10px;">
                    <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">
                      ${d.toLocaleDateString(undefined, { weekday: 'short' })}
                    </div>
                    <div style="font-size:18px; font-weight:700; color:${isToday ? 'var(--accent-blue)' : 'var(--text-primary)'};">
                      ${d.getDate()}
                    </div>
                  </div>
                  <div style="display:flex; flex-direction:column; gap:6px; min-height:260px;">
                    ${dayItems.length === 0 ? '<div style="font-size:11.5px; color:var(--text-muted); text-align:center; margin-top:20px;">No events</div>' : ''}
                    ${dayItems.map(item => this.renderEventPill(item, true)).join('')}
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      `;
    }

    // =========================================================================
    // View 3: Day View
    // =========================================================================
    renderDayView() {
      const year = this.currentDate.getFullYear();
      const month = this.currentDate.getMonth();
      const date = this.currentDate.getDate();

      const dayStart = new Date(year, month, date, 0, 0, 0).getTime() / 1000;
      const dayEnd = new Date(year, month, date, 23, 59, 59).getTime() / 1000;

      const dayItems = this.schedules.filter(s => s.start_time >= dayStart && s.start_time <= dayEnd);

      const hours = Array.from({ length: 24 }, (_, i) => i);

      return `
        <div class="horizontal-scroll-container">
          <div style="min-width:600px; display:flex; flex-direction:column; gap:4px;">
            ${hours.map(h => {
              const hStart = new Date(year, month, date, h, 0, 0).getTime() / 1000;
              const hEnd = new Date(year, month, date, h, 59, 59).getTime() / 1000;
              const matching = dayItems.filter(s => s.start_time >= hStart && s.start_time <= hEnd);

              const formattedHour = h === 0 ? '12 AM' : h < 12 ? `${h} AM` : h === 12 ? '12 PM' : `${h - 12} PM`;

              return `
                <div style="display:flex; border-bottom:1px solid var(--border-color); padding:8px 0; align-items:flex-start; min-height:46px;">
                  <div style="width:70px; font-size:12px; color:var(--text-muted); font-weight:600;">
                    ${formattedHour}
                  </div>
                  <div style="flex:1; display:flex; flex-direction:column; gap:4px;">
                    ${matching.map(item => this.renderEventPill(item, true)).join('')}
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      `;
    }

    // =========================================================================
    // View 4: Timeline / Gantt View
    // =========================================================================
    renderTimelineView() {
      const sorted = [...this.schedules].sort((a, b) => a.start_time - b.start_time);

      if (sorted.length === 0) {
        return `<div style="text-align:center; padding:40px; color:var(--text-muted);">No timeline items in current scope.</div>`;
      }

      return `
        <div class="horizontal-scroll-container">
          <div style="min-width:740px;">
            <div style="display:grid; grid-template-columns:220px 1fr 100px 90px; padding:10px 14px; font-size:12px; font-weight:700; color:var(--text-muted); text-transform:uppercase; border-bottom:2px solid var(--border-color);">
              <div>Schedule Item</div>
              <div>Timeline / Gantt Span</div>
              <div>Priority</div>
              <div>Actions</div>
            </div>

            <div style="display:flex; flex-direction:column; gap:8px; margin-top:10px;">
              ${sorted.map(s => {
                const sDate = new Date(s.start_time * 1000);
                const eDate = s.end_time ? new Date(s.end_time * 1000) : sDate;
                const timeStr = `${sDate.toLocaleDateString(undefined, {month:'short', day:'numeric'})} ${sDate.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}`;

                return `
                  <div style="display:grid; grid-template-columns:220px 1fr 100px 90px; padding:10px 14px; background:var(--bg-surface-hover); border:1px solid var(--border-color); border-radius:var(--radius-md); align-items:center;">
                    <div>
                      <div style="font-size:13px; font-weight:700; color:var(--text-primary);">${this.escape(s.title)}</div>
                      <div style="font-size:11px; color:var(--text-muted);">${s.item_type} • ${s.assigned_to || 'AI CEO'}</div>
                    </div>
                    <div style="padding-right:16px;">
                      <div style="background:rgba(37,99,235,0.15); border-left:3px solid var(--accent-blue); padding:6px 12px; border-radius:var(--radius-sm); font-size:11.5px; color:var(--text-primary);">
                        📅 ${timeStr} → ${eDate.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}
                        ${s.conflict_detected ? `<span style="color:#ef4444; margin-left:8px; font-weight:700;">⚠️ Collision</span>` : ''}
                      </div>
                    </div>
                    <div>
                      <span class="badge ${this.getPriorityBadge(s.priority)}">${s.priority}</span>
                    </div>
                    <div>
                      <button class="btn-secondary" style="font-size:11.5px; padding:4px 8px;" onclick="window.ScheduleWorkspace.viewDetails('${s.schedule_id}')">
                        Inspect
                      </button>
                    </div>
                  </div>
                `;
              }).join('')}
            </div>
          </div>
        </div>
      `;
    }

    // =========================================================================
    // View 5: Agenda List View
    // =========================================================================
    renderAgendaView() {
      const sorted = [...this.schedules].sort((a, b) => a.start_time - b.start_time);

      if (sorted.length === 0) {
        return `<div style="text-align:center; padding:40px; color:var(--text-muted);">No agenda items scheduled.</div>`;
      }

      return `
        <div style="display:flex; flex-direction:column; gap:12px;">
          ${sorted.map(s => {
            const dt = new Date(s.start_time * 1000);
            const dateStr = dt.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
            const timeStr = dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

            return `
              <div class="agenda-item-card" style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:14px 18px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                <div style="display:flex; align-items:center; gap:14px;">
                  <div style="text-align:center; background:var(--bg-surface-hover); padding:8px 12px; border-radius:var(--radius-md); border:1px solid var(--border-color); min-width:64px;">
                    <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">${dt.toLocaleDateString(undefined, {month:'short'})}</div>
                    <div style="font-size:18px; font-weight:800; color:var(--text-primary);">${dt.getDate()}</div>
                  </div>
                  <div>
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                      <span style="font-size:14px; font-weight:700; color:var(--text-primary);">${this.escape(s.title)}</span>
                      <span class="badge ${this.getPriorityBadge(s.priority)}">${s.priority}</span>
                      <span class="badge badge-subtle">${s.item_type}</span>
                    </div>
                    <div style="font-size:12.5px; color:var(--text-secondary);">
                      🕒 ${timeStr} • Assigned: <strong>${this.escape(s.assigned_to || 'AI CEO')}</strong>
                      ${s.description ? ` • ${this.escape(s.description.substring(0, 70))}...` : ''}
                    </div>
                    ${s.conflict_detected ? `
                      <div style="font-size:11.5px; color:#ef4444; margin-top:4px; font-weight:600;">
                        ⚠️ Conflict Warning: ${this.escape(s.conflict_reason || 'Overlap with high-priority item')}
                      </div>
                    ` : ''}
                  </div>
                </div>

                <div style="display:flex; gap:8px;">
                  <button class="btn-secondary" style="font-size:12px; padding:6px 12px;" onclick="window.ScheduleWorkspace.viewDetails('${s.schedule_id}')">
                    Inspect
                  </button>
                  <button class="btn-secondary" style="font-size:12px; padding:6px 12px; color:#ef4444;" onclick="window.ScheduleWorkspace.deleteItem('${s.schedule_id}')">
                    Delete
                  </button>
                </div>
              </div>
            `;
          }).join('')}
        </div>
      `;
    }

    renderEventPill(item, detailed = false) {
      const typeColor = this.getItemTypeColor(item.item_type);
      const isConflict = item.conflict_detected;

      return `
        <div 
          class="event-chip ${isConflict ? 'has-conflict' : ''}" 
          style="background:${typeColor.bg}; border-left:3px solid ${isConflict ? '#ef4444' : typeColor.border}; padding:3px 6px; border-radius:3px; font-size:11px; cursor:pointer; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" 
          onclick="window.ScheduleWorkspace.viewDetails('${item.schedule_id}')" 
          title="${this.escape(item.title)} (${item.item_type})">
          <span style="font-weight:700; color:${typeColor.text};">${this.escape(item.title)}</span>
          ${detailed ? `<div style="font-size:10px; color:var(--text-muted);">${new Date(item.start_time*1000).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</div>` : ''}
        </div>
      `;
    }

    getItemTypeColor(type) {
      switch (type) {
        case 'meeting':
        case 'strategic_review':
          return { bg: 'rgba(124, 58, 237, 0.15)', border: '#7c3aed', text: '#a78bfa' };
        case 'budget_review':
          return { bg: 'rgba(16, 185, 129, 0.15)', border: '#10b981', text: '#34d399' };
        case 'deadline':
        case 'approval_deadline':
          return { bg: 'rgba(239, 68, 68, 0.15)', border: '#ef4444', text: '#f87171' };
        case 'desktop_automation':
        case 'coworker_task':
          return { bg: 'rgba(245, 158, 11, 0.15)', border: '#f59e0b', text: '#fbbf24' };
        case 'process_run':
        case 'maintenance':
          return { bg: 'rgba(59, 130, 246, 0.15)', border: '#3b82f6', text: '#60a5fa' };
        default:
          return { bg: 'rgba(107, 114, 128, 0.15)', border: '#6b7280', text: '#9ca3af' };
      }
    }

    getPriorityBadge(priority) {
      switch (priority) {
        case 'URGENT': return 'badge-rose';
        case 'HIGH': return 'badge-amber';
        case 'MEDIUM': return 'badge-blue';
        case 'LOW':
        default: return 'badge-subtle';
      }
    }

    async parseNaturalLanguage() {
      const input = document.getElementById('nlScheduleInput');
      if (!input || !input.value.trim()) return;

      const text = input.value.trim();
      const companyId = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : 'comp_primary';

      try {
        const res = await fetch('/api/schedules/parse-nl', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text, company_id: companyId })
        });

        if (res.ok) {
          const parsed = await res.json();
          // Open create modal prepopulated with parsed data
          this.openCreateModal(parsed);
          input.value = '';
        } else {
          alert('Could not parse natural language schedule.');
        }
      } catch (err) {
        console.error('Failed to parse NL schedule:', err);
      }
    }

    openCreateModal(initial = null) {
      const modalBody = document.getElementById('modalBody');
      const modalTitle = document.getElementById('modalTitle');
      const overlay = document.getElementById('modalOverlay');

      if (!modalBody || !overlay) return;

      const companyId = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : 'comp_primary';

      const now = new Date();
      now.setHours(now.getHours() + 1, 0, 0, 0);
      const defaultStart = initial ? new Date(initial.start_time * 1000).toISOString().slice(0, 16) : now.toISOString().slice(0, 16);
      const defaultEnd = initial ? new Date(initial.end_time * 1000).toISOString().slice(0, 16) : new Date(now.getTime() + 3600000).toISOString().slice(0, 16);

      modalTitle.textContent = initial ? 'Confirm Parsed Schedule' : 'Create New Schedule Item';
      modalBody.innerHTML = `
        <form id="createScheduleForm" onsubmit="event.preventDefault(); window.ScheduleWorkspace.submitCreateForm();" style="display:flex; flex-direction:column; gap:14px;">
          <div class="form-group">
            <label class="form-label">Schedule Item Title</label>
            <input type="text" id="schFormTitle" class="form-input" value="${this.escape(initial ? initial.title : '')}" placeholder="e.g. Q3 Strategic Operations Review" required />
          </div>

          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div class="form-group">
              <label class="form-label">Item Type (15 Categories)</label>
              <select id="schFormType" class="form-input">
                <option value="meeting" ${initial?.item_type==='meeting'?'selected':''}>Executive Meeting</option>
                <option value="mission_milestone" ${initial?.item_type==='mission_milestone'?'selected':''}>Mission Milestone</option>
                <option value="deadline" ${initial?.item_type==='deadline'?'selected':''}>Deadline</option>
                <option value="process_run" ${initial?.item_type==='process_run'?'selected':''}>Process Run</option>
                <option value="budget_review" ${initial?.item_type==='budget_review'?'selected':''}>Budget Review</option>
                <option value="approval_deadline" ${initial?.item_type==='approval_deadline'?'selected':''}>Approval Deadline</option>
                <option value="coworker_task" ${initial?.item_type==='coworker_task'?'selected':''}>Coworker Task</option>
                <option value="ai_workforce_shift" ${initial?.item_type==='ai_workforce_shift'?'selected':''}>AI Workforce Shift</option>
                <option value="customer_touchpoint" ${initial?.item_type==='customer_touchpoint'?'selected':''}>Customer Touchpoint</option>
                <option value="report_generation" ${initial?.item_type==='report_generation'?'selected':''}>Report Generation</option>
                <option value="reminder" ${initial?.item_type==='reminder'?'selected':''}>Reminder</option>
                <option value="maintenance" ${initial?.item_type==='maintenance'?'selected':''}>Maintenance</option>
                <option value="compliance_audit" ${initial?.item_type==='compliance_audit'?'selected':''}>Compliance Audit</option>
                <option value="desktop_automation" ${initial?.item_type==='desktop_automation'?'selected':''}>Desktop Automation</option>
                <option value="strategic_review" ${initial?.item_type==='strategic_review'?'selected':''}>Strategic Review</option>
              </select>
            </div>

            <div class="form-group">
              <label class="form-label">Priority</label>
              <select id="schFormPriority" class="form-input">
                <option value="LOW" ${initial?.priority==='LOW'?'selected':''}>Low</option>
                <option value="MEDIUM" ${initial?.priority==='MEDIUM'?'selected':''}>Medium</option>
                <option value="HIGH" ${initial?.priority==='HIGH'?'selected':''}>High</option>
                <option value="URGENT" ${initial?.priority==='URGENT'?'selected':''}>Urgent</option>
              </select>
            </div>
          </div>

          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div class="form-group">
              <label class="form-label">Start Date & Time</label>
              <input type="datetime-local" id="schFormStart" class="form-input" value="${defaultStart}" required />
            </div>
            <div class="form-group">
              <label class="form-label">End Date & Time</label>
              <input type="datetime-local" id="schFormEnd" class="form-input" value="${defaultEnd}" required />
            </div>
          </div>

          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div class="form-group">
              <label class="form-label">Assigned Specialist</label>
              <input type="text" id="schFormAssigned" class="form-input" value="${this.escape(initial?.assigned_to || 'AI CEO')}" placeholder="e.g. AI CEO, CFO Agent, Host" />
            </div>
            <div class="form-group">
              <label class="form-label">Recurrence</label>
              <select id="schFormRecurrence" class="form-input">
                <option value="NONE">None (One-time)</option>
                <option value="DAILY">Daily</option>
                <option value="WEEKLY">Weekly</option>
                <option value="MONTHLY">Monthly</option>
              </select>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Description & Context</label>
            <textarea id="schFormDesc" class="form-input" rows="3" placeholder="Context, agenda items, or outcomes...">${this.escape(initial?.description || '')}</textarea>
          </div>

          <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:10px;">
            <button type="button" class="btn-secondary" onclick="closeModal()">Cancel</button>
            <button type="submit" class="btn-primary">Save to Schedule</button>
          </div>
        </form>
      `;

      overlay.style.display = 'flex';
    }

    async submitCreateForm() {
      const companyId = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : 'comp_primary';
      const title = document.getElementById('schFormTitle').value.trim();
      const item_type = document.getElementById('schFormType').value;
      const priority = document.getElementById('schFormPriority').value;
      const startStr = document.getElementById('schFormStart').value;
      const endStr = document.getElementById('schFormEnd').value;
      const assigned_to = document.getElementById('schFormAssigned').value.trim();
      const recurrence = document.getElementById('schFormRecurrence').value;
      const description = document.getElementById('schFormDesc').value.trim();

      const start_time = new Date(startStr).getTime() / 1000;
      const end_time = new Date(endStr).getTime() / 1000;

      try {
        const res = await fetch('/api/schedules', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            company_id: companyId,
            title,
            item_type,
            priority,
            start_time,
            end_time,
            assigned_to,
            recurrence,
            description
          })
        });

        if (res.ok) {
          closeModal();
          this.render();
        } else {
          alert('Failed to save schedule.');
        }
      } catch (e) {
        console.error('Error creating schedule item:', e);
      }
    }

    viewDetails(scheduleId) {
      const item = this.schedules.find(s => s.schedule_id === scheduleId);
      if (!item) return;

      const modalBody = document.getElementById('modalBody');
      const modalTitle = document.getElementById('modalTitle');
      const overlay = document.getElementById('modalOverlay');

      if (!modalBody || !overlay) return;

      const sDate = new Date(item.start_time * 1000);
      const eDate = item.end_time ? new Date(item.end_time * 1000) : sDate;

      modalTitle.textContent = 'Schedule Item Details';
      modalBody.innerHTML = `
        <div style="display:flex; flex-direction:column; gap:16px;">
          <div>
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
              <span class="badge ${this.getPriorityBadge(item.priority)}">${item.priority}</span>
              <span class="badge badge-subtle">${item.item_type}</span>
              <span class="badge ${item.status==='COMPLETED'?'badge-emerald':'badge-blue'}">${item.status}</span>
            </div>
            <h2 style="font-size:20px; font-weight:700; color:var(--text-primary); margin:0 0 6px 0;">
              ${this.escape(item.title)}
            </h2>
            <p style="font-size:13px; color:var(--text-secondary); margin:0;">
              ${this.escape(item.description || 'No additional context provided.')}
            </p>
          </div>

          ${item.conflict_detected ? `
            <div style="background:rgba(239,68,68,0.1); border:1px solid #ef4444; border-radius:var(--radius-md); padding:12px; font-size:12.5px; color:#ef4444;">
              <strong>⚠️ Schedule Collision Detected:</strong> ${this.escape(item.conflict_reason || 'Overlaps with another item')}
            </div>
          ` : ''}

          <div style="background:var(--bg-surface-hover); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:12px; font-size:13px; display:grid; grid-template-columns:1fr 1fr; gap:10px;">
            <div>
              <div style="color:var(--text-muted); font-size:11px; text-transform:uppercase;">Time Window</div>
              <div style="font-weight:600; color:var(--text-primary); margin-top:2px;">
                ${sDate.toLocaleDateString()} ${sDate.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})} → ${eDate.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}
              </div>
            </div>
            <div>
              <div style="color:var(--text-muted); font-size:11px; text-transform:uppercase;">Assigned Agent</div>
              <div style="font-weight:600; color:var(--text-primary); margin-top:2px;">
                ${this.escape(item.assigned_to || 'AI CEO')}
              </div>
            </div>
            <div>
              <div style="color:var(--text-muted); font-size:11px; text-transform:uppercase;">Recurrence</div>
              <div style="font-weight:600; color:var(--text-primary); margin-top:2px;">
                ${item.recurrence}
              </div>
            </div>
            <div>
              <div style="color:var(--text-muted); font-size:11px; text-transform:uppercase;">Schedule ID</div>
              <div style="font-weight:600; color:var(--text-muted); font-family:var(--font-mono); font-size:11px; margin-top:2px;">
                ${item.schedule_id}
              </div>
            </div>
          </div>

          <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px;">
            <button class="btn-secondary" style="color:#ef4444;" onclick="window.ScheduleWorkspace.deleteItem('${item.schedule_id}')">
              Delete Item
            </button>
            <button class="btn-primary" onclick="closeModal()">
              Close
            </button>
          </div>
        </div>
      `;

      overlay.style.display = 'flex';
    }

    async deleteItem(scheduleId) {
      if (!confirm('Are you sure you want to remove this schedule item?')) return;
      try {
        const res = await fetch(`/api/schedules/${scheduleId}/delete`, { method: 'POST' });
        if (res.ok) {
          closeModal();
          this.render();
        }
      } catch (err) {
        console.error('Delete schedule failed:', err);
      }
    }

    openRecommendationsModal() {
      const modalBody = document.getElementById('modalBody');
      const modalTitle = document.getElementById('modalTitle');
      const overlay = document.getElementById('modalOverlay');

      if (!modalBody || !overlay) return;

      modalTitle.textContent = 'AI CEO Schedule Recommendations';
      modalBody.innerHTML = `
        <div style="display:flex; flex-direction:column; gap:12px;">
          <p style="font-size:13px; color:var(--text-secondary); margin:0 0 6px 0;">
            The AI CEO continuously evaluates pending owner governance gates, mission milestones, and ledger integrity to synthesize high-impact schedules.
          </p>
          ${this.recommendations.length === 0 ? '<div style="padding:20px; text-align:center; color:var(--text-muted);">No urgent scheduling recommendations.</div>' : ''}
          ${this.recommendations.map(r => `
            <div style="background:var(--bg-surface-hover); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:14px; display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap;">
              <div>
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                  <span class="badge ${this.getPriorityBadge(r.priority)}">${r.priority}</span>
                  <span class="badge badge-subtle">${r.item_type}</span>
                  <span style="font-size:13.5px; font-weight:700; color:var(--text-primary);">${this.escape(r.title)}</span>
                </div>
                <div style="font-size:12px; color:var(--text-secondary);">${this.escape(r.reason)}</div>
              </div>
              <button class="btn-primary" style="font-size:12px; padding:6px 14px;" onclick="window.ScheduleWorkspace.adoptRecommendation('${r.recommendation_id}')">
                Adopt & Schedule
              </button>
            </div>
          `).join('')}
        </div>
      `;

      overlay.style.display = 'flex';
    }

    async adoptRecommendation(recId) {
      const rec = this.recommendations.find(r => r.recommendation_id === recId);
      if (!rec) return;

      try {
        const res = await fetch('/api/schedules', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            company_id: rec.company_id || 'comp_primary',
            title: rec.title,
            item_type: rec.item_type,
            priority: rec.priority,
            start_time: rec.suggested_start,
            end_time: rec.suggested_start + 3600,
            description: rec.reason,
            assigned_to: 'AI CEO'
          })
        });

        if (res.ok) {
          closeModal();
          this.render();
        }
      } catch (e) {
        console.error('Failed to adopt recommendation:', e);
      }
    }

    escape(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    }
  }

  window.ScheduleWorkspace = new ScheduleWorkspaceManager();
})();
